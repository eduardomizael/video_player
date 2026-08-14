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
    editor: ChapterEditor | None = None
    last_video_path = config.get("last_video", "")

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
    elif last_video_path:
        open_video(last_video_path)
    else:
        open_video()

    root.mainloop()
    save_config(config)


if __name__ == "__main__":
    main()
