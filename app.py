import tkinter as tk
from tkinter import filedialog

from config import load_config, save_config
from gui import ChapterEditor, SettingsWindow


def main() -> None:
    """Inicializa a interface gráfica e executa o aplicativo."""

    root = tk.Tk()
    root.title("Editor de Capítulos")

    config = load_config()
    editor: ChapterEditor | None = None
    last_video_path = config.get("last_video", "")

    def open_video() -> None:
        """Abre um vídeo e cria o widget do editor."""

        nonlocal editor
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
    file_menu.add_command(label="Abrir vídeo", command=open_video)
    file_menu.add_separator()
    file_menu.add_command(label="Sair", command=root.quit)
    menubar.add_cascade(label="Arquivo", menu=file_menu)

    menubar.add_command(label="Configurações", command=show_settings)
    root.config(menu=menubar)

    if last_video_path:
        editor = ChapterEditor(root, last_video_path, config)
    else:
        open_video()

    root.mainloop()
    save_config(config)


if __name__ == "__main__":
    main()
