"""Session state management and shared sidebar component."""
from __future__ import annotations

import inspect
import os
import sys

import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.helpers import lock_status, fmt_time_ago, fmt_val
from utils.commands import get_pending, poll_pending_once, clear_pending, is_command_pending
from hyundai_kia_connect_api.const import ORDER_STATUS


def get_vm():
    return st.session_state.get("vm")


def get_vehicles() -> list:
    return st.session_state.get("vehicles", [])


def get_selected_vehicle():
    vehicles = get_vehicles()
    if not vehicles:
        return None
    vid = st.session_state.get("selected_vehicle_id")
    if vid:
        for v in vehicles:
            if v.id == vid:
                return v
    return vehicles[0]


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def require_auth(current_page: str | None = None):
    """Redirect to login page if not authenticated, saving the intended destination."""
    if not is_logged_in():
        if current_page:
            st.session_state._redirect_after_login = current_page
        st.switch_page("app.py")


def render_pending_banner():
    """Render a full-width pending-action banner at the top of any page.

    When a pending action exists the banner auto-refreshes every 3 seconds:
    it polls check_action_status (non-blocking) and also calls
    update_vehicle_with_cached_state so the vehicle data stays fresh.
    On a terminal status the pending state is cleared and the page reruns.
    """
    if not is_command_pending():
        return

    @st.fragment(run_every=3)
    def _banner():
        pending = get_pending()
        if pending is None:
            # Expired or already cleared — stop the fragment loop.
            st.rerun()
            return

        vm = get_vm()
        import datetime
        elapsed = int((datetime.datetime.now(datetime.timezone.utc) - pending["sent_at"]).total_seconds())

        # Auto-poll on every fragment run (every 3 s).
        terminal = False
        status_msg = None
        if vm:
            try:
                vm.update_vehicle_with_cached_state(pending["vehicle_id"])
                st.session_state["vehicles"] = list(vm.vehicles.values())
            except Exception:
                pass
            status = poll_pending_once(vm)
            if status == ORDER_STATUS.SUCCESS:
                terminal = True
                status_msg = ("success", "✅ Vehicle confirmed the action.")
            elif status == ORDER_STATUS.FAILED:
                terminal = True
                status_msg = ("error", "❌ Vehicle rejected the action.")
            elif status == ORDER_STATUS.TIMEOUT:
                terminal = True
                status_msg = ("warning", "⏱️ No response from vehicle (it may still execute the command).")

        if terminal:
            if status_msg:
                getattr(st, status_msg[0])(status_msg[1])
            st.rerun()
            return

        col_text, col_dismiss = st.columns([8, 1])
        with col_text:
            st.warning(
                f"⏳ **{pending['label']}** sent {elapsed}s ago — waiting for vehicle confirmation. "
                "Checking every 3 s. New commands are blocked."
            )
        with col_dismiss:
            if st.button("✕", key="_banner_dismiss", help="Dismiss and stop tracking"):
                clear_pending()
                st.rerun()

    _banner()


def render_sidebar():
    """Render the vehicle selector and status in the sidebar. Returns selected vehicle."""
    caller_file = inspect.stack()[1].filename
    _ui_root = os.path.abspath(os.path.join(_HERE, ".."))
    try:
        current_page = os.path.relpath(caller_file, _ui_root)
    except ValueError:
        current_page = None
    require_auth(current_page)
    vehicles = get_vehicles()
    if not vehicles:
        st.sidebar.warning("No vehicles found.")
        return None

    names = [f"{v.name} ({v.model})" for v in vehicles]
    current = get_selected_vehicle()
    current_idx = next((i for i, v in enumerate(vehicles) if v.id == (current.id if current else None)), 0)

    st.sidebar.markdown("### 🚗 Vehicle")
    choice = st.sidebar.selectbox("Select vehicle", names, index=current_idx, label_visibility="collapsed")
    selected = vehicles[names.index(choice)]
    st.session_state["selected_vehicle_id"] = selected.id

    st.sidebar.divider()

    # Mini status summary
    st.sidebar.markdown(f"**Status:** {lock_status(selected.is_locked)}")
    if selected.ev_battery_percentage is not None:
        pct = selected.ev_battery_percentage
        bar = "🟩" * (pct // 10) + "⬛" * (10 - pct // 10)
        st.sidebar.markdown(f"**Battery:** {pct}%  \n{bar}")
    elif selected.fuel_level is not None:
        st.sidebar.markdown(f"**Fuel:** {fmt_val(selected.fuel_level, '%')}")
    st.sidebar.markdown(f"**Updated:** {fmt_time_ago(selected.last_updated_at)}")

    # Pending action indicator in sidebar
    pending = get_pending()
    if pending:
        import datetime
        elapsed = int((datetime.datetime.now(datetime.timezone.utc) - pending["sent_at"]).total_seconds())
        st.sidebar.warning(f"⏳ {pending['label']} ({elapsed}s)")

    st.sidebar.divider()

    vm = get_vm()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Refresh", width="stretch", key="sidebar_refresh"):
            # Poll pending action status on every refresh
            if pending and vm:
                status = poll_pending_once(vm)
                if status in (ORDER_STATUS.SUCCESS, ORDER_STATUS.FAILED,
                               ORDER_STATUS.TIMEOUT, ORDER_STATUS.UNKNOWN):
                    clear_pending()
            with st.spinner("Refreshing…"):
                try:
                    vm.update_vehicle_with_cached_state(selected.id)
                    st.session_state["vehicles"] = list(vm.vehicles.values())
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(str(e))
    with col2:
        if st.button("⚡ Force", width="stretch", key="sidebar_force"):
            with st.spinner("Waking vehicle…"):
                try:
                    vm.force_refresh_vehicle_state(selected.id)
                    st.session_state["vehicles"] = list(vm.vehicles.values())
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(str(e))

    return selected
