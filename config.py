from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app_storage import StorageError, open_storage


def _application_dir() -> Path:
    """Retorna o diretório que contém o código-fonte ou o executável empacotado."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = _application_dir() / "config.vdb"

DEFAULT_CONFIG: dict[str, Any] = {
    "update_ms": 500,
    "small_jump": 5,
    "large_jump": 20,
    "video_scroll_jump": 5,
    "track_scroll_jump": 20,
    "volume": 100,
    "always_on_top": False,
    "window_geometry": "",
    "last_video": "",
    "keys": {
        "play_pause": "<space>",
        "back_small": "<Left>",
        "fwd_small": "<Right>",
        "back_large": "<Shift-Left>",
        "fwd_large": "<Shift-Right>",
    },
}


class ConfigLoadError(RuntimeError):
    """Indica que a configuração não pôde ser lida sem risco de perda."""

    def __init__(self, path: Path, backup_path: Path | None, reason: Exception) -> None:
        """Registra o arquivo afetado, seu backup e a causa original."""

        self.path = path
        self.backup_path = backup_path
        self.reason = reason
        super().__init__(f"Não foi possível carregar {path}: {reason}")


def default_config() -> dict[str, Any]:
    """Retorna uma cópia independente da configuração padrão."""

    return deepcopy(DEFAULT_CONFIG)


def _deep_update(base: dict[str, Any], updates: dict[str, Any]) -> None:
    """Atualiza ``base`` recursivamente com valores de ``updates``."""

    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    """Normaliza um inteiro para o intervalo permitido ou retorna o padrão."""

    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if minimum <= parsed <= maximum else default


def normalize_config(config: object) -> dict[str, Any]:
    """Valida tipos e limites da configuração, restaurando campos inválidos."""

    normalized = default_config()
    if not isinstance(config, dict):
        return normalized

    normalized["update_ms"] = _bounded_int(config.get("update_ms"), 500, 50, 60_000)
    normalized["small_jump"] = _bounded_int(config.get("small_jump"), 5, 1, 3_600)
    normalized["large_jump"] = _bounded_int(config.get("large_jump"), 20, 1, 3_600)
    normalized["video_scroll_jump"] = _bounded_int(config.get("video_scroll_jump"), 5, 1, 3_600)
    normalized["track_scroll_jump"] = _bounded_int(config.get("track_scroll_jump"), 20, 1, 3_600)
    normalized["volume"] = _bounded_int(config.get("volume"), 100, 0, 100)
    normalized["always_on_top"] = config.get("always_on_top", False) is True

    for field in ("window_geometry", "last_video"):
        value = config.get(field, "")
        normalized[field] = value if isinstance(value, str) else ""

    keys = config.get("keys", {})
    if isinstance(keys, dict):
        for name, default_value in DEFAULT_CONFIG["keys"].items():
            value = keys.get(name)
            normalized["keys"][name] = value.strip() if isinstance(value, str) and value.strip() else default_value
    return normalized


def _backup_corrupted_config(path: Path) -> Path | None:
    """Copia uma configuração problemática para um arquivo de recuperação."""

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.corrompido_{timestamp}.bak")
    try:
        shutil.copy2(path, backup_path)
    except OSError:
        return None
    return backup_path


def load_config() -> dict[str, Any]:
    """Carrega e normaliza a configuração armazenada ao lado da aplicação."""

    path = Path(CONFIG_PATH)
    try:
        with open_storage(path) as connection:
            loaded = {key: json.loads(value) for key, value in connection.execute("SELECT key, value FROM settings")}
    except StorageError as exc:
        raise ConfigLoadError(exc.path, _backup_corrupted_config(exc.path), exc) from exc
    return normalize_config(loaded)


def save_config(config: dict[str, Any]) -> None:
    """Grava todas as preferências em uma transação, preservando a biblioteca."""

    path = Path(CONFIG_PATH)
    normalized = normalize_config(config)
    with open_storage(path) as connection:
        for (stored_value,) in connection.execute("SELECT value FROM settings"):
            json.loads(stored_value)
        connection.executemany(
            "INSERT INTO settings VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            [(key, json.dumps(value, ensure_ascii=False)) for key, value in normalized.items()],
        )
    config.clear()
    config.update(deepcopy(normalized))
