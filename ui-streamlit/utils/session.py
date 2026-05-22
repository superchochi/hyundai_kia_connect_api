"""Session state management and shared sidebar component."""
from __future__ import annotations

import inspect
import os
import sys

import streamlit as st

# Ensure the repo root is on the path so hyundai_kia_connect_api is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


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


def render_sidebar():
    """Render the vehicle selector and status in the sidebar. Returns selected vehicle."""
    # Auto-detect calling page path so login can redirect back here.
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
    from utils.helpers import lock_status, fmt_time_ago, fmt_val
    st.sidebar.markdown(f"**Status:** {lock_status(selected.is_locked)}")
    if selected.ev_battery_percentage is not None:
        pct = selected.ev_battery_percentage
        bar = "🟩" * (pct // 10) + "⬛" * (10 - pct // 10)
        st.sidebar.markdown(f"**Battery:** {pct}%  \n{bar}")
    elif selected.fuel_level is not None:
        st.sidebar.markdown(f"**Fuel:** {fmt_val(selected.fuel_level, '%')}")
    st.sidebar.markdown(f"**Updated:** {fmt_time_ago(selected.last_updated_at)}")

    st.sidebar.divider()

    vm = get_vm()
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Refresh", width="stretch", key="sidebar_refresh"):
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
