import json
import os


def fmt_sec(sec: int) -> str:
    """Converte segundos para formato ``hh:mm:ss`` ou ``mm:ss``."""
    h, sec = divmod(max(0, sec), 3600)
    m, s = divmod(sec, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_time(txt: str) -> int:
    """Converte strings ``hh:mm:ss`` ou ``mm:ss`` em segundos."""
    parts = [int(p) for p in txt.strip().split(":")]
    if len(parts) == 2:
        m, s = parts
        h = 0
    elif len(parts) == 3:
        h, m, s = parts
    else:
        raise ValueError("Time must be in hh:mm:ss or mm:ss format")
    return h * 3600 + m * 60 + s


def parse_flexible_time(txt: str) -> int:
    """Converte ``hh:mm:ss``, ``mm:ss`` ou dígitos em segundos."""
    cleaned = txt.strip()
    if ":" in cleaned:
        return parse_time(cleaned)

    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if not digits:
        raise ValueError("Invalid time")

    digits = digits[-6:]  # keep last 6 digits (hhmmss)
    if len(digits) <= 2:
        h, m, s = 0, 0, int(digits)
    elif len(digits) <= 4:
        h = 0
        m = int(digits[:-2])
        s = int(digits[-2:])
    else:
        h = int(digits[:-4])
        m = int(digits[-4:-2])
        s = int(digits[-2:])
    return h * 3600 + m * 60 + s


class ChapterManager:
    """Gerencia carregamento e salvamento de dados de um vídeo."""

    def __init__(self, video_path: str) -> None:
        """Cria um gerenciador para o arquivo de vídeo indicado."""

        self.json_path = os.path.splitext(video_path)[0] + ".json"

    def load(self) -> dict:
        """Carrega capítulos e casting do disco, se houver."""

        data: dict = {"chapters": [], "casting": []}
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
            except json.JSONDecodeError:
                return data  # Retorna dados vazios se o JSON for inválido
            if isinstance(loaded, list):
                data["chapters"] = loaded
            else:
                data["chapters"] = loaded.get("chapters", [])
                data["casting"] = loaded.get("casting", [])
        return data

    def save(self, chapters: list[dict], casting: list[str]) -> None:
        """Grava capítulos e casting no disco."""

        with open(self.json_path, "w", encoding="utf-8") as fh:
            json.dump({"chapters": chapters, "casting": casting}, fh, ensure_ascii=False, indent=2)


def fmt_srt_time(ms: int) -> str:
    """Converte milissegundos em formato de legenda SRT ``hh:mm:ss,mss``."""
    ms = max(0, ms)
    seconds, mss = divmod(ms, 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{mss:03d}"


def parse_srt_time(txt: str) -> int:
    """Converte string de tempo estendido (hh:mm:ss,mss ou mm:ss,mss) em milissegundos."""
    cleaned = txt.strip().replace(".", ",")
    if "," in cleaned:
        time_part, ms_part = cleaned.split(",", 1)
        ms_part = (ms_part + "000")[:3]
        mss = int(ms_part)
        parts = [int(p) for p in time_part.split(":")]
        if len(parts) == 2:
            m, s = parts
            h = 0
        elif len(parts) == 3:
            h, m, s = parts
        else:
            raise ValueError("Formato de tempo estendido inválido")
        return (h * 3600 + m * 60 + s) * 1000 + mss
    else:
        sec = parse_flexible_time(cleaned)
        return sec * 1000


class SubtitleManager:
    """Gerencia leitura e gravação de arquivos de legenda no formato padrão .srt."""

    def __init__(self, video_path: str) -> None:
        """Define o caminho do arquivo .srt com base no vídeo."""
        self.srt_path = os.path.splitext(video_path)[0] + ".srt"

    def load(self) -> list[dict]:
        """Carrega blocos de legenda do arquivo .srt se existir no disco."""
        subtitles: list[dict] = []
        if not os.path.exists(self.srt_path):
            return subtitles

        try:
            with open(self.srt_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception:
            return subtitles

        blocks = content.strip().split("\n\n")
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) >= 2:
                time_line_idx = -1
                for idx, line in enumerate(lines):
                    if "-->" in line:
                        time_line_idx = idx
                        break
                if time_line_idx != -1:
                    times = lines[time_line_idx].split("-->")
                    if len(times) == 2:
                        try:
                            start_ms = parse_srt_time(times[0])
                            end_ms = parse_srt_time(times[1])
                            text = "\n".join(lines[time_line_idx + 1 :])
                            subtitles.append({"start": start_ms, "end": end_ms, "text": text})
                        except ValueError:
                            continue
        return subtitles

    def save(self, subtitles: list[dict]) -> None:
        """Grava a lista de legendas no formato padrão .srt em disco."""
        subtitles.sort(key=lambda x: x["start"])
        blocks = []
        for idx, sub in enumerate(subtitles, start=1):
            start_str = fmt_srt_time(sub["start"])
            end_str = fmt_srt_time(sub["end"])
            text = sub.get("text", "")
            blocks.append(f"{idx}\n{start_str} --> {end_str}\n{text}")

        with open(self.srt_path, "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(blocks) + "\n")

