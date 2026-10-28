"""Script de automação para compilar a aplicação em um executável (.exe) no Windows."""

import argparse
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path


def build_exe(webview: bool = False) -> None:
    """Gera um executável independente para a interface clássica ou webview."""
    print("[INFO] Iniciando compilacao do Editor de Capitulos...")

    root = Path(__file__).resolve().parent
    app_name = "EditorDeCapitulosWebview" if webview else "EditorDeCapitulos"
    entry_point = "web_app.py" if webview else "app.py"
    if webview and find_spec("webview") is None:
        raise SystemExit("Instale a dependencia opcional: uv sync --extra webview --dev")

    # Comando do PyInstaller via módulo Python corrente
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--name",
        app_name,
        "--distpath",
        str(root / "dist"),
        "--workpath",
        str(root / "build" / app_name),
        "--specpath",
        str(root / "build" / "specs"),
    ]
    if webview:
        cmd.extend(
            [
                "--icon",
                str(root / "web_ui" / "app-icon.ico"),
                "--add-data",
                f"{root / 'web_ui'}:web_ui",
                "--collect-data",
                "webview",
                "--collect-binaries",
                "webview",
                "--hidden-import",
                "_cffi_backend",
                "--exclude-module",
                "tkinter",
                "--exclude-module",
                "vlc",
            ]
        )
        if sys.platform == "win32":
            cmd.extend(
                [
                    "--hidden-import",
                    "webview.platforms.winforms",
                    "--hidden-import",
                    "webview.platforms.edgechromium",
                    "--exclude-module",
                    "webview.platforms.qt",
                    "--exclude-module",
                    "webview.platforms.gtk",
                    "--exclude-module",
                    "webview.platforms.cocoa",
                    "--exclude-module",
                    "webview.platforms.android",
                    "--exclude-module",
                    "webview.platforms.cef",
                ]
            )
    cmd.append(str(root / entry_point))

    print(f"[BUILD] Executando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=False, cwd=root)

    if result.returncode == 0:
        exe_path = root / "dist" / f"{app_name}.exe"
        print("\n[SUCESSO] Compilacao concluida com sucesso!")
        print(f"[OUTPUT] Executavel disponivel em: {exe_path}\n")
    else:
        print("\n[ERRO] Falha durante a compilacao.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o executavel da interface escolhida.")
    parser.add_argument("--webview", action="store_true", help="Gera a interface webview em um executavel separado.")
    build_exe(webview=parser.parse_args().webview)
