"""Charging – EV charging controls, limits, scheduling, off-peak."""
from __future__ import annotations

import os
import sys
from datetime import time as dt_time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ui-streamlit/
from utils import _bootstrap  # noqa: F401  (adds repo root for hyundai_kia_connect_api)

import streamlit as st

from utils.session import render_sidebar, get_vm, render_pending_banner
from utils.commands import send_command, is_command_pending
from utils.helpers import status_dot, fmt_val, fmt_distance, door_status
from hyundai_kia_connect_api import ScheduleChargingClimateRequestOptions
from hyundai_kia_connect_api.const import ENGINE_TYPES

DepartureOptions = ScheduleChargingClimateRequestOptions.DepartureOptions

_DAYS_MAP = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}


def _dep_form(
    prefix: str,
    enabled_default: bool,
    time_default: dt_time,
    days_default: list,
    climate_default: bool,
    temp_default: float,
    defrost_default: bool,
):
    enabled = st.checkbox("Enable", value=enabled_default, key=f"{prefix}_enabled")
    dep_cols = st.columns(2)
    with dep_cols[0]:
        dep_time = st.time_input("Departure Time", value=time_default, key=f"{prefix}_time")
    with dep_cols[1]:
        days = st.multiselect(
            "Days",
            options=list(_DAYS_MAP.keys()),
            default=days_default,
            format_func=lambda d: _DAYS_MAP[d],
            key=f"{prefix}_days",
        )
    clim_enabled = st.checkbox("Enable Climate Pre-conditioning", value=climate_default, key=f"{prefix}_clim")
    if clim_enabled:
        c1, c2 = st.columns(2)
        with c1:
            temp = st.number_input("Temperature", 16.0, 30.0, temp_default, 0.5, key=f"{prefix}_temp")
        with c2:
            defrost = st.checkbox("Defrost", value=defrost_default, key=f"{prefix}_defrost")
    else:
        temp = temp_default
        defrost = defrost_default
    return enabled, dep_time, days, clim_enabled, temp, defrost


st.set_page_config(page_title="Charging", page_icon="🔋", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

vm = get_vm()
render_pending_banner()
_pending = is_command_pending()

if vehicle.engine_type not in (ENGINE_TYPES.EV, ENGINE_TYPES.PHEV):
    st.title("🔋 Charging")
    st.info("This page is for EV and PHEV vehicles. The selected vehicle is not EV/PHEV.")
    st.stop()

st.title("🔋 Charging")
st.caption(f"{vehicle.name} · {vehicle.model}")

# ── Current Status ─────────────────────────────────────────────────────────────
st.subheader("⚡ Current Charging Status")

s_cols = st.columns(4)
with s_cols[0]:
    pct = vehicle.ev_battery_percentage or 0
    st.metric("Battery", f"{pct}%")
    st.progress(pct / 100)
with s_cols[1]:
    charging = vehicle.ev_battery_is_charging
    plugged = vehicle.ev_battery_is_plugged_in
    st.metric("State", "⚡ Charging" if charging else ("🔌 Plugged" if plugged else "🔋 Unplugged"))
    if vehicle.ev_charging_power is not None:
        st.caption(f"{vehicle.ev_charging_power:.1f} kW")
with s_cols[2]:
    st.metric("AC Charge Limit", fmt_val(vehicle.ev_charge_limits_ac, "%"))
    st.metric("DC Charge Limit", fmt_val(vehicle.ev_charge_limits_dc, "%"))
with s_cols[3]:
    st.metric("Time to 100%", fmt_val(vehicle.ev_estimated_current_charge_duration, "min"))
    st.metric("DC Fast to 80%", fmt_val(vehicle.ev_estimated_fast_charge_duration, "min"))

st.divider()

_TABS = ["▶️ Start / Stop", "🎚️ Charge Limits", "📅 Scheduled Departure", "🌙 Off-Peak Charging", "🔌 Charge Port", "⚡ V2L / V2X"]
tab = st.segmented_control("Section", _TABS, default=_TABS[0], key="charging_tab", label_visibility="collapsed")
if tab is None:
    tab = _TABS[0]
st.divider()

# ── Start / Stop ───────────────────────────────────────────────────────────────
if tab == _TABS[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ▶️ Start Charging")
        st.caption("Initiates charging if charger is connected.")
        if st.button("▶️ Start Charge", width="stretch", type="primary", key="btn_start_charge", disabled=_pending):
            send_command("Start Charge", vm.start_charge, vehicle.id)
    with col2:
        st.markdown("#### ⏹️ Stop Charging")
        st.caption("Stops an active charging session.")
        if st.button("⏹️ Stop Charge", width="stretch", key="btn_stop_charge", disabled=_pending):
            send_command("Stop Charge", vm.stop_charge, vehicle.id)

# ── Charge Limits ──────────────────────────────────────────────────────────────
elif tab == _TABS[1]:
    st.markdown("#### Set Charge Limits")
    st.caption("Define maximum battery level for AC and DC charging.")

    with st.form("charge_limits_form"):
        lim_cols = st.columns(2)
        with lim_cols[0]:
            ac_limit = st.slider(
                "AC Charge Limit (%)",
                min_value=50, max_value=100, step=10,
                value=vehicle.ev_charge_limits_ac or 90,
            )
        with lim_cols[1]:
            dc_limit = st.slider(
                "DC Charge Limit (%)",
                min_value=50, max_value=100, step=10,
                value=vehicle.ev_charge_limits_dc or 80,
            )
        limits_submitted = st.form_submit_button("💾 Apply Charge Limits", type="primary", width="stretch", disabled=_pending)

    if limits_submitted:
        send_command("Set Charge Limits", vm.set_charge_limits, vehicle.id, ac_limit, dc_limit)

    st.divider()
    st.markdown("#### Set Charging Current (EU only)")
    st.caption("1 = 100%, 2 = 90%, 3 = 60%")
    if vehicle.ev_charging_current is not None:
        current_label = {1: "100%", 2: "90%", 3: "60%"}.get(vehicle.ev_charging_current, str(vehicle.ev_charging_current))
        st.info(f"Current charging current: **{current_label}**")
    with st.form("charging_current_form"):
        current_level = st.selectbox(
            "Current Level",
            [1, 2, 3],
            format_func=lambda x: {1: "100%", 2: "90%", 3: "60%"}[x],
            index=0,
        )
        cur_submitted = st.form_submit_button("💾 Apply Current Level", type="primary", width="stretch", disabled=_pending)
    if cur_submitted:
        send_command("Set Charging Current", vm.set_charging_current, vehicle.id, current_level)

# ── Scheduled Departure ────────────────────────────────────────────────────────
elif tab == _TABS[2]:
    st.markdown("#### Scheduled Departure / Preconditioning")
    st.caption("Configure up to two departure times with optional climate pre-conditioning.")

    with st.form("schedule_form"):
        st.markdown("**First Departure**")
        f1_enabled, f1_time, f1_days, f1_clim, f1_temp, f1_defrost = _dep_form(
            "dep1",
            vehicle.ev_first_departure_enabled or False,
            vehicle.ev_first_departure_time or dt_time(7, 0),
            vehicle.ev_first_departure_days or [],
            vehicle.ev_first_departure_climate_enabled or False,
            vehicle.ev_first_departure_climate_temperature or 22.0,
            vehicle.ev_first_departure_climate_defrost or False,
        )
        st.divider()
        st.markdown("**Second Departure**")
        st.caption("Note: The API applies one shared climate setting across both departures. Second departure climate settings here are shown for information only.")
        f2_enabled, f2_time, f2_days, f2_clim, f2_temp, f2_defrost = _dep_form(
            "dep2",
            vehicle.ev_second_departure_enabled or False,
            vehicle.ev_second_departure_time or dt_time(8, 0),
            vehicle.ev_second_departure_days or [],
            vehicle.ev_second_departure_climate_enabled or False,
            vehicle.ev_second_departure_climate_temperature or 22.0,
            vehicle.ev_second_departure_climate_defrost or False,
        )
        st.divider()
        st.markdown("**Charging**")
        sched_charge = st.checkbox("Enable Scheduled Charging", value=vehicle.ev_schedule_charge_enabled or False)

        sched_submitted = st.form_submit_button("📅 Apply Schedule", type="primary", width="stretch", disabled=_pending)

    if sched_submitted:
        opts = ScheduleChargingClimateRequestOptions(
            first_departure=DepartureOptions(
                enabled=f1_enabled,
                days=f1_days,
                time=f1_time,
            ),
            second_departure=DepartureOptions(
                enabled=f2_enabled,
                days=f2_days,
                time=f2_time,
            ),
            charging_enabled=sched_charge,
            climate_enabled=f1_clim,
            temperature=f1_temp,
            temperature_unit=0,
            defrost=f1_defrost,
        )
        send_command("Schedule Charging & Climate", vm.schedule_charging_and_climate, vehicle.id, opts)

# ── Off-Peak Charging ──────────────────────────────────────────────────────────
elif tab == _TABS[3]:
    st.markdown("#### Off-Peak Charging Window")
    st.caption("Charge only during cheaper off-peak electricity hours.")

    with st.form("offpeak_form"):
        op_cols = st.columns(2)
        with op_cols[0]:
            start_time = st.time_input("Off-Peak Start", value=vehicle.ev_off_peak_start_time or dt_time(23, 0))
        with op_cols[1]:
            end_time = st.time_input("Off-Peak End", value=vehicle.ev_off_peak_end_time or dt_time(7, 0))
        off_peak_only = st.checkbox(
            "Charge only during off-peak",
            value=vehicle.ev_off_peak_charge_only_enabled or False,
        )
        op_submitted = st.form_submit_button("💾 Apply Off-Peak Settings", type="primary", width="stretch", disabled=_pending)

    if op_submitted:
        opts = ScheduleChargingClimateRequestOptions(
            off_peak_start_time=start_time,
            off_peak_end_time=end_time,
            off_peak_charge_only_enabled=off_peak_only,
        )
        send_command("Off-Peak Charging", vm.schedule_charging_and_climate, vehicle.id, opts)

# ── Charge Port ────────────────────────────────────────────────────────────────
elif tab == _TABS[4]:
    st.markdown("#### Charge Port Door")
    st.markdown(f"**Current state:** {door_status(vehicle.ev_charge_port_door_is_open)}")
    st.divider()
    cp_cols = st.columns(2)
    with cp_cols[0]:
        if st.button("🔓 Open Charge Port", width="stretch", key="btn_cp_open", disabled=_pending):
            send_command("Open Charge Port", vm.open_charge_port, vehicle.id)
    with cp_cols[1]:
        if st.button("🔒 Close Charge Port", width="stretch", key="btn_cp_close", disabled=_pending):
            send_command("Close Charge Port", vm.close_charge_port, vehicle.id)

# ── V2L / V2X ──────────────────────────────────────────────────────────────────
elif tab == _TABS[5]:
    st.markdown("#### Vehicle-to-Load (V2L) / Vehicle-to-Grid (V2X)")
    if vehicle.ev_v2l_status is None and vehicle.ev_v2l_discharge_limit is None:
        st.info("V2L/V2X data not available for this vehicle/region.")
    else:
        v_cols = st.columns(3)
        with v_cols[0]:
            st.markdown(f"**V2L Status:** {status_dot(vehicle.ev_v2l_status, 'Active', 'Off')}")
        with v_cols[1]:
            st.markdown(f"**V2X Status:** {status_dot(vehicle.ev_v2x_status, 'Active', 'Off')}")
        with v_cols[2]:
            st.markdown(f"**Discharge Limit:** {fmt_val(vehicle.ev_v2l_discharge_limit, '%')}")

        st.divider()
        st.markdown("#### Set V2L Discharge Limit")
        with st.form("v2l_form"):
            v2l_limit = st.slider("Discharge Limit (%)", 10, 100,
                                   vehicle.ev_v2l_discharge_limit or 20, step=5)
            v2l_submitted = st.form_submit_button("💾 Apply V2L Limit", type="primary", width="stretch", disabled=_pending)
        if v2l_submitted:
            send_command("Set V2L Limit", vm.set_vehicle_to_load_discharge_limit, vehicle.id, v2l_limit)
