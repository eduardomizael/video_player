"""Formulário modal para revisar itens antes de inseri-los nas árvores."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import messagebox


@dataclass(frozen=True)
class FormField:
    """Define um campo exibido pelo formulário de inclusão."""

    name: str
    label: str
    value: str
    multiline: bool = False


class AddItemDialog(tk.Toplevel):
    """Coleta valores editáveis e só confirma a inclusão após validação."""

    def __init__(
        self,
        master: tk.Widget,
        title: str,
        fields: list[FormField],
        on_submit: Callable[[dict[str, str]], str | None],
    ) -> None:
        """Monta o formulário modal com os valores iniciais informados."""

        super().__init__(master.winfo_toplevel())
        self.title(title)
        self.transient(master.winfo_toplevel())
        self.resizable(False, False)
        self.on_submit = on_submit
        self.widgets: dict[str, tk.Entry | tk.Text] = {}

        content = tk.Frame(self, padx=16, pady=14)
        content.pack(fill="both", expand=True)
        for row, field in enumerate(fields):
            tk.Label(content, text=field.label).grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=4)
            if field.multiline:
                widget = tk.Text(content, width=42, height=5)
                widget.insert("1.0", field.value)
            else:
                widget = tk.Entry(content, width=42)
                widget.insert(0, field.value)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.widgets[field.name] = widget
        content.columnconfigure(1, weight=1)

        footer = tk.Frame(content, pady=10)
        footer.grid(row=len(fields), column=0, columnspan=2, sticky="ew")
        tk.Button(footer, text="Cancelar", command=self.destroy, width=10).pack(side="right")
        tk.Button(footer, text="Salvar", command=self.save, width=10).pack(side="right", padx=(0, 6))
        self.bind("<Escape>", self._cancel)
        self.bind("<Return>", self._save_from_key)
        self.grab_set()
        self.update_idletasks()
        parent = master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{max(0, x)}+{max(0, y)}")
        self.after_idle(lambda: self._focus_first_field(fields[0].name))

    def _focus_first_field(self, name: str) -> None:
        """Posiciona o foco no primeiro campo e seleciona seu conteúdo inicial."""

        widget = self.widgets[name]
        widget.focus_set()
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end-1c")
        else:
            widget.selection_range(0, tk.END)

    def _cancel(self, _: tk.Event) -> str:
        """Fecha o formulário quando o usuário pressiona Escape."""

        self.destroy()
        return "break"

    def _save_from_key(self, event: tk.Event) -> str | None:
        """Confirma o formulário quando o usuário pressiona Enter."""

        if event.state & 0x1 and isinstance(event.widget, tk.Text):
            return None

        self.save()
        return "break"

    def save(self) -> None:
        """Valida os valores por meio do chamador e fecha apenas em caso de sucesso."""

        values = {
            name: widget.get("1.0", "end-1c") if isinstance(widget, tk.Text) else widget.get()
            for name, widget in self.widgets.items()
        }
        error = self.on_submit(values)
        if error:
            messagebox.showerror("Dados inválidos", error, parent=self)
            return
        self.destroy()
