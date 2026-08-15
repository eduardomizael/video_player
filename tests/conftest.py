"""Fixtures compartilhadas para testes que dependem do interpretador Tcl/Tk."""

import tkinter as tk
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session")
def tk_root() -> Iterator[tk.Tk]:
    """Mantém uma única raiz Tk durante a sessão para evitar falhas intermitentes no Windows."""

    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
