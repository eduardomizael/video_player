# Repository instructions for video_player

This project is written in Python 3.12 and uses [`python-vlc`](https://pypi.org/project/python-vlc/) for video playback.

## Contribution guidelines

- **Formatting**: Run `black --line-length 120 .` on all Python files.
- **Linting**: Ensure `ruff` passes with default settings (`ruff .`).
- **Syntax check**: Run `python -m py_compile $(git ls-files '*.py')`.
- **Style**: Follow PEP 8 with 4‑space indentation and inclua type hints e docstrings em português para todas as funções, métodos e classes.
- **Documentation**: Atualize `README.md` ao adicionar ou alterar funcionalidades. Toda documentação deve permanecer em português.
- **Commits**: Write commit messages in Brazilian Portuguese summarizing the changes.

These checks must be run after every modification.