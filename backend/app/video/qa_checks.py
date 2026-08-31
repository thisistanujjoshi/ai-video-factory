import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TechnicalCheckResult:
    passed: bool
    issues: list[str] = field(default_factory=list)


def _ffprobe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    return json.loads(result.stdout)


def _has_decode_errors(path: Path) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode != 0 or bool(result.stderr.strip())


# ponytail: tolerance for encode/mux rounding, not a real quality margin.
_DURATION_TOLERANCE_SECONDS = 2.0
_ASPECT_RATIO_TOLERANCE = 0.01


def run_technical_checks(video_path: Path, profile, scenes) -> TechnicalCheckResult:
    if not video_path.exists() or video_path.stat().st_size == 0:
        return TechnicalCheckResult(False, ["rendered file does not exist or is empty"])

    probe = _ffprobe(video_path)
    if not probe:
        return TechnicalCheckResult(False, ["file is not a valid/readable media container"])

    issues: list[str] = []
    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        issues.append("no video stream found")
    if not audio_streams:
        issues.append("no audio stream found")

    if video_streams:
        vs = video_streams[0]
        width, height = vs.get("width"), vs.get("height")
        expected_w, expected_h = (
            int(x) for x in profile.video.get("resolution", "1080x1920").split("x")
        )
        if (width, height) != (expected_w, expected_h):
            issues.append(f"resolution {width}x{height} != expected {expected_w}x{expected_h}")

        expected_ratio = profile.video.get("aspect_ratio", "9:16")
        ratio_w, ratio_h = (int(x) for x in expected_ratio.split(":"))
        if (
            width
            and height
            and abs((width / height) - (ratio_w / ratio_h)) > _ASPECT_RATIO_TOLERANCE
        ):
            issues.append(
                f"aspect ratio of {width}x{height} does not match expected {expected_ratio}"
            )

        if vs.get("codec_name") != "h264":
            issues.append(f"unexpected video codec {vs.get('codec_name')!r}, expected h264")

    if audio_streams and audio_streams[0].get("codec_name") != "aac":
        issues.append(
            f"unexpected audio codec {audio_streams[0].get('codec_name')!r}, expected aac"
        )

    duration = float(probe.get("format", {}).get("duration", 0))
    min_duration = profile.video.get("min_duration_seconds", 0)
    max_duration = profile.video.get("max_duration_seconds", 10**9)
    if not (
        min_duration - _DURATION_TOLERANCE_SECONDS
        <= duration
        <= max_duration + _DURATION_TOLERANCE_SECONDS
    ):
        issues.append(
            f"duration {duration:.1f}s outside expected range {min_duration}-{max_duration}s"
        )

    if not all(scene.caption.strip() for scene in scenes):
        issues.append("one or more scenes are missing caption text")

    if _has_decode_errors(video_path):
        issues.append("ffmpeg reported decode errors (possible corrupt frames)")

    return TechnicalCheckResult(passed=not issues, issues=issues)
