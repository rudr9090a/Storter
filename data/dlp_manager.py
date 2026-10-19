import asyncio
import json
import logging
from pathlib import Path
from typing import Any

# ============================================================
# PATHS
# ============================================================

DATA_DIR = Path(__file__).resolve().parent
TOOLS_DIR = DATA_DIR / "tools"
DOWNLOAD_DIR = DATA_DIR / "song_assets"

YTDLP = TOOLS_DIR / "yt-dlp.exe"
DENO = TOOLS_DIR / "deno.exe"
FFMPEG = TOOLS_DIR / "ffmpeg.exe"
FFPROBE = TOOLS_DIR / "ffprobe.exe"

# ============================================================
# CONFIGURATION
# ============================================================

MAX_CONCURRENT_DOWNLOADS = 5
MAX_DURATION_SECONDS = 600  # 10 minutes

logger = logging.getLogger("storter.dlp_manager")


# ============================================================
# VALIDATION
# ============================================================

def validate_tools() -> None:
    """Ensure all required bundled executables exist."""
    required_tools = {
        "yt-dlp": YTDLP,
        "Deno": DENO,
        "FFmpeg": FFMPEG,
        "FFprobe": FFPROBE,
    }

    missing = [
        f"{name}: {path}"
        for name, path in required_tools.items()
        if not path.is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required bundled tools:\n" + "\n".join(missing)
        )

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def already_downloaded(video_id: str) -> bool:
    """Check whether this YouTube video already has its MP3."""
    return (DOWNLOAD_DIR / f"{video_id}.mp3").is_file()


# ============================================================
# SUBPROCESS
# ============================================================

async def run_command(
    *args: str,
) -> tuple[int, str, str]:
    """Run a command asynchronously and capture its output."""
    process = await asyncio.create_subprocess_exec(
        *map(str, args),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(DATA_DIR),
    )

    stdout, stderr = await process.communicate()

    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def base_command() -> list[str]:
    """Common yt-dlp arguments for the bundled runtime and media tools."""
    return [
        str(YTDLP),
        "--js-runtimes",
        f"deno:{DENO}",
        "--remote-components",
        "ejs:npm",
        "--ffmpeg-location",
        str(TOOLS_DIR),
        "--ignore-errors",
        "--no-warnings",
    ]


# ============================================================
# METADATA EXTRACTION
# ============================================================

async def get_video_info(
    video_url: str,
) -> dict[str, Any] | None:
    """
    Fetch metadata without downloading media.

    Returns None if yt-dlp cannot retrieve usable video metadata.
    """
    command = base_command() + [
        "--dump-single-json",
        "--skip-download",
        "--no-playlist",
        video_url,
    ]

    code, stdout, stderr = await run_command(*command)

    if code != 0:
        logger.warning(
            "Could not inspect video %s: %s",
            video_url,
            stderr[-1000:],
        )

    # yt-dlp may emit informational output alongside JSON.
    for line in reversed(stdout.splitlines()):
        try:
            data = json.loads(line)
            if isinstance(data, dict) and data.get("id"):
                return data
        except json.JSONDecodeError:
            continue

    return None


async def get_playlist_entries(
    playlist_url: str,
) -> list[dict[str, Any]]:
    """Extract playlist entries and their durations before downloading."""
    command = base_command() + [
        "--dump-single-json",
        "--skip-download",
        "--flat-playlist",
        "--yes-playlist",
        playlist_url,
    ]

    code, stdout, stderr = await run_command(*command)

    if code != 0 and not stdout.strip():
        raise RuntimeError(
            "Failed to retrieve playlist metadata:\n" + stderr[-2000:]
        )

    # Find the JSON object in yt-dlp's output.
    playlist_data = None

    for line in reversed(stdout.splitlines()):
        try:
            data = json.loads(line)
            if isinstance(data, dict) and (
                "entries" in data or data.get("id")
            ):
                playlist_data = data
                break
        except json.JSONDecodeError:
            continue

    if playlist_data is None:
        raise RuntimeError(
            "yt-dlp did not return valid playlist metadata."
        )

    entries = playlist_data.get("entries")

    # A single video URL may return one video instead of a playlist.
    if entries is None:
        entries = [playlist_data]

    return [entry for entry in entries if isinstance(entry, dict)]


# ============================================================
# SINGLE TRACK DOWNLOAD
# ============================================================

async def download_track(
    video_id: str,
    track_number: int,
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict[str, Any] | None, str | None]:
    """
    Download one track.

    Returns:
        (video_id, metadata, error)
    """
    async with semaphore:
        # Check again immediately before downloading.
        if already_downloaded(video_id):
            logger.info("Skipping existing track: %s", video_id)
            return video_id, None, None

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        command = base_command() + [
            "--no-playlist",
            "--no-overwrites",
            "--format",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "--write-thumbnail",
            "--convert-thumbnails",
            "png",
            "--write-info-json",
            "--output",
            str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
            video_url,
        ]

        logger.info("Downloading track %s (%s)", track_number, video_id)

        code, stdout, stderr = await run_command(*command)

        mp3_path = DOWNLOAD_DIR / f"{video_id}.mp3"
        info_path = DOWNLOAD_DIR / f"{video_id}.info.json"
        thumbnail_path = DOWNLOAD_DIR / f"{video_id}.png"

        if code != 0 or not mp3_path.is_file():
            error = stderr[-2000:] or stdout[-2000:] or (
                "yt-dlp failed to create the MP3."
            )
            logger.error("Download failed for %s: %s", video_id, error)
            return video_id, None, error

        # Read metadata produced by yt-dlp.
        info: dict[str, Any] = {}

        if info_path.is_file():
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Could not read metadata for %s: %s",
                    video_id,
                    exc,
                )

            # The info JSON is an intermediate file, not the final output.
            info_path.unlink(missing_ok=True)

        metadata = {
            "video_id": video_id,
            "title": info.get("title"),
            "artist": (
                info.get("artist")
                or info.get("creator")
                or info.get("uploader")
                or info.get("channel")
            ),
            "album": info.get("album"),
            "thumbnail": (
                str(thumbnail_path)
                if thumbnail_path.is_file()
                else None
            ),
            "track_number": (
                info.get("track_number") or track_number
            ),
            "duration": info.get("duration"),
            "webpage_url": (
                info.get("webpage_url") or video_url
            ),
            "filename": mp3_path.name,
        }

        logger.info("Downloaded: %s", mp3_path.name)

        return video_id, metadata, None


# ============================================================
# ALBUM / PLAYLIST DOWNLOAD
# ============================================================

async def download_album(album_url: str) -> dict[str, dict[str, Any]]:
    """
    Download eligible tracks from a YouTube playlist or video URL.

    Rules:
    - Existing {video_id}.mp3 files are skipped.
    - Videos longer than 600 seconds are skipped.
    - Videos with unknown duration are inspected individually.
    - At most MAX_CONCURRENT_DOWNLOADS tracks download at once.
    - MP3 and PNG artwork filenames use the YouTube video ID.

    Returns:
        A dictionary keyed by MP3 filename:
        {
            "VIDEO_ID.mp3": {
                "video_id": "...",
                "title": "...",
                "artist": "...",
                ...
            }
        }

    Only tracks successfully downloaded during this call are returned.
    """
    validate_tools()

    logger.info("Inspecting playlist: %s", album_url)

    entries = await get_playlist_entries(album_url)

    if not entries:
        logger.warning("No videos found.")
        return {}

    tracks: list[dict[str, Any]] = []
    skipped_existing: list[str] = []
    skipped_too_long: list[dict[str, Any]] = []
    skipped_unknown_duration: list[str] = []
    skipped_unavailable: list[str] = []

    # First pass: filter using playlist metadata.
    for index, entry in enumerate(entries, start=1):
        video_id = entry.get("id")

        if not video_id:
            skipped_unavailable.append(f"Playlist entry {index}")
            continue

        if already_downloaded(video_id):
            skipped_existing.append(video_id)
            continue

        duration = entry.get("duration")

        # Some YouTube playlist entries omit duration.
        # Fetch individual metadata before deciding whether to download.
        if duration is None:
            video_url = (
                entry.get("webpage_url")
                or f"https://www.youtube.com/watch?v={video_id}"
            )

            info = await get_video_info(video_url)

            if info is None:
                skipped_unavailable.append(video_id)
                logger.warning(
                    "Skipping %s: unable to verify its duration.",
                    video_id,
                )
                continue

            duration = info.get("duration")

            # Refuse to download if the duration still cannot be verified.
            if duration is None:
                skipped_unknown_duration.append(video_id)
                logger.warning(
                    "Skipping %s: duration is unknown.",
                    video_id,
                )
                continue

            entry = {**entry, **info}

        if duration > MAX_DURATION_SECONDS:
            skipped_too_long.append({
                "video_id": video_id,
                "duration_seconds": duration,
                "title": entry.get("title"),
            })
            logger.info(
                "Skipping %s: duration %s seconds exceeds 10 minutes.",
                video_id,
                duration,
            )
            continue

        tracks.append({
            "id": video_id,
            "track_number": (
                entry.get("playlist_index") or index
            ),
        })

    logger.info(
        "Playlist scan complete: %d entries, %d eligible, "
        "%d already downloaded, %d over limit.",
        len(entries),
        len(tracks),
        len(skipped_existing),
        len(skipped_too_long),
    )

    if not tracks:
        logger.info("Nothing to download.")
        logger.info(
            "Skipped: existing=%d, too_long=%d, unknown_duration=%d, "
            "unavailable=%d",
            len(skipped_existing),
            len(skipped_too_long),
            len(skipped_unknown_duration),
            len(skipped_unavailable),
        )
        return {}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    results = await asyncio.gather(
        *[
            download_track(
                track["id"],
                track["track_number"],
                semaphore,
            )
            for track in tracks
        ],
        return_exceptions=True,
    )

    album_data: dict[str, dict[str, Any]] = {}
    failed_downloads: list[dict[str, str]] = []

    for track, result in zip(tracks, results):
        if isinstance(result, Exception):
            failed_downloads.append({
                "video_id": track["id"],
                "error": str(result),
            })
            logger.exception(
                "Unexpected error downloading %s",
                track["id"],
                exc_info=result,
            )
            continue

        video_id, metadata, error = result

        if error:
            failed_downloads.append({
                "video_id": video_id,
                "error": error,
            })
            continue

        if metadata is not None:
            album_data[f"{video_id}.mp3"] = metadata

    logger.info(
        "Download complete: downloaded=%d, existing=%d, too_long=%d, "
        "unknown_duration=%d, unavailable=%d, failed=%d",
        len(album_data),
        len(skipped_existing),
        len(skipped_too_long),
        len(skipped_unknown_duration),
        len(skipped_unavailable),
        len(failed_downloads),
    )

    return album_data
