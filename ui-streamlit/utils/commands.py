"""Shared vehicle-command runner. Stateless — just spinner + result feedback."""
from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from hyundai_kia_connect_api.exceptions import DuplicateRequestError


def send_command(
    label: str,
    fn: Callable,
    *args: Any,
    toast: bool = False,
    **kwargs: Any,
) -> str | None:
    """Run a vehicle command, render feedback, return the action_id (or None on failure).

    toast=True uses st.toast (preferred for compact pages with many buttons);
    toast=False uses st.success with the action_id visible.
    """
    with st.spinner(f"Sending {label}…"):
        try:
            action_id = fn(*args, **kwargs)
            if toast:
                st.toast(f"✅ {label} command sent", icon="✅")
            else:
                st.success(f"✅ **{label}** sent. Action ID: `{action_id}`")
            return action_id
        except DuplicateRequestError:
            st.warning(
                "⏳ A previous command is still pending. "
                "Wait 30–60 seconds for the car to respond, then try again."
            )
            return None
        except Exception as e:
            st.error(f"❌ **{label}** failed: {e}")
            return None
