"""Controls – lock, climate, windows, valet, alerts."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ui-streamlit/
from utils import _bootstrap  # noqa: F401  (adds repo root for hyundai_kia_connect_api)

import streamlit as st

from utils.session import render_sidebar, get_vm, render_pending_banner
from utils.commands import send_command, is_command_pending
from utils.helpers import lock_status, status_dot
from hyundai_kia_connect_api import ClimateRequestOptions, WindowRequestOptions
from hyundai_kia_connect_api.const import WINDOW_STATE

st.set_page_config(page_title="Controls", page_icon="🎛️", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

vm = get_vm()
render_pending_banner()

st.title("🎛️ Controls")
st.caption(f"{vehicle.name} · {vehicle.model}")

_pending = is_command_pending()

_TABS = ["🔒 Lock / Unlock", "🌡️ Climate", "🪟 Windows", "🚨 Alerts", "🅿️ Valet"]
tab = st.segmented_control("Section", _TABS, default=_TABS[0], key="controls_tab", label_visibility="collapsed")
if tab is None:
    tab = _TABS[0]
st.divider()

# ── Lock / Unlock ──────────────────────────────────────────────────────────────
if tab == _TABS[0]:
    st.subheader("Door Lock")
    st.markdown(f"**Current status:** {lock_status(vehicle.is_locked)}")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔒 Lock Vehicle")
        st.caption("Sends a lock command to all doors.")
        if st.button("🔒 Lock", width="stretch", type="primary", key="btn_lock",
                     disabled=_pending):
            send_command("Lock", vm.lock, vehicle.id)
    with col2:
        st.markdown("#### 🔓 Unlock Vehicle")
        st.caption("Sends an unlock command to all doors.")
        with st.popover("🔓 Unlock", use_container_width=True):
            st.warning("Unlock all doors?")
            if st.button("Yes, unlock", type="primary", key="btn_unlock_confirm",
                         disabled=_pending):
                send_command("Unlock", vm.unlock, vehicle.id)

# ── Climate ────────────────────────────────────────────────────────────────────
elif tab == _TABS[1]:
    st.subheader("Climate Control")
    st.markdown(f"**A/C currently:** {status_dot(vehicle.air_control_is_on, 'On', 'Off')}")
    st.divider()

    col_left, col_right = st.columns([3, 2])
    with col_left:
        with st.form("climate_form"):
            st.markdown("#### Start Climate")
            temp = st.slider("Temperature (°C)", min_value=16.0, max_value=30.0, value=22.0, step=0.5)
            duration = st.slider("Duration (minutes)", min_value=5, max_value=30, value=10, step=5)

            c1, c2 = st.columns(2)
            with c1:
                climate_on = st.checkbox("A/C On", value=True)
                defrost = st.checkbox("Defrost", value=False)
            with c2:
                heating = st.selectbox("Heating Level", [0, 1, 2, 3, 4], index=0,
                                       help="0=off, 1-4=levels")

            st.markdown("**Seat Heaters/Coolers** (0=off, 1-8)")
            s_cols = st.columns(4)
            with s_cols[0]:
                fl_seat = st.number_input("Front L", 0, 8, 0, key="s_fl")
            with s_cols[1]:
                fr_seat = st.number_input("Front R", 0, 8, 0, key="s_fr")
            with s_cols[2]:
                rl_seat = st.number_input("Rear L", 0, 8, 0, key="s_rl")
            with s_cols[3]:
                rr_seat = st.number_input("Rear R", 0, 8, 0, key="s_rr")

            steer = st.number_input("Steering Wheel Heater (0=off)", 0, 3, 0, key="steer")
            start_submitted = st.form_submit_button(
                "▶️ Start Climate", type="primary", width="stretch", disabled=_pending
            )

        if start_submitted:
            opts = ClimateRequestOptions(
                set_temp=temp,
                duration=duration,
                defrost=defrost,
                climate=climate_on,
                heating=heating,
                front_left_seat=fl_seat,
                front_right_seat=fr_seat,
                rear_left_seat=rl_seat,
                rear_right_seat=rr_seat,
                steering_wheel=steer,
            )
            send_command("Start Climate", vm.start_climate, vehicle.id, opts)

    with col_right:
        st.markdown("#### Stop Climate")
        st.caption("Turns off the remote climate control.")
        if st.button("⏹️ Stop Climate", width="stretch", key="btn_stop_climate",
                     disabled=_pending):
            send_command("Stop Climate", vm.stop_climate, vehicle.id)

# ── Windows ────────────────────────────────────────────────────────────────────
elif tab == _TABS[2]:
    st.subheader("Window Control")
    if not vehicle.supports_window_control:
        st.warning("⚠️ Window control is not supported for this vehicle/region.")
    else:
        st.caption("Set each window state independently.")
        _state_options = {s.value: s.name.title() for s in WINDOW_STATE}
        _state_labels = list(_state_options.values())
        _state_values = list(_state_options.keys())

        with st.form("window_form"):
            w_cols = st.columns(4)
            window_selections = {}
            for col, (key, label) in zip(w_cols, [
                ("fl", "Front Left"), ("fr", "Front Right"),
                ("rl", "Rear Left"), ("rr", "Rear Right"),
            ]):
                with col:
                    idx = st.selectbox(label, options=range(len(_state_labels)),
                                       format_func=lambda i: _state_labels[i], key=f"win_{key}")
                    window_selections[key] = _state_values[idx]

            win_submitted = st.form_submit_button(
                "🪟 Apply Window States", type="primary", width="stretch", disabled=_pending
            )

        if win_submitted:
            opts = WindowRequestOptions(
                front_left=WINDOW_STATE(window_selections["fl"]),
                front_right=WINDOW_STATE(window_selections["fr"]),
                back_left=WINDOW_STATE(window_selections["rl"]),
                back_right=WINDOW_STATE(window_selections["rr"]),
            )
            send_command("Window Control", vm.set_windows_state, vehicle.id, opts)

# ── Alerts ─────────────────────────────────────────────────────────────────────
elif tab == _TABS[3]:
    st.subheader("Lights & Horn Alerts")
    st.caption("Both commands activate for 30 seconds.")
    st.divider()
    a_cols = st.columns(2)
    with a_cols[0]:
        st.markdown("#### 🚨 Hazard Lights")
        st.caption("Flash hazard lights to locate your vehicle.")
        if st.button("🚨 Activate Hazard Lights", width="stretch", key="btn_hazard",
                     disabled=_pending):
            send_command("Hazard Lights", vm.start_hazard_lights, vehicle.id)
    with a_cols[1]:
        st.markdown("#### 📯 Hazard Lights + Horn")
        st.caption("Flash lights and honk horn simultaneously.")
        if st.button("📯 Lights + Horn", width="stretch", key="btn_horn",
                     disabled=_pending):
            send_command("Horn + Lights", vm.start_hazard_lights_and_horn, vehicle.id)

# ── Valet ──────────────────────────────────────────────────────────────────────
elif tab == _TABS[4]:
    st.subheader("Valet Mode")
    if vehicle.supports_valet_mode is False:
        st.info("Valet mode is not supported by this vehicle.")
        st.stop()
    st.caption("Valet mode restricts vehicle operation. Region-dependent feature.")
    if vehicle.valet_mode_active is not None:
        st.markdown(f"**Current state:** {'🅿️ Active' if vehicle.valet_mode_active else '⬜ Inactive'}")
    st.divider()
    v_cols = st.columns(2)
    with v_cols[0]:
        st.markdown("#### Enable Valet Mode")
        with st.popover("🅿️ Start Valet Mode", use_container_width=True):
            st.warning("Enable valet mode? This restricts vehicle operation.")
            if st.button("Yes, enable valet", type="primary", key="btn_valet_on_confirm",
                         disabled=_pending):
                send_command("Start Valet Mode", vm.start_valet_mode, vehicle.id)
    with v_cols[1]:
        st.markdown("#### Disable Valet Mode")
        with st.popover("🔑 Stop Valet Mode", use_container_width=True):
            st.warning("Disable valet mode?")
            if st.button("Yes, disable valet", type="primary", key="btn_valet_off_confirm",
                         disabled=_pending):
                send_command("Stop Valet Mode", vm.stop_valet_mode, vehicle.id)
