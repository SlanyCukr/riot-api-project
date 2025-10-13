"""Backend package adapter exposing the real ``app`` package under ``backend.app``."""

from importlib import import_module
from pathlib import Path
import sys

__path__ = [str(Path(__file__).resolve().parent)]
if __spec__ is not None:
    __spec__.submodule_search_locations = __path__

_app_module = import_module("app")
sys.modules.setdefault("backend.app", _app_module)

# Provide attribute access so ``backend.app`` resolves correctly
app = _app_module

__all__ = ["app"]
