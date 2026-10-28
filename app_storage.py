"""Banco único da aplicação com migração transacional dos arquivos anteriores."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path


class StorageError(OSError):
    """Informa uma falha de armazenamento sem permitir a restauração destrutiva."""

    def __init__(self, path: Path, reason: Exception) -> None:
        """Identifica o arquivo que impediu a leitura, migração ou gravação."""
        self.path = path
        super().__init__(f"Não foi possível acessar {path}: {reason}")


def _legacy_settings(path: Path) -> dict:
    """Lê as preferências antigas sem modificar seu arquivo de origem."""
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise TypeError("a raiz da configuração deve ser um objeto JSON")
        return loaded
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise StorageError(path, exc) from exc


def _legacy_history(path: Path) -> list[tuple[str, str, str]]:
    """Lê o histórico anterior em modo somente leitura, incluindo vídeos indisponíveis."""
    if not path.exists():
        return []
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            return connection.execute("SELECT key, path, accessed FROM videos").fetchall()
    except sqlite3.Error as exc:
        raise StorageError(path, exc) from exc


@contextmanager
def open_storage(path: Path) -> Iterator[sqlite3.Connection]:
    """Abre uma transação e migra as fontes antigas uma única vez, sem apagá-las."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            version = connection.execute("SELECT value FROM app_metadata WHERE key='schema_version'").fetchone()
            if version is not None and version[0] != "1":
                raise ValueError("versão do banco incompatível com esta aplicação")
            connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS videos (key TEXT PRIMARY KEY, path TEXT NOT NULL, accessed TEXT NOT NULL)"
            )
            if version is None:
                settings = _legacy_settings(path.with_name("config.json"))
                history = _legacy_history(path.with_name("video_history.sqlite3"))
                connection.executemany(
                    "INSERT INTO settings VALUES (?, ?)",
                    [(key, json.dumps(value, ensure_ascii=False)) for key, value in settings.items()],
                )
                connection.executemany("INSERT INTO videos VALUES (?, ?, ?)", history)
                connection.execute("INSERT INTO app_metadata VALUES ('schema_version', '1')")
            yield connection
    except StorageError:
        raise
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise StorageError(path, exc) from exc
