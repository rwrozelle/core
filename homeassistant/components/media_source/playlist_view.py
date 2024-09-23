"""HTTP view that returns a playlist of all the leaf descendants of media-id."""

import io

from aiohttp import web

# pylint: disable-next=hass-relative-import
from homeassistant.components import media_source
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.media_player import async_process_play_media_url
from homeassistant.core import HomeAssistant

from .models import BrowseMediaSource, MediaSourceItem


class PlaylistView(HomeAssistantView):
    """Web view that returns a playlist of all the leaf descendants of media_content_id."""

    requires_auth = True
    url = "/api/media/playlist/playlist.m3u"
    name = "api:media:playlist"

    # def __init__(self) -> None:
    #    """Initialize a playlist view."""

    async def get(
        self,
        request: web.Request,
    ) -> web.StreamResponse:
        """Get that returns a playlist of all the leaf descendants of media_content_id."""

        media_content_id = request.query.get("media")
        assert media_content_id
        hass = request.app[KEY_HASS]
        ms_item = MediaSourceItem.from_uri(hass, media_content_id, None)
        br_item = await ms_item.async_browse()
        playlist = await self._async_flatten(hass, br_item, [])
        content = await self._async_generate_m3u(hass, br_item, playlist)
        return web.Response(text=content, content_type="audio/x-mpegurl")

    async def _async_flatten(
        self, hass: HomeAssistant, parent: BrowseMediaSource, playlist: list
    ) -> list:
        """Create a flattened list with a left hand tree walk."""

        if parent.children:
            for child in parent.children:
                if child.can_expand:
                    ms_child = MediaSourceItem.from_uri(
                        hass, child.media_content_id, None
                    )
                    br_child = await ms_child.async_browse()
                    playlist = await self._async_flatten(hass, br_child, playlist)
                else:
                    playlist.append(child)

        else:
            playlist.append(parent)

        return playlist

    async def _async_generate_m3u(
        self, hass: HomeAssistant, br_item: BrowseMediaSource, playlist: list
    ) -> str:
        """Generate string containing m3u contents."""
        output = io.StringIO()
        output.write("#EXTM3U\n")
        output.write("#PLAYLIST:")
        output.write(br_item.title)
        output.write("\n")
        for track in playlist:
            sourced_media = await media_source.async_resolve_media(
                hass, track.media_content_id, None
            )
            url = async_process_play_media_url(hass, sourced_media.url)
            # with tinytag, we could get duration for audio files
            output.write("#EXTINF:0,")
            output.write(track.title)
            output.write("\n")
            output.write(url)
            output.write("\n")

        m3u = output.getvalue()
        output.close()
        return m3u
