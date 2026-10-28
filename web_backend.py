"""Sessão compartilhada de edição e entrega local de mídia para a interface web."""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import mimetypes
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from logic import ChapterManager, SubtitleManager


class EditorSession:
    """Isola a sessão web e reutiliza os formatos e validadores da interface clássica."""

    def __init__(self) -> None:
        """Inicializa uma sessão vazia sem depender de Tkinter ou VLC."""
        self.lock = threading.RLock()
        self.path: Path | None = None
        self.data: dict[str, Any] = {}
        self.subtitles: list[dict] = []
        self.revision = 0
        self.media_id = secrets.token_urlsafe(24)
        self.base_url = ""
        self.signatures: dict[str, str] = {}

    def _signature(self, suffix: str) -> str:
        """Identifica alterações externas nos arquivos antes de sobrescrevê-los."""
        assert self.path is not None
        path = self.path.with_suffix(suffix)
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "ausente"

    def open(self, path: str) -> dict:
        """Abre o vídeo somente depois de carregar todos os seus dados com sucesso."""
        with self.lock:
            candidate = Path(path).resolve(strict=True)
            if not candidate.is_file():
                raise ValueError("Selecione um arquivo de vídeo.")
            data = ChapterManager(str(candidate)).load()
            subtitles = SubtitleManager(str(candidate)).load()
            self.path, self.data, self.subtitles = candidate, data, subtitles
            self.media_id = secrets.token_urlsafe(24)
            self.signatures = {suffix: self._signature(suffix) for suffix in (".chp", ".srt")}
            self.revision += 1
            return self.snapshot()

    def snapshot(self) -> dict:
        """Retorna uma representação JSON sem expor objetos binários ao JavaScript."""
        with self.lock:
            data = copy.deepcopy(self.data)
            for image in data.get("images", []):
                image["source"] = f"data:{image['mime_type']};base64," + base64.b64encode(image.pop("data")).decode(
                    "ascii"
                )
            return {
                "name": self.path.name if self.path else "",
                "path": str(self.path) if self.path else "",
                "media_url": f"{self.base_url}/media/{self.media_id}" if self.path else "",
                "revision": self.revision,
                "data": data,
                "subtitles": copy.deepcopy(self.subtitles),
            }

    def save(self, section: str, items: list[dict], revision: int) -> dict:
        """Grava uma seção preservando as demais e rejeita sessões desatualizadas."""
        with self.lock:
            if self.path is None:
                raise ValueError("Abra um vídeo primeiro.")
            if revision != self.revision:
                raise ValueError("A sessão mudou. Reabra o editor do item e tente novamente.")
            if section not in {"chapters", "casting", "metadata", "images", "subtitles"}:
                raise ValueError("Seção desconhecida.")
            suffix = ".srt" if section == "subtitles" else ".chp"
            if self._signature(suffix) != self.signatures[suffix]:
                raise ValueError("O arquivo foi alterado por outro programa. Reabra o vídeo antes de salvar.")
            if not isinstance(items, list):
                raise TypeError("Os registros devem formar uma lista.")
            if section == "subtitles":
                SubtitleManager(str(self.path)).save(items)
                self.subtitles = SubtitleManager(str(self.path)).load()
            else:
                data = copy.deepcopy(self.data)
                if section == "images":
                    originals = {image["id"]: image for image in data["images"]}
                    prepared = []
                    for item in items:
                        image = copy.deepcopy(item)
                        if image.get("id") in originals:
                            image = originals[image["id"]] | {
                                "title": image.get("title", ""),
                                "description": image.get("description", ""),
                            }
                        else:
                            raw = base64.b64decode(image.pop("source").split(",", 1)[1], validate=True)
                            if len(raw) > 20 * 1024 * 1024:
                                raise ValueError("A imagem deve ter no máximo 20 MB.")
                            with Image.open(io.BytesIO(raw)) as original:
                                original.load()
                                normalized = ImageOps.exif_transpose(original).convert("RGB")
                                output = io.BytesIO()
                                normalized.save(output, "JPEG", quality=92)
                                image.update(
                                    data=output.getvalue(),
                                    mime_type="image/jpeg",
                                    width=normalized.width,
                                    height=normalized.height,
                                )
                        prepared.append(image)
                    items = prepared
                    retained = {image["id"] for image in items}

                    def remove_links(nodes: list[dict]) -> None:
                        """Remove vínculos de imagens excluídas em qualquer nível da árvore."""
                        for node in nodes:
                            node["images"] = [key for key in node.get("images", []) if key in retained]
                            remove_links(node.get("subs", node.get("children", [])))

                    for name in ("chapters", "casting", "metadata"):
                        remove_links(data[name])
                data[section] = items

                def sort_chapters(nodes: list[dict]) -> None:
                    """Mantém os irmãos ordenados pelo início, como na interface clássica."""
                    nodes.sort(key=lambda node: node["start"])
                    for node in nodes:
                        sort_chapters(node.get("subs", []))

                sort_chapters(data["chapters"])
                manager = ChapterManager(str(self.path))
                manager.save(data["chapters"], data["casting"], data["metadata"], data["images"])
                self.data = manager.load()
            self.signatures[suffix] = self._signature(suffix)
            self.revision += 1
            return self.snapshot()


class MediaServer:
    """Entrega apenas os recursos da aplicação e o vídeo selecionado em loopback."""

    def __init__(self, session: EditorSession) -> None:
        """Reserva uma porta dinâmica e um caminho secreto por execução."""
        self.session = session
        self.token = secrets.token_urlsafe(32)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            """Responde a leituras locais, incluindo intervalos de bytes de vídeo."""

            def log_message(self, format: str, *args: object) -> None:
                """Evita registrar caminhos e tokens da sessão no terminal."""

            def do_HEAD(self) -> None:
                """Retorna os mesmos cabeçalhos de uma leitura sem enviar conteúdo."""
                self._serve(head=True)

            def do_GET(self) -> None:
                """Entrega um recurso autorizado ou um intervalo do vídeo."""
                self._serve(head=False)

            def _serve(self, head: bool) -> None:
                """Valida a rota antes de abrir qualquer arquivo no computador."""
                prefix = f"/{owner.token}/"
                if self.headers.get("Host") != f"127.0.0.1:{owner.server.server_port}":
                    self.send_error(403)
                    return
                if not self.path.startswith(prefix):
                    self.send_error(404)
                    return
                route = self.path[len(prefix) :].split("?", 1)[0]
                with session.lock:
                    media = route == f"media/{session.media_id}" and session.path is not None
                    path = session.path if media else None
                if not media:
                    if route not in {"", "index.html", "app.js", "style.css", "app-icon.svg"}:
                        self.send_error(404)
                        return
                    path = Path(__file__).parent / "web_ui" / (route or "index.html")
                assert path is not None
                try:
                    with path.open("rb") as stream:
                        size = path.stat().st_size
                        start, end = 0, size - 1
                        ranged = self.headers.get("Range") if media else None
                        if ranged:
                            match = re.fullmatch(r"bytes=(\d*)-(\d*)", ranged)
                            if match and any(match.groups()):
                                left, right = match.groups()
                                if left:
                                    start = int(left)
                                    end = min(int(right), size - 1) if right else size - 1
                                else:
                                    start = max(0, size - int(right))
                            else:
                                start = size
                            if start > end or start >= size:
                                self.send_response(416)
                                self.send_header("Content-Range", f"bytes */{size}")
                                self.send_header("Content-Length", "0")
                                self.end_headers()
                                return
                        self.send_response(206 if ranged else 200)
                        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                        self.send_header("Content-Type", mime)
                        self.send_header("Content-Length", str(max(0, end - start + 1)))
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Referrer-Policy", "no-referrer")
                        self.send_header("X-Content-Type-Options", "nosniff")
                        if media:
                            self.send_header("Accept-Ranges", "bytes")
                        if ranged:
                            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                        self.end_headers()
                        if not head:
                            stream.seek(start)
                            remaining = end - start + 1
                            while remaining > 0:
                                chunk = stream.read(min(256 * 1024, remaining))
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                remaining -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                except OSError:
                    self.send_error(404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        session.base_url = f"http://127.0.0.1:{self.server.server_port}/{self.token}"

    def start(self) -> str:
        """Inicia a entrega em segundo plano e retorna a página inicial."""
        self.thread.start()
        return self.session.base_url + "/"

    def close(self) -> None:
        """Encerra a escuta local e libera a porta ao fechar a aplicação."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
