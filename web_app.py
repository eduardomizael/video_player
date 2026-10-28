"""Entrada independente da interface webview, sem importar Tkinter ou VLC."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from config import ConfigLoadError, default_config, load_config
from web_backend import EditorSession, MediaServer


class WebApi:
    """Expõe somente operações de edição e seletores nativos para a página local."""

    def __init__(self, session: EditorSession, settings: dict, startup_error: str = "") -> None:
        """Mantém a sessão e recebe a janela depois de sua criação."""
        self._session = session
        self._settings = settings
        self._startup_error = startup_error
        self._window: Any = None
        self._fullscreen = False
        self._saving = False

    def get_state(self) -> dict:
        """Fornece o estado inicial e as preferências de reprodução existentes."""
        return self._session.snapshot() | {"settings": self._settings, "startup_error": self._startup_error}

    def open_video(self) -> dict | None:
        """Solicita um vídeo pelo seletor do sistema sem aceitar caminhos da página."""
        import webview

        paths = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("Vídeos (*.mp4;*.m4v;*.webm;*.mov;*.mkv;*.avi;*.ogv)", "Todos os arquivos (*.*)"),
        )
        return self._session.open(paths[0]) if paths else None

    def save_section(self, section: str, items: list[dict], revision: int) -> dict:
        """Persiste uma seção pelos mesmos gerenciadores usados no Tkinter."""
        self._saving = True
        try:
            return self._session.save(section, items, revision)
        finally:
            self._saving = False

    def set_edit_state(self, pending: bool) -> None:
        """Atualiza a confirmação nativa sem consultar JavaScript durante o fechamento."""
        self._window.confirm_close = bool(pending)

    def set_fullscreen(self, active: bool) -> None:
        """Sincroniza a tela cheia do vídeo com a janela nativa nos diferentes sistemas."""
        if bool(active) != self._fullscreen:
            self._window.toggle_fullscreen()
            self._fullscreen = bool(active)


def main() -> None:
    """Inicializa o servidor local e a janela webview com tratamento de encerramento."""
    parser = argparse.ArgumentParser(description="Editor de capítulos — interface webview")
    parser.add_argument("video", nargs="?", help="Vídeo a abrir inicialmente")
    args = parser.parse_args()
    try:
        import webview
    except ImportError:
        parser.exit(1, "Instale as dependências opcionais: uv sync --extra webview --dev\n")
    error = ""
    try:
        settings = load_config()
    except ConfigLoadError as exc:
        settings, error = default_config(), str(exc)
    session = EditorSession()
    if args.video:
        try:
            session.open(args.video)
        except (OSError, ValueError, RuntimeError) as exc:
            error = str(exc)
    server = MediaServer(session)
    api = WebApi(session, settings, error)
    try:
        api._window = webview.create_window(
            "Editor de Capítulos",
            server.start(),
            js_api=api,
            width=1440,
            height=900,
            min_size=(860, 620),
            background_color="#111318",
            on_top=settings.get("always_on_top", False),
        )

        def can_close() -> bool:
            """Protege gravações em andamento e edições ainda não confirmadas."""
            return not api._saving

        api._window.events.closing += can_close
        webview.start(
            gui="edgechromium" if sys.platform == "win32" else None,
            localization={"global.quitConfirmation": "Descartar a edição não salva e fechar?"},
            icon=str(
                Path(__file__).resolve().parent
                / "web_ui"
                / ("app-icon.ico" if sys.platform == "win32" else "app-icon.png")
            ),
        )
    finally:
        server.close()


if __name__ == "__main__":
    main()
