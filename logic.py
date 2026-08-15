from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


class DataLoadError(RuntimeError):
    """Indica que um arquivo lateral não pôde ser carregado com segurança."""

    def __init__(self, path: Path, reason: str) -> None:
        """Registra o caminho e uma explicação adequada para exibição ao usuário."""

        self.path = path
        self.reason = reason
        super().__init__(f"Não foi possível carregar {path}: {reason}")


def _atomic_write_text(path: Path, content: str) -> None:
    """Substitui um arquivo atomicamente e mantém a versão anterior em ``.bak``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
            newline="\n",
        ) as file_handle:
            file_handle.write(content)
            file_handle.flush()
            os.fsync(file_handle.fileno())
            temporary_path = Path(file_handle.name)
        if path.exists():
            shutil.copy2(path, path.with_suffix(f"{path.suffix}.bak"))
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def fmt_sec(sec: int) -> str:
    """Converte segundos para formato ``hh:mm:ss`` ou ``mm:ss``."""

    hours, sec = divmod(max(0, sec), 3600)
    minutes, seconds = divmod(sec, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def parse_time(txt: str) -> int:
    """Converte strings ``hh:mm:ss`` ou ``mm:ss`` em segundos válidos."""

    parts = [int(part) for part in txt.strip().split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        hours = 0
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError("O tempo deve estar no formato hh:mm:ss ou mm:ss")
    if hours < 0 or not 0 <= minutes <= 59 or not 0 <= seconds <= 59:
        raise ValueError("Os componentes do tempo estão fora do intervalo permitido")
    return hours * 3600 + minutes * 60 + seconds


def parse_flexible_time(txt: str) -> int:
    """Converte ``hh:mm:ss``, ``mm:ss`` ou dígitos ``hhmmss`` em segundos."""

    cleaned = txt.strip()
    if ":" in cleaned:
        return parse_time(cleaned)
    if not cleaned.isdigit():
        raise ValueError("O tempo deve conter apenas dígitos")

    digits = cleaned[-6:]
    if len(digits) <= 2:
        hours, minutes, seconds = 0, 0, int(digits)
    elif len(digits) <= 4:
        hours = 0
        minutes = int(digits[:-2])
        seconds = int(digits[-2:])
    else:
        hours = int(digits[:-4])
        minutes = int(digits[-4:-2])
        seconds = int(digits[-2:])
    if minutes > 59 or seconds > 59:
        raise ValueError("Os minutos e segundos devem estar entre 00 e 59")
    return hours * 3600 + minutes * 60 + seconds


def _validate_chapter(chapter: object, location: str, parent: dict[str, Any] | None = None) -> dict[str, Any]:
    """Valida a hierarquia e amplia o fim dos pais para conter seus descendentes."""

    if not isinstance(chapter, dict):
        raise TypeError(f"{location} não é um objeto")
    title = chapter.get("title")
    start = chapter.get("start")
    end = chapter.get("end")
    subs = chapter.get("subs", [])
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"{location} não possui título válido")
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise ValueError(f"{location} possui início inválido")
    if isinstance(end, bool) or not isinstance(end, int) or end < 0:
        raise ValueError(f"{location} possui fim inválido")
    end = max(start, end)
    if parent is not None and start < parent["start"]:
        raise ValueError(f"{location} começa antes do capítulo pai")
    if not isinstance(subs, list):
        raise TypeError(f"{location} possui subcapítulos inválidos")

    normalized = {"title": title.strip(), "start": start, "end": end, "subs": []}
    normalized["subs"] = [
        _validate_chapter(sub, f"{location}, subcapítulo {index}", normalized)
        for index, sub in enumerate(subs, start=1)
    ]
    if normalized["subs"]:
        normalized["end"] = max(normalized["end"], *(sub["end"] for sub in normalized["subs"]))
    return normalized


class ChapterManager:
    """Gerencia carregamento e salvamento de dados de um vídeo."""

    def __init__(self, video_path: str) -> None:
        """Cria um gerenciador para o arquivo de vídeo indicado."""

        self.json_path = os.path.splitext(video_path)[0] + ".json"

    def load(self) -> dict[str, Any]:
        """Carrega capítulos e casting, rejeitando dados que poderiam ser perdidos."""

        path = Path(self.json_path)
        if not path.exists():
            return {"chapters": [], "casting": []}
        try:
            with path.open("r", encoding="utf-8") as file_handle:
                loaded = json.load(file_handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DataLoadError(path, str(exc)) from exc

        if isinstance(loaded, list):
            chapters = loaded
            casting: object = []
        elif isinstance(loaded, dict):
            chapters = loaded.get("chapters", [])
            casting = loaded.get("casting", [])
        else:
            raise DataLoadError(path, "a raiz do JSON deve ser um objeto ou uma lista")
        if not isinstance(chapters, list):
            raise DataLoadError(path, "o campo 'chapters' deve ser uma lista")
        if not isinstance(casting, list) or any(not isinstance(name, str) or not name.strip() for name in casting):
            raise DataLoadError(path, "o campo 'casting' deve conter apenas nomes válidos")
        try:
            validated_chapters = [
                _validate_chapter(chapter, f"capítulo {index}") for index, chapter in enumerate(chapters, start=1)
            ]
        except (TypeError, ValueError) as exc:
            raise DataLoadError(path, str(exc)) from exc
        return {"chapters": validated_chapters, "casting": [name.strip() for name in casting]}

    def save(self, chapters: list[dict], casting: list[str]) -> None:
        """Valida e grava capítulos e casting de forma atômica."""

        try:
            validated = [
                _validate_chapter(chapter, f"capítulo {index}") for index, chapter in enumerate(chapters, start=1)
            ]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Os capítulos não foram salvos: {exc}") from exc
        if any(not isinstance(name, str) or not name.strip() for name in casting):
            raise ValueError("O casting não foi salvo porque contém um nome inválido")
        content = json.dumps(
            {"chapters": validated, "casting": [name.strip() for name in casting]}, ensure_ascii=False, indent=2
        )
        _atomic_write_text(Path(self.json_path), f"{content}\n")


def fmt_srt_time(ms: int) -> str:
    """Converte milissegundos em formato de legenda SRT ``hh:mm:ss,mss``."""

    ms = max(0, ms)
    seconds, milliseconds = divmod(ms, 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_srt_time(txt: str) -> int:
    """Converte ``hh:mm:ss,mss`` ou ``mm:ss,mss`` em milissegundos."""

    cleaned = txt.strip().replace(".", ",")
    if "," not in cleaned:
        return parse_flexible_time(cleaned) * 1000

    time_part, milliseconds_part = cleaned.split(",", 1)
    if not milliseconds_part.isdigit() or len(milliseconds_part) > 3:
        raise ValueError("Os milissegundos devem conter de um a três dígitos")
    milliseconds = int(milliseconds_part.ljust(3, "0"))
    return parse_time(time_part) * 1000 + milliseconds


class SubtitleManager:
    """Gerencia leitura e gravação de arquivos de legenda no formato padrão .srt."""

    def __init__(self, video_path: str) -> None:
        """Define o caminho do arquivo .srt com base no vídeo."""

        self.srt_path = os.path.splitext(video_path)[0] + ".srt"

    def load(self) -> list[dict]:
        """Carrega todas as legendas ou rejeita o arquivo sem descartar blocos."""

        path = Path(self.srt_path)
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise DataLoadError(path, str(exc)) from exc
        if not content.strip():
            return []

        subtitles: list[dict] = []
        normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
        blocks = re.split(r"\n{2,}", normalized_content)
        for block_index, block in enumerate(blocks, start=1):
            lines = block.splitlines()
            time_line_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
            if time_line_index < 0:
                raise DataLoadError(path, f"o bloco {block_index} não possui uma linha de tempo")
            times = lines[time_line_index].split("-->")
            if len(times) != 2:
                raise DataLoadError(path, f"o bloco {block_index} possui uma linha de tempo inválida")
            try:
                start_ms = parse_srt_time(times[0])
                end_ms = parse_srt_time(times[1])
            except ValueError as exc:
                raise DataLoadError(path, f"tempo inválido no bloco {block_index}: {exc}") from exc
            if end_ms < start_ms:
                raise DataLoadError(path, f"o bloco {block_index} termina antes de começar")
            text = "\n".join(lines[time_line_index + 1 :])
            subtitles.append({"start": start_ms, "end": end_ms, "text": text})
        return subtitles

    def save(self, subtitles: list[dict]) -> None:
        """Valida e grava a lista de legendas de forma atômica."""

        validated: list[dict] = []
        for index, subtitle in enumerate(subtitles, start=1):
            start = subtitle.get("start")
            end = subtitle.get("end")
            text = subtitle.get("text", "")
            if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                raise ValueError(f"A legenda {index} possui início inválido")
            if isinstance(end, bool) or not isinstance(end, int) or end < start:
                raise ValueError(f"A legenda {index} termina antes de começar")
            if not isinstance(text, str):
                raise TypeError(f"O texto da legenda {index} é inválido")
            validated.append({"start": start, "end": end, "text": text})

        validated.sort(key=lambda item: item["start"])
        blocks = [
            f"{index}\n{fmt_srt_time(subtitle['start'])} --> {fmt_srt_time(subtitle['end'])}\n{subtitle['text']}"
            for index, subtitle in enumerate(validated, start=1)
        ]
        content = "\n\n".join(blocks) + "\n" if blocks else ""
        _atomic_write_text(Path(self.srt_path), content)
