from datetime import timedelta

# ponytail: no speech-to-text step here. ASR exists to align audio to text
# whose timing you don't already know. We always know both -- each scene
# carries its own caption text and duration_seconds straight from the
# storyboard -- so captions are just those, laid out cumulatively. Real
# per-word timestamps (spec section 19) become worth it once a real TTS
# provider (Phase 5) can hand back word-level timing itself.


def _format_timestamp(seconds: float) -> str:
    total_ms = int(timedelta(seconds=seconds).total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(scenes) -> str:
    cues = []
    start = 0.0
    for index, scene in enumerate(scenes, start=1):
        end = start + scene.duration_seconds
        cues.append(
            f"{index}\n{_format_timestamp(start)} --> {_format_timestamp(end)}\n{scene.caption}\n"
        )
        start = end
    return "\n".join(cues)
