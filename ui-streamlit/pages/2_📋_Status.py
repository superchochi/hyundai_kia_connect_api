"""Vehicle Status – detailed read-only status grouped by category."""
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

from utils.session import render_sidebar
from utils.helpers import (
    fmt_val, fmt_bool, status_dot, warning_dot,
    door_status, door_lock_status, fmt_distance, fmt_energy,
)
from hyundai_kia_connect_api.const import SEAT_STATUS, HEAT_STATUS

st.set_page_config(page_title="Vehicle Status", page_icon="📋", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

st.title("📋 Vehicle Status")
st.caption(f"{vehicle.name} · {vehicle.model}")

tabs = st.tabs(["🚪 Doors & Windows", "🌡️ Climate", "⚠️ Warnings", "🔦 Lighting", "⚙️ General", "🔋 EV Battery"])

# ── Doors & Windows ────────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Doors")
    d_cols = st.columns(4)
    doors = [
        ("Front Left", vehicle.front_left_door_is_open, vehicle.front_left_door_is_locked),
        ("Front Right", vehicle.front_right_door_is_open, vehicle.front_right_door_is_locked),
        ("Rear Left", vehicle.back_left_door_is_open, vehicle.back_left_door_is_locked),
        ("Rear Right", vehicle.back_right_door_is_open, vehicle.back_right_door_is_locked),
    ]
    for col, (label, is_open, is_locked) in zip(d_cols, doors):
        with col:
            st.markdown(f"**{label}**")
            st.markdown(door_status(is_open))
            st.markdown(door_lock_status(is_locked))

    st.divider()
    extra_cols = st.columns(3)
    with extra_cols[0]:
        st.markdown("**Trunk**")
        st.markdown(door_status(vehicle.trunk_is_open))
    with extra_cols[1]:
        st.markdown("**Hood**")
        st.markdown(door_status(vehicle.hood_is_open))
    with extra_cols[2]:
        st.markdown("**Overall Lock**")
        from utils.helpers import lock_status
        st.markdown(lock_status(vehicle.is_locked))

    st.divider()
    st.subheader("Windows")
    w_cols = st.columns(5)
    windows = [
        ("Front Left", vehicle.front_left_window_is_open),
        ("Front Right", vehicle.front_right_window_is_open),
        ("Rear Left", vehicle.back_left_window_is_open),
        ("Rear Right", vehicle.back_right_window_is_open),
        ("Sunroof", vehicle.sunroof_is_open),
    ]
    for col, (label, is_open) in zip(w_cols, windows):
        with col:
            st.markdown(f"**{label}**")
            st.markdown(door_status(is_open))

    if vehicle.ev_charge_port_door_is_open is not None:
        st.divider()
        st.markdown(f"**Charge Port Door:** {door_status(vehicle.ev_charge_port_door_is_open)}")

# ── Climate ────────────────────────────────────────────────────────────────────
with tabs[1]:
    c_cols = st.columns(3)
    with c_cols[0]:
        st.markdown("**A/C**")
        st.markdown(status_dot(vehicle.air_control_is_on, "On", "Off"))
        if vehicle.air_temperature is not None:
            st.markdown(f"Cabin temp: **{vehicle.air_temperature} °C**")
    with c_cols[1]:
        st.markdown("**Defrost**")
        st.markdown(status_dot(vehicle.defrost_is_on, "On", "Off"))
    with c_cols[2]:
        st.markdown("**Outside Temp**")
        st.markdown(fmt_val(vehicle.outside_temperature, "°C"))

    st.divider()
    st.subheader("Seat Heaters / Coolers")
    s_cols = st.columns(4)
    seats = [
        ("Front Left", vehicle.front_left_seat_status),
        ("Front Right", vehicle.front_right_seat_status),
        ("Rear Left", vehicle.rear_left_seat_status),
        ("Rear Right", vehicle.rear_right_seat_status),
    ]
    for col, (label, status) in zip(s_cols, seats):
        with col:
            st.markdown(f"**{label}**")
            display = SEAT_STATUS.get(status, str(status) if status is not None else "—")
            st.markdown(display or "—")

    st.divider()
    st.subheader("Heaters")
    h_cols = st.columns(3)
    with h_cols[0]:
        st.markdown("**Steering Wheel**")
        st.markdown(status_dot(vehicle.steering_wheel_heater_is_on, "On", "Off"))
    with h_cols[1]:
        st.markdown("**Rear Window**")
        st.markdown(status_dot(vehicle.back_window_heater_is_on, "On", "Off"))
    with h_cols[2]:
        st.markdown("**Side Mirrors**")
        st.markdown(status_dot(vehicle.side_mirror_heater_is_on, "On", "Off"))

# ── Warnings & Diagnostics ─────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Tire Pressure")
    tp_cols = st.columns(5)
    tires = [
        ("All", vehicle.tire_pressure_all_warning_is_on),
        ("Front Left", vehicle.tire_pressure_front_left_warning_is_on),
        ("Front Right", vehicle.tire_pressure_front_right_warning_is_on),
        ("Rear Left", vehicle.tire_pressure_rear_left_warning_is_on),
        ("Rear Right", vehicle.tire_pressure_rear_right_warning_is_on),
    ]
    for col, (label, warn) in zip(tp_cols, tires):
        with col:
            st.markdown(f"**{label}**")
            st.markdown(warning_dot(warn))

    st.divider()
    st.subheader("Fluid & Battery Warnings")
    w_cols = st.columns(3)
    with w_cols[0]:
        st.markdown("**Washer Fluid**")
        st.markdown(warning_dot(vehicle.washer_fluid_warning_is_on))
    with w_cols[1]:
        st.markdown("**Brake Fluid**")
        st.markdown(warning_dot(vehicle.brake_fluid_warning_is_on))
    with w_cols[2]:
        st.markdown("**Smart Key Battery**")
        st.markdown(warning_dot(vehicle.smart_key_battery_warning_is_on))

    st.divider()
    st.subheader("Diagnostic Trouble Codes (DTC)")
    if vehicle.dtc_count:
        st.error(f"⚠️ {vehicle.dtc_count} DTC(s) active")
        if vehicle.dtc_descriptions:
            for code, desc in (vehicle.dtc_descriptions or {}).items():
                st.markdown(f"- `{code}`: {desc}")
    else:
        st.success("🟢 No active DTCs")

    st.divider()
    st.subheader("Service")
    sv_cols = st.columns(2)
    with sv_cols[0]:
        st.metric("Distance to Next Service", fmt_distance(vehicle.next_service_distance, vehicle.odometer_unit))
    with sv_cols[1]:
        st.metric("Distance Since Last Service", fmt_distance(vehicle.last_service_distance, vehicle.odometer_unit))

# ── Lighting ───────────────────────────────────────────────────────────────────
with tabs[3]:
    if all(v is None for v in [
        vehicle.headlamp_status, vehicle.headlamp_left_low, vehicle.stop_lamp_left,
        vehicle.turn_signal_left_front,
    ]):
        st.info("Lighting data not available for this vehicle/region.")
    else:
        l_cols = st.columns(3)
        with l_cols[0]:
            st.markdown("**Headlamps**")
            st.markdown(fmt_val(vehicle.headlamp_status, fallback="—"))
            st.markdown(f"Left low: {status_dot(vehicle.headlamp_left_low)}")
            st.markdown(f"Right low: {status_dot(vehicle.headlamp_right_low)}")
        with l_cols[1]:
            st.markdown("**Stop Lamps**")
            st.markdown(f"Left: {status_dot(vehicle.stop_lamp_left)}")
            st.markdown(f"Right: {status_dot(vehicle.stop_lamp_right)}")
        with l_cols[2]:
            st.markdown("**Turn Signals**")
            st.markdown(f"Front Left: {status_dot(vehicle.turn_signal_left_front)}")
            st.markdown(f"Front Right: {status_dot(vehicle.turn_signal_right_front)}")
            st.markdown(f"Rear Left: {status_dot(vehicle.turn_signal_left_rear)}")
            st.markdown(f"Rear Right: {status_dot(vehicle.turn_signal_right_rear)}")

# ── General ────────────────────────────────────────────────────────────────────
with tabs[4]:
    g_cols = st.columns(3)
    with g_cols[0]:
        st.markdown("**Engine / Motor**")
        st.markdown(status_dot(vehicle.engine_is_running, "Running", "Off"))
        if vehicle.ign3 is not None:
            st.markdown(f"**Ignition:** {status_dot(vehicle.ign3, 'On', 'Off')}")
        if vehicle.transmission_condition is not None:
            st.markdown(f"**Transmission:** {vehicle.transmission_condition}")
        if vehicle.remote_ignition is not None:
            st.markdown(f"**Remote Ignition:** {fmt_bool(vehicle.remote_ignition)}")
        if vehicle.accessory_on is not None:
            st.markdown(f"**Accessory:** {status_dot(vehicle.accessory_on, 'On', 'Off')}")
    with g_cols[1]:
        st.markdown("**Fuel**")
        st.markdown(f"Level: {fmt_val(vehicle.fuel_level, '%')}")
        st.markdown(f"Low: {warning_dot(vehicle.fuel_level_is_low, 'Low', 'OK')}")
        st.markdown(f"Range: {fmt_distance(vehicle.fuel_driving_range, vehicle.odometer_unit)}")
    with g_cols[2]:
        st.markdown("**12V Battery**")
        st.markdown(f"Level: {fmt_val(vehicle.car_battery_percentage, '%')}")
        if vehicle.sleep_mode_check is not None:
            st.markdown(f"**Sleep Mode:** {fmt_bool(vehicle.sleep_mode_check)}")

# ── EV Battery ─────────────────────────────────────────────────────────────────
with tabs[5]:
    if vehicle.ev_battery_percentage is None:
        st.info("This vehicle does not have EV battery data (ICE vehicle or data unavailable).")
    else:
        ev_cols = st.columns(3)
        with ev_cols[0]:
            st.metric("State of Charge", f"{vehicle.ev_battery_percentage}%")
            st.progress(vehicle.ev_battery_percentage / 100)
            if vehicle.ev_battery_soh_percentage is not None:
                st.metric("State of Health", f"{vehicle.ev_battery_soh_percentage}%")
        with ev_cols[1]:
            st.markdown("**Charging**")
            st.markdown(f"Charging: {status_dot(vehicle.ev_battery_is_charging, 'Yes', 'No')}")
            st.markdown(f"Plugged in: {status_dot(vehicle.ev_battery_is_plugged_in, 'Yes', 'No')}")
            if vehicle.ev_charging_power is not None:
                st.markdown(f"Power: **{vehicle.ev_charging_power:.1f} kW**")
        with ev_cols[2]:
            st.markdown("**Capacity**")
            st.markdown(f"Remaining: {fmt_val(vehicle.ev_battery_remain, 'kWh')}")
            st.markdown(f"Total: {fmt_val(vehicle.ev_battery_capacity, 'kWh')}")
            st.markdown(f"Pack Voltage: {fmt_val(vehicle.ev_battery_pack_voltage, 'V')}")

        st.divider()
        st.subheader("Thermal Management")
        th_cols = st.columns(4)
        with th_cols[0]:
            st.metric("Min Cell Temp", fmt_val(vehicle.ev_battery_temperature_min, "°C"))
        with th_cols[1]:
            st.metric("Max Cell Temp", fmt_val(vehicle.ev_battery_temperature_max, "°C"))
        with th_cols[2]:
            st.metric("Coolant Temp", fmt_val(vehicle.ev_battery_water_temperature, "°C"))
        with th_cols[3]:
            st.metric("Chiller RPM", fmt_val(vehicle.ev_battery_chiller_rpm))

        st.markdown(f"**Heater Active:** {status_dot(vehicle.ev_battery_heating_state, 'Yes', 'No')}")
        st.markdown(f"**Winter Mode:** {status_dot(vehicle.ev_battery_winter_mode, 'On', 'Off')}")
        if vehicle.ev_battery_precondition_enabled is not None:
            st.markdown(f"**Preconditioning:** {status_dot(vehicle.ev_battery_precondition_enabled, 'Active', 'Off')}")

        st.divider()
        st.subheader("Range Estimates")
        r_cols = st.columns(2)
        with r_cols[0]:
            st.metric("EV Range", fmt_distance(vehicle.ev_driving_range, vehicle.ev_driving_range_unit))
            st.metric("Target Range (AC)", fmt_distance(vehicle.ev_target_range_charge_AC, vehicle.ev_driving_range_unit))
            st.metric("Target Range (DC)", fmt_distance(vehicle.ev_target_range_charge_DC, vehicle.ev_driving_range_unit))
        with r_cols[1]:
            st.metric("Time to 100% (current)", fmt_val(vehicle.ev_estimated_current_charge_duration, "min"))
            st.metric("DC Fast Charge to 80%", fmt_val(vehicle.ev_estimated_fast_charge_duration, "min"))
            st.metric("Level 2 Charge", fmt_val(vehicle.ev_estimated_station_charge_duration, "min"))
            st.metric("120V Charge", fmt_val(vehicle.ev_estimated_portable_charge_duration, "min"))

        st.divider()
        st.subheader("Lifetime Energy (EU)")
        en_cols = st.columns(3)
        with en_cols[0]:
            st.metric("Total Consumed", fmt_energy(vehicle.total_power_consumed))
        with en_cols[1]:
            st.metric("Total Regenerated", fmt_energy(vehicle.total_power_regenerated))
        with en_cols[2]:
            st.metric("Last 30 Days", fmt_energy(vehicle.power_consumption_30d))

        if vehicle.ev_v2l_status is not None or vehicle.ev_v2x_status is not None:
            st.divider()
            st.subheader("V2L / V2X")
            v_cols = st.columns(3)
            with v_cols[0]:
                st.markdown(f"**V2L:** {status_dot(vehicle.ev_v2l_status, 'Active', 'Off')}")
            with v_cols[1]:
                st.markdown(f"**V2X:** {status_dot(vehicle.ev_v2x_status, 'Active', 'Off')}")
            with v_cols[2]:
                st.markdown(f"**V2L Discharge Limit:** {fmt_val(vehicle.ev_v2l_discharge_limit, '%')}")
