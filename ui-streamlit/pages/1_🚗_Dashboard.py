"""Dashboard – key metrics, location map, and quick actions."""
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
from utils.helpers import (
    fmt_val, fmt_distance, fmt_time_ago, fmt_datetime,
    lock_status, status_dot, engine_type_badge,
)
from hyundai_kia_connect_api.const import ENGINE_TYPES

st.set_page_config(page_title="Dashboard", page_icon="🚗", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

vm = get_vm()

st.title(f"🚗 {vehicle.name}")
st.caption(f"{vehicle.model} · {vehicle.year or ''} · VIN: {vehicle.VIN or '—'} · {engine_type_badge(vehicle.engine_type)}")

st.divider()

# ── Top metrics row ────────────────────────────────────────────────────────────
cols = st.columns(4)

with cols[0]:
    st.metric("Lock Status", lock_status(vehicle.is_locked))

with cols[1]:
    if vehicle.ev_battery_percentage is not None:
        delta = None
        st.metric("EV Battery", f"{vehicle.ev_battery_percentage}%")
        st.progress(vehicle.ev_battery_percentage / 100)
    elif vehicle.fuel_level is not None:
        st.metric("Fuel Level", f"{vehicle.fuel_level}%")
        st.progress(vehicle.fuel_level / 100)
    else:
        st.metric("Battery / Fuel", "—")

with cols[2]:
    if vehicle.ev_driving_range is not None and vehicle.total_driving_range is not None:
        st.metric("Total Range", fmt_distance(vehicle.total_driving_range, vehicle.total_driving_range_unit))
        st.caption(f"EV: {fmt_distance(vehicle.ev_driving_range, vehicle.ev_driving_range_unit)}")
    elif vehicle.total_driving_range is not None:
        st.metric("Range", fmt_distance(vehicle.total_driving_range, vehicle.total_driving_range_unit))
    elif vehicle.fuel_driving_range is not None:
        st.metric("Fuel Range", fmt_distance(vehicle.fuel_driving_range, vehicle.fuel_driving_range_unit))
    else:
        st.metric("Range", "—")

with cols[3]:
    st.metric("Odometer", fmt_distance(vehicle.odometer, vehicle.odometer_unit))

st.divider()

# ── Second row: charging + engine + last update ────────────────────────────────
cols2 = st.columns(4)

with cols2[0]:
    if vehicle.ev_battery_is_charging is not None:
        charging = vehicle.ev_battery_is_charging
        plugged = vehicle.ev_battery_is_plugged_in
        label = "⚡ Charging" if charging else ("🔌 Plugged in" if plugged else "🔋 Unplugged")
        st.metric("Charge State", label)
        if vehicle.ev_charging_power is not None:
            st.caption(f"{vehicle.ev_charging_power:.1f} kW")
    else:
        st.metric("Engine", status_dot(vehicle.engine_is_running, "Running", "Off"))

with cols2[1]:
    st.metric("12V Battery", fmt_val(vehicle.car_battery_percentage, "%"))

with cols2[2]:
    st.metric("Outside Temp", fmt_val(vehicle.outside_temperature, "°C") if vehicle.outside_temperature is not None else "—")

with cols2[3]:
    st.metric("Last Updated", fmt_time_ago(vehicle.last_updated_at))
    st.caption(fmt_datetime(vehicle.last_updated_at))

st.divider()

# ── Location map ───────────────────────────────────────────────────────────────
lat = vehicle.location_latitude
lon = vehicle.location_longitude

if lat and lon:
    st.subheader("📍 Location")
    try:
        import folium
        from streamlit_folium import st_folium

        m = folium.Map(location=[lat, lon], zoom_start=15, tiles="CartoDB dark_matter")
        folium.Marker(
            [lat, lon],
            popup=f"{vehicle.name}<br>{lat:.5f}, {lon:.5f}",
            icon=folium.Icon(color="blue", icon="car", prefix="fa"),
        ).add_to(m)
        folium.Circle([lat, lon], radius=50, color="#00b4d8", fill=True, fill_opacity=0.15).add_to(m)
        st_folium(m, width="100%", height=340, returned_objects=[])
    except ImportError:
        st.info(f"Map unavailable (folium not installed). Coordinates: {lat:.5f}, {lon:.5f}")

    geo_parts = []
    if vehicle._geocode_name:
        geo_parts.append(vehicle._geocode_name)
    if vehicle._geocode_address and isinstance(vehicle._geocode_address, str):
        geo_parts.append(vehicle._geocode_address)
    if geo_parts:
        st.caption("📌 " + " · ".join(geo_parts))
    st.caption(f"Location updated: {fmt_time_ago(vehicle.location_last_updated_at)}")
else:
    st.info("📍 Location data not available.")

st.divider()

# ── Quick actions ──────────────────────────────────────────────────────────────
st.subheader("⚡ Quick Actions")

def _run_action(label, fn, *args, **kwargs):
    with st.spinner(f"{label}…"):
        try:
            action_id = fn(*args, **kwargs)
            st.toast(f"✅ {label} command sent (ID: {action_id})", icon="✅")
        except Exception as e:
            st.error(f"{label} failed: {e}")

qa_cols = st.columns(6)
with qa_cols[0]:
    if st.button("🔒 Lock", width="stretch"):
        _run_action("Lock", vm.lock, vehicle.id)
with qa_cols[1]:
    if st.button("🔓 Unlock", width="stretch"):
        _run_action("Unlock", vm.unlock, vehicle.id)
with qa_cols[2]:
    if st.button("❄️ Climate On", width="stretch"):
        from hyundai_kia_connect_api import ClimateRequestOptions
        opts = ClimateRequestOptions(set_temp=22.0, duration=10, defrost=False, climate=True, heating=0)
        _run_action("Climate On", vm.start_climate, vehicle.id, opts)
with qa_cols[3]:
    if st.button("🌡️ Climate Off", width="stretch"):
        _run_action("Climate Off", vm.stop_climate, vehicle.id)
with qa_cols[4]:
    if st.button("🚨 Hazard Lights", width="stretch"):
        _run_action("Hazard Lights", vm.start_hazard_lights, vehicle.id)
with qa_cols[5]:
    if st.button("🔔 Horn + Lights", width="stretch"):
        _run_action("Horn + Lights", vm.start_hazard_lights_and_horn, vehicle.id)

# ── Vehicle info ───────────────────────────────────────────────────────────────
with st.expander("ℹ️ Vehicle Details"):
    info_cols = st.columns(3)
    with info_cols[0]:
        st.markdown(f"**Model:** {fmt_val(vehicle.model)}")
        st.markdown(f"**Year:** {fmt_val(vehicle.year)}")
        st.markdown(f"**VIN:** `{fmt_val(vehicle.VIN)}`")
    with info_cols[1]:
        st.markdown(f"**Engine:** {engine_type_badge(vehicle.engine_type)}")
        st.markdown(f"**Generation:** {fmt_val(vehicle.generation)}")
        st.markdown(f"**Registration:** {fmt_val(vehicle.registration_date)}")
    with info_cols[2]:
        st.markdown(f"**Vehicle ID:** `{vehicle.id}`")
        st.markdown(f"**Protocol:** {fmt_val(vehicle.ccu_ccs2_protocol_support)}")

    st.divider()
    enabled = vehicle.enabled if vehicle.enabled is not None else True
    st.markdown(f"**Polling:** {'🟢 Enabled' if enabled else '🔴 Disabled'}")
    st.caption("Disabling a vehicle suspends all background polling for it.")
    tog_cols = st.columns(2)
    with tog_cols[0]:
        if st.button("✅ Enable Vehicle", disabled=enabled, width="stretch", key="btn_enable_vehicle"):
            with st.spinner("Enabling…"):
                try:
                    vm.enable_vehicle(vehicle.id)
                    st.session_state["vehicles"] = list(vm.vehicles.values())
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    with tog_cols[1]:
        if st.button("🚫 Disable Vehicle", disabled=not enabled, width="stretch", key="btn_disable_vehicle"):
            with st.spinner("Disabling…"):
                try:
                    vm.disable_vehicle(vehicle.id)
                    st.session_state["vehicles"] = list(vm.vehicles.values())
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
