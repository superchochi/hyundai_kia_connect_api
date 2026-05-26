"""Imported for its side effect: puts the repo root on sys.path.

Pages still need to add ui-streamlit/ to sys.path themselves before importing
this module, because Python must find `utils` first.
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
