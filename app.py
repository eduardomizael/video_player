import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from config import load_config, save_config


def check_vlc_installed() -> bool:
    """Verifica se o VLC Media Player está instalado e acessível no sistema."""
    try:
        import vlc

        instance = vlc.Instance()
        if instance is None:
            return False
        instance.release()
        return True
    except Exception:
        return False


def reveal_in_explorer(file_path: str) -> None:
    """Abre o gerenciador de arquivos do sistema operacional e seleciona o arquivo de vídeo."""
    if not file_path or not os.path.exists(file_path):
        return
    norm_path = os.path.normpath(file_path)
    if os.name == "nt":
        import subprocess

        subprocess.Popen(["explorer", "/select,", norm_path])
    elif sys.platform == "darwin":
        import subprocess

        subprocess.Popen(["open", "-R", norm_path])
    else:
        import subprocess

        subprocess.Popen(["xdg-open", os.path.dirname(norm_path)])


def main() -> None:
    """Inicializa a interface gráfica e executa o aplicativo."""
    if not check_vlc_installed():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "VLC Não Encontrado",
            "O VLC Media Player não foi encontrado no sistema.\n\n"
            "Ele é necessário para a execução deste aplicativo.\n"
            "Por favor, instale o VLC Media Player (versão 64-bit) e tente novamente.",
        )
        root.destroy()
        sys.exit(1)

    from gui import ChapterEditor, SettingsWindow

    root = tk.Tk()
    root.title("Editor de Capítulos")

    config = load_config()

    # Função para centralizar a janela na tela se não houver posição salva
    def center_window(width: int = 1050, height: int = 650) -> None:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        root.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    # Restaura a última geometria/posição salva da janela ou centraliza
    saved_geom = config.get("window_geometry", "")
    if saved_geom:
        try:
            root.geometry(saved_geom)
        except Exception:
            center_window()
    else:
        center_window()

    editor: ChapterEditor | None = None
    last_video_path = config.get("last_video", "")

    # Barra superior com o caminho do vídeo selecionável e o botão do explorador
    path_frame = tk.Frame(root, bd=1, relief="groove")
    path_frame.pack(fill="x", side="top", padx=4, pady=(4, 2))

    tk.Label(path_frame, text=" Arquivo: ").pack(side="left")

    path_var = tk.StringVar(value="")
    path_entry = tk.Entry(path_frame, textvariable=path_var, state="readonly")
    path_entry.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=2)

    browse_btn = tk.Button(
        path_frame,
        text="📁",
        command=lambda: reveal_in_explorer(path_var.get()),
        width=3,
        cursor="hand2",
    )
    browse_btn.pack(side="right", padx=2, pady=2)

    def open_video(path: str = "") -> None:
        """Abre um vídeo e cria o widget do editor."""
        nonlocal editor
        if not path:
            path = filedialog.askopenfilename(
                filetypes=[
                    ("Vídeo MP4", "*.mp4"),
                    ("Videos AVI", "*.avi"),
                    ("Todos os arquivos", "*.*"),
                ]
            )
        if not path:
            return
        if editor:
            editor.destroy()
        editor = ChapterEditor(root, path, config)
        config["last_video"] = path
        abs_path = os.path.abspath(path)
        path_var.set(abs_path)

    def show_settings() -> None:
        """Exibe a janela de configurações."""
        SettingsWindow(root, config, lambda: editor.update_config(config) if editor else None)

    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Abrir vídeo", command=lambda: open_video())
    file_menu.add_separator()
    file_menu.add_command(label="Sair", command=root.quit)
    menubar.add_cascade(label="Arquivo", menu=file_menu)

    menubar.add_command(label="Configurações", command=show_settings)
    root.config(menu=menubar)

    # Verifica se foi passado um arquivo de vídeo via argumento
    video_arg = ""
    if len(sys.argv) > 1:
        video_arg = sys.argv[1]

    if video_arg:
        open_video(video_arg)
    elif last_video_path and os.path.exists(last_video_path):
        open_video(last_video_path)
    else:
        open_video()

    def on_closing() -> None:
        """Salva a geometria da janela ao fechar a aplicação."""
        config["window_geometry"] = root.geometry()
        save_config(config)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
