import tkinter as tk
from tkinter import filedialog

from gui import ChapterEditor


def main() -> None:
    root = tk.Tk()
    root.title("Editor de Capítulos")
    video = filedialog.askopenfilename(filetypes=[("Vídeo MP4", "*.mp4")])
    if video:
        ChapterEditor(root, video)
        root.mainloop()


if __name__ == "__main__":
    main()
