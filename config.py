from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _application_dir() -> Path:
    """Retorna o diretório que contém o código-fonte ou o executável empacotado."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


CONFIG_PATH = _application_dir() / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "update_ms": 500,
    "small_jump": 5,
    "large_jump": 20,
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
    if not path.exists():
        return default_config()

    try:
        with path.open("r", encoding="utf-8") as file_handle:
            loaded = json.load(file_handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigLoadError(path, _backup_corrupted_config(path), exc) from exc
    if not isinstance(loaded, dict):
        reason = TypeError("a raiz da configuração deve ser um objeto JSON")
        raise ConfigLoadError(path, _backup_corrupted_config(path), reason)
    return normalize_config(loaded)


def save_config(config: dict[str, Any]) -> None:
    """Grava a configuração de forma atômica ao lado da aplicação."""

    path = Path(CONFIG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_config(config)
    config.clear()
    config.update(deepcopy(normalized))

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file_handle:
            json.dump(normalized, file_handle, ensure_ascii=False, indent=2)
            file_handle.write("\n")
            file_handle.flush()
            os.fsync(file_handle.fileno())
            temporary_path = Path(file_handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
