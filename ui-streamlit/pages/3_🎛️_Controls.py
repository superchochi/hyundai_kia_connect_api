"""Controls – lock, climate, windows, valet, alerts."""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_UI = os.path.abspath(os.path.join(_HERE, ".."))
for p in (_ROOT, _UI):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from utils.session import render_sidebar, get_vm
from hyundai_kia_connect_api import ClimateRequestOptions, WindowRequestOptions
from hyundai_kia_connect_api.const import WINDOW_STATE, ORDER_STATUS
from hyundai_kia_connect_api.exceptions import DuplicateRequestError

st.set_page_config(page_title="Controls", page_icon="🎛️", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

vm = get_vm()
st.title("🎛️ Controls")
st.caption(f"{vehicle.name} · {vehicle.model}")


def _send(label: str, fn, *args, **kwargs):
    """Execute a command and show a status message."""
    with st.spinner(f"Sending {label}…"):
        try:
            action_id = fn(*args, **kwargs)
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


def _poll_status(action_id: str):
    if action_id is None:
        return
    with st.spinner("Waiting for vehicle confirmation…"):
        try:
            result = vm.check_action_status(vehicle.id, action_id, synchronous=True, timeout=60)
            if result == ORDER_STATUS.SUCCESS:
                st.success("✅ Vehicle confirmed the action.")
            elif result == ORDER_STATUS.FAILED:
                st.error("❌ Vehicle rejected the action.")
            elif result == ORDER_STATUS.TIMEOUT:
                st.warning("⏱️ Action timed out (vehicle may still execute it).")
            else:
                st.info(f"Status: {result}")
        except Exception as e:
            st.warning(f"Could not check action status: {e}")


tabs = st.tabs(["🔒 Lock / Unlock", "🌡️ Climate", "🪟 Windows", "🚨 Alerts", "🅿️ Valet"])

# ── Lock / Unlock ──────────────────────────────────────────────────────────────
with tabs[0]:
    from utils.helpers import lock_status
    st.subheader("Door Lock")
    st.markdown(f"**Current status:** {lock_status(vehicle.is_locked)}")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔒 Lock Vehicle")
        st.caption("Sends a lock command to all doors.")
        wait_lock = st.checkbox("Wait for confirmation", value=True, key="wait_lock")
        if st.button("🔒 Lock", width="stretch", type="primary", key="btn_lock"):
            aid = _send("Lock", vm.lock, vehicle.id)
            if wait_lock and aid:
                _poll_status(aid)
    with col2:
        st.markdown("#### 🔓 Unlock Vehicle")
        st.caption("Sends an unlock command to all doors.")
        wait_unlock = st.checkbox("Wait for confirmation", value=True, key="wait_unlock")
        if st.button("🔓 Unlock", width="stretch", key="btn_unlock"):
            aid = _send("Unlock", vm.unlock, vehicle.id)
            if wait_unlock and aid:
                _poll_status(aid)

# ── Climate ────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Climate Control")
    from utils.helpers import status_dot
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
            wait_climate = st.checkbox("Wait for vehicle confirmation", value=True)

            start_submitted = st.form_submit_button("▶️ Start Climate", type="primary", width="stretch")

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
            aid = _send("Start Climate", vm.start_climate, vehicle.id, opts)
            if wait_climate and aid:
                _poll_status(aid)

    with col_right:
        st.markdown("#### Stop Climate")
        st.caption("Turns off the remote climate control.")
        if st.button("⏹️ Stop Climate", width="stretch", key="btn_stop_climate"):
            _send("Stop Climate", vm.stop_climate, vehicle.id)

# ── Windows ────────────────────────────────────────────────────────────────────
with tabs[2]:
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

            win_submitted = st.form_submit_button("🪟 Apply Window States", type="primary", width="stretch")
            wait_windows = st.checkbox("Wait for confirmation", value=True, key="wait_windows")

        if win_submitted:
            def _ws(v):
                return WINDOW_STATE(v)
            opts = WindowRequestOptions(
                front_left=_ws(window_selections["fl"]),
                front_right=_ws(window_selections["fr"]),
                back_left=_ws(window_selections["rl"]),
                back_right=_ws(window_selections["rr"]),
            )
            aid = _send("Window Control", vm.set_windows_state, vehicle.id, opts)
            if wait_windows and aid:
                _poll_status(aid)

# ── Alerts ─────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Lights & Horn Alerts")
    st.caption("Both commands activate for 30 seconds.")
    st.divider()
    a_cols = st.columns(2)
    with a_cols[0]:
        st.markdown("#### 🚨 Hazard Lights")
        st.caption("Flash hazard lights to locate your vehicle.")
        if st.button("🚨 Activate Hazard Lights", width="stretch", key="btn_hazard"):
            _send("Hazard Lights", vm.start_hazard_lights, vehicle.id)
    with a_cols[1]:
        st.markdown("#### 📯 Hazard Lights + Horn")
        st.caption("Flash lights and honk horn simultaneously.")
        if st.button("📯 Lights + Horn", width="stretch", key="btn_horn"):
            _send("Horn + Lights", vm.start_hazard_lights_and_horn, vehicle.id)

# ── Valet ──────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Valet Mode")
    st.caption("Valet mode restricts vehicle operation. Region-dependent feature.")
    st.divider()
    v_cols = st.columns(2)
    with v_cols[0]:
        st.markdown("#### Enable Valet Mode")
        if st.button("🅿️ Start Valet Mode", width="stretch", key="btn_valet_on"):
            _send("Start Valet Mode", vm.start_valet_mode, vehicle.id)
    with v_cols[1]:
        st.markdown("#### Disable Valet Mode")
        if st.button("🔑 Stop Valet Mode", width="stretch", key="btn_valet_off"):
            _send("Stop Valet Mode", vm.stop_valet_mode, vehicle.id)
