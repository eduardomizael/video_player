import json
import os


def fmt_sec(sec: int) -> str:
    """Convert seconds to ``hh:mm:ss`` or ``mm:ss`` format."""
    h, sec = divmod(max(0, sec), 3600)
    m, s = divmod(sec, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_time(txt: str) -> int:
    """Parse ``hh:mm:ss`` or ``mm:ss`` strings into seconds."""
    parts = [int(p) for p in txt.strip().split(":")]
    if len(parts) == 2:
        m, s = parts
        h = 0
    elif len(parts) == 3:
        h, m, s = parts
    else:
        raise ValueError("Time must be in hh:mm:ss or mm:ss format")
    return h * 3600 + m * 60 + s


class ChapterManager:
    """Handle loading and saving chapter information for a video."""

    def __init__(self, video_path: str) -> None:
        self.json_path = os.path.splitext(video_path)[0] + ".json"

    def load(self) -> list[dict]:
        chapters: list[dict] = []
        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as fh:
                chapters = json.load(fh)
        return chapters

    def save(self, chapters: list[dict]) -> None:
        with open(self.json_path, "w", encoding="utf-8") as fh:
            json.dump(chapters, fh, ensure_ascii=False, indent=2)
