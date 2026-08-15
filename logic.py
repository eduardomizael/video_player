from __future__ import annotations

import os
import re
import shutil
import sqlite3
import tempfile
import uuid
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


def _new_id() -> str:
    """Cria um identificador estável para relacionamentos no arquivo ``.chp``."""

    return str(uuid.uuid4())


def _normalize_record_id(item: dict[str, Any], location: str) -> str:
    """Garante que um registro possua um identificador textual não vazio."""

    record_id = item.get("id")
    if record_id is None:
        record_id = _new_id()
        item["id"] = record_id
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError(f"{location} possui identificador inválido")
    return record_id


def _normalize_image_ids(item: dict[str, Any], location: str) -> list[str]:
    """Valida as referências de imagens atribuídas a um registro."""

    image_ids = item.setdefault("images", [])
    if not isinstance(image_ids, list) or any(not isinstance(image_id, str) or not image_id for image_id in image_ids):
        raise TypeError(f"{location} possui referências de imagens inválidas")
    if len(image_ids) != len(set(image_ids)):
        raise ValueError(f"{location} possui imagens repetidas")
    return image_ids


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

    record_id = _normalize_record_id(chapter, location)
    image_ids = _normalize_image_ids(chapter, location)
    normalized = {"id": record_id, "title": title.strip(), "start": start, "end": end, "subs": [], "images": image_ids}
    normalized["subs"] = [
        _validate_chapter(sub, f"{location}, subcapítulo {index}", normalized)
        for index, sub in enumerate(subs, start=1)
    ]
    if normalized["subs"]:
        normalized["end"] = max(normalized["end"], *(sub["end"] for sub in normalized["subs"]))
    return normalized


def _validate_metadata(items: object, location: str = "metadados") -> list[dict[str, Any]]:
    """Valida nós de metadados, permitindo valores apenas nas folhas."""

    if not isinstance(items, list):
        raise TypeError(f"{location} deve ser uma lista")

    normalized: list[dict[str, Any]] = []
    keys: set[str] = set()
    for index, item in enumerate(items, start=1):
        item_location = f"{location}, item {index}"
        if not isinstance(item, dict):
            raise TypeError(f"{item_location} não é um objeto")
        key = item.get("key")
        value = item.get("value", "")
        children = item.get("children", [])
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{item_location} possui chave inválida")
        key = key.strip()
        if key in keys:
            raise ValueError(f"{location} possui chaves repetidas: '{key}'")
        if not isinstance(value, str):
            raise TypeError(f"{item_location} possui valor inválido")
        record_id = _normalize_record_id(item, item_location)
        image_ids = _normalize_image_ids(item, item_location)
        normalized_children = _validate_metadata(children, f"{item_location} ({key})")
        if normalized_children and value:
            raise ValueError(f"{item_location} possui filhos e não pode ter valor")
        keys.add(key)
        normalized.append(
            {"id": record_id, "key": key, "value": value, "children": normalized_children, "images": image_ids}
        )
    return normalized


def _validate_casting(casting: object) -> list[dict[str, Any]]:
    """Valida os integrantes do elenco e suas imagens associadas."""

    if not isinstance(casting, list):
        raise TypeError("o campo 'casting' deve ser uma lista")
    normalized: list[dict[str, Any]] = []
    for index, member in enumerate(casting, start=1):
        location = f"casting, item {index}"
        if isinstance(member, str):
            member = {"id": _new_id(), "name": member, "images": []}
            casting[index - 1] = member
        if not isinstance(member, dict):
            raise TypeError(f"{location} não é um objeto")
        name = member.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{location} possui nome inválido")
        normalized.append(
            {
                "id": _normalize_record_id(member, location),
                "name": name.strip(),
                "images": _normalize_image_ids(member, location),
            }
        )
    return normalized


def _validate_images(images: object) -> list[dict[str, Any]]:
    """Valida imagens recortadas mantidas como BLOB no banco SQLite."""

    if not isinstance(images, list):
        raise TypeError("as imagens devem ser uma lista")
    normalized: list[dict[str, Any]] = []
    for index, image in enumerate(images, start=1):
        location = f"imagem {index}"
        if not isinstance(image, dict):
            raise TypeError(f"{location} não é um objeto")
        title = image.get("title", "")
        description = image.get("description", "")
        data = image.get("data")
        mime_type = image.get("mime_type")
        width = image.get("width")
        height = image.get("height")
        if not isinstance(title, str) or not isinstance(description, str):
            raise TypeError(f"{location} possui título ou descrição inválidos")
        if not isinstance(data, bytes) or not data:
            raise ValueError(f"{location} não possui conteúdo binário")
        if mime_type not in {"image/jpeg", "image/png"}:
            raise ValueError(f"{location} possui formato inválido")
        if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
            raise ValueError(f"{location} possui largura inválida")
        if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
            raise ValueError(f"{location} possui altura inválida")
        normalized.append(
            {
                "id": _normalize_record_id(image, location),
                "title": title.strip(),
                "description": description.strip(),
                "data": data,
                "mime_type": mime_type,
                "width": width,
                "height": height,
            }
        )
    return normalized


class ChapterManager:
    """Gerencia o arquivo SQLite ``.chp`` associado a um vídeo."""

    def __init__(self, video_path: str) -> None:
        """Cria um gerenciador para o arquivo de vídeo indicado."""

        self.chp_path = os.path.splitext(video_path)[0] + ".chp"

    @staticmethod
    def _connect(path: Path) -> sqlite3.Connection:
        """Abre uma conexão SQLite configurada para preservar integridade referencial."""

        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        """Cria as tabelas estáveis do formato ``.chp`` quando necessário."""

        connection.executescript("""
            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY, parent_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
                position INTEGER NOT NULL, title TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS casting (
                id TEXT PRIMARY KEY, position INTEGER NOT NULL, name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
                id TEXT PRIMARY KEY, parent_id TEXT REFERENCES metadata(id) ON DELETE CASCADE,
                position INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL DEFAULT '',
                UNIQUE(parent_id, key)
            );
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
                width INTEGER NOT NULL, height INTEGER NOT NULL, mime_type TEXT NOT NULL, data BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS image_links (
                image_id TEXT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
                record_type TEXT NOT NULL CHECK(record_type IN ('chapters', 'casting', 'metadata')),
                record_id TEXT NOT NULL, position INTEGER NOT NULL,
                PRIMARY KEY(image_id, record_type, record_id),
                UNIQUE(record_type, record_id, position)
            );
            """)

    @staticmethod
    def _image_links(connection: sqlite3.Connection) -> dict[tuple[str, str], list[str]]:
        """Lê os vínculos de imagens ordenados para cada registro do arquivo."""

        links: dict[tuple[str, str], list[str]] = {}
        for row in connection.execute("SELECT image_id, record_type, record_id FROM image_links ORDER BY position"):
            links.setdefault((row["record_type"], row["record_id"]), []).append(row["image_id"])
        return links

    def load(self) -> dict[str, Any]:
        """Carrega capítulos, elenco, metadados e imagens do arquivo ``.chp``."""

        path = Path(self.chp_path)
        if not path.exists():
            return {"chapters": [], "casting": [], "metadata": [], "images": []}
        try:
            with self._connect(path) as connection:
                self._create_schema(connection)
                links = self._image_links(connection)
                chapter_rows = connection.execute("SELECT * FROM chapters ORDER BY position").fetchall()
                metadata_rows = connection.execute("SELECT * FROM metadata ORDER BY position").fetchall()
                casting_rows = connection.execute("SELECT * FROM casting ORDER BY position").fetchall()
                image_rows = connection.execute("SELECT * FROM images").fetchall()
        except (OSError, sqlite3.DatabaseError) as exc:
            raise DataLoadError(path, str(exc)) from exc

        chapters_by_id = {
            row["id"]: {
                "id": row["id"],
                "title": row["title"],
                "start": row["start"],
                "end": row["end"],
                "subs": [],
                "images": links.get(("chapters", row["id"]), []),
            }
            for row in chapter_rows
        }
        chapters = []
        for row in chapter_rows:
            node = chapters_by_id[row["id"]]
            if row["parent_id"]:
                chapters_by_id[row["parent_id"]]["subs"].append(node)
            else:
                chapters.append(node)
        metadata_by_id = {
            row["id"]: {
                "id": row["id"],
                "key": row["key"],
                "value": row["value"],
                "children": [],
                "images": links.get(("metadata", row["id"]), []),
            }
            for row in metadata_rows
        }
        metadata = []
        for row in metadata_rows:
            node = metadata_by_id[row["id"]]
            if row["parent_id"]:
                metadata_by_id[row["parent_id"]]["children"].append(node)
            else:
                metadata.append(node)
        casting = [
            {"id": row["id"], "name": row["name"], "images": links.get(("casting", row["id"]), [])}
            for row in casting_rows
        ]
        images = [dict(row) for row in image_rows]
        return {
            "chapters": chapters,
            "casting": casting,
            "metadata": metadata,
            "images": images,
        }

    def save(
        self,
        chapters: list[dict],
        casting: list[dict],
        metadata: list[dict] | None = None,
        images: list[dict] | None = None,
    ) -> None:
        """Valida e grava todos os dados em uma única transação SQLite."""

        try:
            validated = [
                _validate_chapter(chapter, f"capítulo {index}") for index, chapter in enumerate(chapters, start=1)
            ]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Os capítulos não foram salvos: {exc}") from exc
        try:
            validated_metadata = _validate_metadata([] if metadata is None else metadata)
            validated_casting = _validate_casting(casting)
            validated_images = _validate_images([] if images is None else images)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Os dados não foram salvos: {exc}") from exc
        image_ids = {image["id"] for image in validated_images}

        def insert_links(connection: sqlite3.Connection, record_type: str, record: dict) -> None:
            for position, image_id in enumerate(record["images"]):
                if image_id not in image_ids:
                    raise ValueError(f"A imagem vinculada ao registro '{record['id']}' não existe")
                connection.execute(
                    "INSERT INTO image_links VALUES (?, ?, ?, ?)", (image_id, record_type, record["id"], position)
                )

        def insert_chapters(connection: sqlite3.Connection, nodes: list[dict], parent_id: str | None = None) -> None:
            for position, node in enumerate(nodes):
                connection.execute(
                    "INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?)",
                    (node["id"], parent_id, position, node["title"], node["start"], node["end"]),
                )
                insert_links(connection, "chapters", node)
                insert_chapters(connection, node["subs"], node["id"])

        def insert_metadata(connection: sqlite3.Connection, nodes: list[dict], parent_id: str | None = None) -> None:
            for position, node in enumerate(nodes):
                connection.execute(
                    "INSERT INTO metadata VALUES (?, ?, ?, ?, ?)",
                    (node["id"], parent_id, position, node["key"], node["value"]),
                )
                insert_links(connection, "metadata", node)
                insert_metadata(connection, node["children"], node["id"])

        path = Path(self.chp_path)
        try:
            with self._connect(path) as connection:
                self._create_schema(connection)
                connection.execute("DELETE FROM image_links")
                connection.execute("DELETE FROM chapters")
                connection.execute("DELETE FROM casting")
                connection.execute("DELETE FROM metadata")
                connection.execute("DELETE FROM images")
                connection.executemany(
                    "INSERT INTO images VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            image["id"],
                            image["title"],
                            image["description"],
                            image["width"],
                            image["height"],
                            image["mime_type"],
                            image["data"],
                        )
                        for image in validated_images
                    ],
                )
                insert_chapters(connection, validated)
                for position, member in enumerate(validated_casting):
                    connection.execute("INSERT INTO casting VALUES (?, ?, ?)", (member["id"], position, member["name"]))
                    insert_links(connection, "casting", member)
                insert_metadata(connection, validated_metadata)
        except (OSError, sqlite3.DatabaseError) as exc:
            raise ValueError(f"Os dados não foram salvos: {exc}") from exc


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
