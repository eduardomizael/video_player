import tkinter as tk
from tkinter import filedialog

from config import load_config, save_config
from gui import ChapterEditor, SettingsWindow


def main() -> None:
    root = tk.Tk()
    root.title("Editor de Capítulos")

    config = load_config()
    editor: ChapterEditor | None = None

    def open_video() -> None:
        nonlocal editor
        path = filedialog.askopenfilename(filetypes=[("Vídeo MP4", "*.mp4")])
        if not path:
            return
        if editor:
            editor.destroy()
        editor = ChapterEditor(root, path, config)

    def show_settings() -> None:
        SettingsWindow(root, config, lambda: editor.update_config(config) if editor else None)

    menubar = tk.Menu(root)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Abrir vídeo", command=open_video)
    file_menu.add_separator()
    file_menu.add_command(label="Sair", command=root.quit)
    menubar.add_cascade(label="Arquivo", menu=file_menu)

    menubar.add_command(label="Configurações", command=show_settings)
    root.config(menu=menubar)

    open_video()
    root.mainloop()
    save_config(config)


if __name__ == "__main__":
    main()
