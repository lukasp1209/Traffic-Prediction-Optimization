from __future__ import annotations

__all__ = ["run_app"]


def run_app():
    from .main import run_app as _run_app

    return _run_app()
