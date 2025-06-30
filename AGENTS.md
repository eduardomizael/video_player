# Repository instructions for video_player

This project is written in Python 3.12 and uses [`python-vlc`](https://pypi.org/project/python-vlc/) for video playback.

## Contribution guidelines

- **Formatting**: Run `black --line-length 120 .` on all Python files.
- **Linting**: Ensure `ruff` passes with default settings (`ruff check .`).
- **Syntax check**: Run `python -m py_compile $(git ls-files '*.py')`.
- **Style**: Follow PEP 8 with 4‑space indentation and include type hints and docstrings in Brazilian Portuguese for all functions, methods and classes.
- **Documentation**: Update `README.md` on add ou alter functionalities. All documentation must remain in portuguese.
- **Commits**: Write commit messages in Brazilian Portuguese summarizing the changes.

These checks must be run after every modification.