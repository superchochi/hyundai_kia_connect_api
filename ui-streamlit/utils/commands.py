"""Shared vehicle-command runner and pending-action tracker."""
from __future__ import annotations

import datetime
from typing import Any, Callable

import streamlit as st

from hyundai_kia_connect_api.const import ORDER_STATUS
from hyundai_kia_connect_api.exceptions import (
    AuthenticationError,
    DuplicateRequestError,
    NoDataFound,
    PINMissingError,
    RateLimitingError,
    RequestTimeoutError,
    ServiceTemporaryUnavailable,
    UnsupportedControlError,
)

# Hard ceiling: clear pending state after this many seconds even if no response.
_PENDING_TIMEOUT_SECONDS = 90


# ── Pending action helpers ─────────────────────────────────────────────────────

def get_pending() -> dict | None:
    """Return the current pending action dict, or None if none / expired."""
    pending = st.session_state.get("_pending_action")
    if pending is None:
        return None
    elapsed = (datetime.datetime.now(datetime.timezone.utc) - pending["sent_at"]).total_seconds()
    if elapsed > _PENDING_TIMEOUT_SECONDS:
        st.session_state["_pending_action"] = None
        return None
    return pending


def is_command_pending() -> bool:
    return get_pending() is not None


def _set_pending(action_id: str, vehicle_id: str, label: str) -> None:
    st.session_state["_pending_action"] = {
        "action_id": action_id,
        "vehicle_id": vehicle_id,
        "label": label,
        "sent_at": datetime.datetime.now(datetime.timezone.utc),
    }


def clear_pending() -> None:
    st.session_state["_pending_action"] = None


def poll_pending_once(vm) -> ORDER_STATUS | None:
    """Do one non-blocking status poll. Clears pending on terminal status.

    Returns the ORDER_STATUS if polled, None if nothing pending.
    """
    pending = get_pending()
    if pending is None:
        return None
    try:
        status = vm.check_action_status(
            pending["vehicle_id"], pending["action_id"],
            synchronous=False,
        )
        if status in (ORDER_STATUS.SUCCESS, ORDER_STATUS.FAILED,
                      ORDER_STATUS.TIMEOUT, ORDER_STATUS.UNKNOWN):
            clear_pending()
        return status
    except Exception:
        return None


# ── Command sender ─────────────────────────────────────────────────────────────

def send_command(
    label: str,
    fn: Callable,
    *args: Any,
    toast: bool = False,
    **kwargs: Any,
) -> str | None:
    """Send a vehicle command, show feedback, register it as the pending action.

    Returns the action_id on success, None on failure.
    Blocks new commands while a previous action is still pending.
    """
    # Guard: don't allow a second command while one is in flight.
    if is_command_pending():
        pending = get_pending()
        st.warning(
            f"⏳ **{pending['label']}** is still pending. "
            "Wait for the vehicle to confirm before sending another command."
        )
        return None

    with st.spinner(f"Sending {label}…"):
        try:
            action_id = fn(*args, **kwargs)
            # Extract vehicle_id: first positional arg is always vehicle_id for all commands.
            vehicle_id = args[0] if args else None
            if vehicle_id and action_id:
                _set_pending(action_id, vehicle_id, label)
            if toast:
                st.toast(f"✅ {label} sent", icon="✅")
            else:
                st.success(f"✅ **{label}** sent · waiting for vehicle confirmation…")
            return action_id
        except DuplicateRequestError:
            st.warning(
                "⏳ A previous command is still pending on the server. "
                "Wait 30–60 seconds for the car to respond, then try again."
            )
            return None
        except UnsupportedControlError:
            st.error(f"⚠️ **{label}** is not supported by this vehicle or region.")
            return None
        except RequestTimeoutError:
            st.warning(
                f"⏱️ **{label}** timed out — the server could not reach the car. "
                "The car may be in a low-signal area. Try again in a few minutes."
            )
            return None
        except RateLimitingError:
            st.warning(
                f"🚦 **{label}** was rate-limited by the server. "
                "Wait a few minutes before sending another command."
            )
            return None
        except ServiceTemporaryUnavailable:
            st.warning(
                f"🔧 **{label}** failed — the OEM service is temporarily unavailable. "
                "Try again shortly."
            )
            return None
        except NoDataFound:
            st.warning(
                f"📭 **{label}** failed — the server has no data for this vehicle. "
                "If this persists, try disabling and re-enabling the vehicle."
            )
            return None
        except PINMissingError:
            st.error(
                f"🔢 **{label}** requires a PIN. "
                "Log out and log in again with your vehicle PIN."
            )
            return None
        except AuthenticationError as e:
            st.error(
                f"🔐 **{label}** failed — session expired or authentication error: {e}. "
                "Please log out and log in again."
            )
            return None
        except Exception as e:
            st.error(f"❌ **{label}** failed: {e}")
            return None
