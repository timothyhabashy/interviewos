"""Entrypoint: launch JupyterLab rooted at the project's `notebooks/` folder.

Run with either of:

    uv run python -m spring_spring_hackathon
    uv run spring-spring-hackathon
"""

from __future__ import annotations

import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _notebooks_dir() -> Path:
    notebooks = _project_root() / "notebooks"
    notebooks.mkdir(exist_ok=True)
    return notebooks


def main() -> None:
    try:
        from jupyterlab.labapp import LabApp
    except ImportError as exc:
        raise SystemExit(
            "JupyterLab is not installed. Run `uv sync` to install project "
            "dependencies, then try again."
        ) from exc

    sys.argv = [
        "jupyter-lab",
        f"--notebook-dir={_notebooks_dir()}",
    ]
    LabApp.launch_instance()


if __name__ == "__main__":
    main()
