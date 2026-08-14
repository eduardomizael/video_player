"""Script de automação para compilar a aplicação em um executável (.exe) no Windows."""

import os
import subprocess
import sys


def build_exe() -> None:
    """Compila o projeto gerando um arquivo executável único na pasta dist/."""
    print("[INFO] Iniciando compilacao do Editor de Capitulos...")

    app_name = "EditorDeCapitulos"
    entry_point = "app.py"

    # Comando do PyInstaller via módulo Python corrente
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name",
        app_name,
        entry_point,
    ]

    print(f"[BUILD] Executando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", f"{app_name}.exe"))
        print("\n[SUCESSO] Compilacao concluida com sucesso!")
        print(f"[OUTPUT] Executavel disponivel em: {exe_path}\n")
    else:
        print("\n[ERRO] Falha durante a compilacao.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build_exe()
