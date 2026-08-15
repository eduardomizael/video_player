import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from config import ConfigLoadError, default_config, load_config, save_config
from logic import DataLoadError


def check_vlc_installed() -> bool:
    """Verifica se o VLC Media Player está instalado e acessível no sistema."""
    try:
        import vlc

        instance = vlc.Instance()
        if instance is None:
            return False
        instance.release()
        return True
    except (ImportError, OSError, AttributeError):
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


class AboutDialog(tk.Toplevel):
    """Janela modal detalhada com informações sobre a aplicação."""

    def __init__(self, master: tk.Tk) -> None:
        """Cria e posiciona o diálogo modal Sobre."""
        super().__init__(master)
        self.title("Sobre - Editor de Capítulos")
        self.resizable(False, False)
        self.transient(master)
        self.attributes("-topmost", True)

        main_frame = tk.Frame(self, padx=24, pady=20)
        main_frame.pack(fill="both", expand=True)

        title_lbl = tk.Label(
            main_frame,
            text="Editor de Capítulos e Legendas",
            font=("Segoe UI", 14, "bold"),
            fg="#005a9e",
        )
        title_lbl.pack(pady=(0, 4))

        version_lbl = tk.Label(
            main_frame,
            text="Versão 1.2.0",
            font=("Segoe UI", 9, "italic"),
            fg="#666666",
        )
        version_lbl.pack(pady=(0, 12))

        desc_text = (
            "Aplicativo desktop completo para reprodução de vídeos, edição de capítulos,\n"
            "gerenciamento de legendas (.srt com tempo estendido) e elenco (casting).\n\n"
            "Desenvolvido com Python 3.12, Tkinter e VLC Media Player."
        )
        desc_lbl = tk.Label(main_frame, text=desc_text, font=("Segoe UI", 9), justify="center")
        desc_lbl.pack(pady=(0, 16))

        btn = tk.Button(
            main_frame,
            text="OK",
            command=self.destroy,
            width=10,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        btn.pack()

        self.grab_set()
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = master.winfo_x() + (master.winfo_width() - width) // 2
        y = master.winfo_y() + (master.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")


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

    try:
        config = load_config()
    except ConfigLoadError as exc:
        config = default_config()
        backup_message = f"\n\nUma cópia foi preservada em:\n{exc.backup_path}" if exc.backup_path else ""
        messagebox.showwarning(
            "Configuração restaurada",
            f"O arquivo de configuração estava ilegível e os valores padrão serão restaurados.{backup_message}",
        )
        try:
            save_config(config)
        except OSError as save_error:
            messagebox.showerror("Erro ao salvar configuração", str(save_error))

    # Aplica configuração de Sempre no Topo (Always on Top)
    always_on_top_var = tk.BooleanVar(value=config.get("always_on_top", False))
    root.attributes("-topmost", always_on_top_var.get())

    def toggle_always_on_top() -> None:
        """Alterna o modo sempre no topo e persiste a preferência."""

        val = always_on_top_var.get()
        root.attributes("-topmost", val)
        config["always_on_top"] = val
        try:
            save_config(config)
        except OSError as exc:
            messagebox.showerror("Configuração não salva", str(exc))

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
        except tk.TclError:
            center_window()
    else:
        center_window()

    editor: ChapterEditor | None = None
    last_video_path = config.get("last_video", "")

    # Barra superior com o caminho do vídeo selecionável e o botão do explorador
    path_frame = tk.Frame(root, bd=0, relief="flat")
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
        abs_path = os.path.abspath(path)
        if not os.path.isfile(abs_path):
            messagebox.showerror("Vídeo não encontrado", f"O arquivo informado não existe:\n{abs_path}")
            return
        try:
            new_editor = ChapterEditor(root, abs_path, config)
        except (DataLoadError, OSError, ValueError, RuntimeError, tk.TclError) as exc:
            messagebox.showerror("Não foi possível abrir o vídeo", str(exc))
            return
        if editor:
            editor.destroy()
        editor = new_editor
        config["last_video"] = abs_path
        path_var.set(abs_path)

    def show_settings() -> None:
        """Exibe a janela de configurações."""
        SettingsWindow(root, config, lambda: editor.update_config(config) if editor else None)

    def show_about() -> None:
        """Exibe a janela modal Sobre."""
        AboutDialog(root)

    def on_closing() -> None:
        """Salva a configuração e libera o VLC antes de fechar a aplicação."""

        config["window_geometry"] = root.geometry()
        try:
            save_config(config)
        except OSError as exc:
            if not messagebox.askyesno(
                "Configuração não salva",
                f"Não foi possível salvar a configuração:\n{exc}\n\nDeseja fechar mesmo assim?",
            ):
                return
        if editor:
            editor.destroy()
        root.destroy()

    menubar = tk.Menu(root)

    # Menu Arquivo
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Abrir vídeo", command=lambda: open_video())
    file_menu.add_separator()
    file_menu.add_command(label="Sair", command=on_closing)
    menubar.add_cascade(label="Arquivo", menu=file_menu)

    # Menu Exibir
    view_menu = tk.Menu(menubar, tearoff=0)
    view_menu.add_checkbutton(
        label="Sempre no topo",
        variable=always_on_top_var,
        command=toggle_always_on_top,
    )
    menubar.add_cascade(label="Exibir", menu=view_menu)

    # Menu Configurações
    menubar.add_command(label="Configurações", command=show_settings)

    # Menu Ajuda
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="Sobre", command=show_about)
    menubar.add_cascade(label="Ajuda", menu=help_menu)

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

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
