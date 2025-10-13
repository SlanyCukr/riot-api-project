"""Compatibility shim exposing the real ``app`` package as ``backend.app``."""

from importlib import import_module
from pathlib import Path
import sys

__path__ = [str(Path(__file__).resolve().parent)]

_app_module = import_module("app")
sys.modules.setdefault("backend.app", _app_module)

app = _app_module

__all__ = ["app"]
