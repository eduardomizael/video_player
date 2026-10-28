"""Biblioteca persistente de vídeos que possuem recursos de edição salvos."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import config
from app_storage import open_storage

VIDEO_SUFFIXES = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".ogv"}


class VideoHistory:
    """Mantém a biblioteca no mesmo banco das configurações da aplicação."""

    def __init__(self, path: Path | None = None) -> None:
        """Define o banco ao lado da aplicação sem criá-lo durante a inicialização."""
        self.path = path if path is not None else Path(config.CONFIG_PATH)

    @staticmethod
    def _key(path: Path) -> str:
        """Normaliza caminhos equivalentes para impedir entradas duplicadas."""
        return os.path.normcase(str(path.resolve()))

    def _write(self, entries: list[tuple[str, str, str]]) -> None:
        """Insere ou atualiza os registros em uma transação sem descartar o histórico."""
        if not entries:
            return
        with open_storage(self.path) as connection:
            connection.executemany(
                "INSERT INTO videos VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                "path=excluded.path, accessed=MAX(videos.accessed, excluded.accessed)",
                entries,
            )

    def remember(self, video: Path) -> bool:
        """Registra somente vídeos existentes com arquivo CHP ou SRT salvo."""
        video = video.resolve()
        if not video.is_file() or not any(video.with_suffix(suffix).is_file() for suffix in (".chp", ".srt")):
            return False
        self._write([(self._key(video), str(video), datetime.now(UTC).isoformat())])
        return True

    def entries(self) -> list[dict]:
        """Lista os vídeos por acesso recente e sinaliza caminhos indisponíveis."""
        with open_storage(self.path) as connection:
            rows = connection.execute("SELECT key, path, accessed FROM videos ORDER BY accessed DESC, key").fetchall()
        return [
            {"id": key, "path": path, "name": Path(path).name, "accessed": accessed, "available": Path(path).is_file()}
            for key, path, accessed in rows
        ]

    def resolve(self, identifier: str) -> Path:
        """Autoriza a abertura apenas de um vídeo previamente registrado no índice."""
        entry = next((entry for entry in self.entries() if entry["id"] == identifier), None)
        if entry is None:
            raise ValueError("O vídeo não está na biblioteca.")
        if not entry["available"]:
            raise FileNotFoundError("Vídeo indisponível. O arquivo pode ter sido movido ou apagado.")
        return Path(entry["path"])

    def import_folder(self, folder: Path) -> int:
        """Localiza recursivamente vídeos com CHP ou SRT na pasta escolhida pelo usuário."""
        entries = []

        def raise_error(error: OSError) -> None:
            """Interrompe a descoberta quando uma pasta não pode ser lida."""
            raise error

        for directory, _, filenames in os.walk(folder, onerror=raise_error):
            resources = {
                os.path.normcase(Path(name).stem) for name in filenames if Path(name).suffix.lower() in {".chp", ".srt"}
            }
            for name in filenames:
                video = Path(directory, name)
                if video.suffix.lower() not in VIDEO_SUFFIXES or os.path.normcase(video.stem) not in resources:
                    continue
                modified = max(
                    video.with_suffix(suffix).stat().st_mtime
                    for suffix in (".chp", ".srt")
                    if video.with_suffix(suffix).is_file()
                )
                entries.append(
                    (self._key(video), str(video.resolve()), datetime.fromtimestamp(modified, UTC).isoformat())
                )
        self._write(entries)
        return len(entries)
