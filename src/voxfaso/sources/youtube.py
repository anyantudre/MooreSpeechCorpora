"""YouTube videos and playlists, audio only, through yt-dlp.

YouTube's terms forbid downloading without permission: only use content you have the
right to use. Install with `pip install "voxfaso[youtube]"`; a JavaScript runtime
(e.g. Deno) helps yt-dlp with YouTube's player checks.
"""
from __future__ import annotations

from pathlib import Path

from .base import Source, register


@register("youtube")
class YouTube(Source):
    """Params: urls (list of video or playlist URLs) or urls_file (one URL per line)."""

    def fetch(self, raw_dir: Path) -> list[dict]:
        import yt_dlp
        from ..audio import ffmpeg_binary

        urls = list(self.params.get("urls", []))
        if self.params.get("urls_file"):
            urls += [u.strip() for u in Path(self.params["urls_file"]).read_text().splitlines() if u.strip()]
        raw_dir.mkdir(parents=True, exist_ok=True)
        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(raw_dir / "%(id)s.%(ext)s"),
            "ffmpeg_location": ffmpeg_binary(),
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
            "postprocessor_args": ["-ac", "1", "-ar", "16000"],
            "download_archive": str(raw_dir / "downloaded.txt"),   # skip what is already done
            "sleep_interval": max(self.delay, 5), "max_sleep_interval": 10,
            "playlistend": self.limit, "quiet": True, "noprogress": True, "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            for url in urls:
                ydl.download([url])
        return [{"id": p.stem, "audio_filepath": p.name, "lines": None, "source": "youtube"}
                for p in sorted(raw_dir.glob("*.wav"))][: self.limit]
