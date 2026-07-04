"""Navigation – send POI destinations to the vehicle's built-in nav system."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ui-streamlit/
from utils import _bootstrap  # noqa: F401  (adds repo root for hyundai_kia_connect_api)

import streamlit as st

from utils.session import render_sidebar, get_vm
from hyundai_kia_connect_api import POIInfo, POICoord

st.set_page_config(page_title="Navigation", page_icon="🧭", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

brand = st.session_state.get("_brand")
region = st.session_state.get("_region")
# Europe=1, China=4, Australia=5, India=6 (from const.REGIONS)
SUPPORTED_NAV_REGIONS = {1, 4, 5, 6}
if brand != 1 or region not in SUPPORTED_NAV_REGIONS:
    st.warning("Navigation is only available for Kia vehicles in Europe, Australia, China, and India.")
    st.stop()

vm = get_vm()
st.title("🧭 Navigation")
st.caption(f"{vehicle.name} · {vehicle.model}")
st.info("Send up to 5 waypoints directly to the vehicle's built-in navigation system. Supported on EU, AU, CN, IN regions (Kia).")

# ── POI entry form ─────────────────────────────────────────────────────────────
st.subheader("Add Destination")

with st.form("nav_form"):
    num_pois = st.number_input("Number of waypoints", min_value=1, max_value=5, value=1)

    pois_input = []
    for i in range(int(num_pois)):
        st.markdown(f"**Waypoint {i + 1}**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            name = st.text_input("Name", placeholder="Berlin Central Station", key=f"name_{i}")
        with c2:
            addr = st.text_input("Address", placeholder="Berlin, Germany", key=f"addr_{i}")
        with c3:
            lat = st.number_input("Latitude", value=0.0, format="%.6f", key=f"lat_{i}")
            lon = st.number_input("Longitude", value=0.0, format="%.6f", key=f"lon_{i}")
        with c4:
            zip_code  = st.text_input("ZIP / Postal code", key=f"zip_{i}")
            place_id  = st.text_input("Place ID (optional)", key=f"pid_{i}")
            phone     = st.text_input("Phone (optional)", key=f"phone_{i}")
        pois_input.append((name, addr, lat, lon, zip_code, place_id, phone))
        if i < int(num_pois) - 1:
            st.divider()

    submitted = st.form_submit_button("🧭 Send to Vehicle", type="primary", width="stretch")

if submitted:
    errors = []
    pois = []
    for i, (name, addr, lat, lon, zip_code, place_id, phone) in enumerate(pois_input):
        if lat == 0.0 and lon == 0.0:
            errors.append(f"Waypoint {i + 1}: latitude and longitude cannot both be 0.")
        else:
            pois.append(POIInfo(
                coord=POICoord(lat=lat, lon=lon),
                name=name,
                addr=addr,
                zip=zip_code,
                place_id=place_id,
                phone=phone,
                waypoint_id=i + 1,
            ))

    if errors:
        for e in errors:
            st.error(e)
    else:
        with st.spinner("Sending destination(s) to vehicle…"):
            try:
                vm.set_navigation(vehicle.id, pois)
                st.success(f"✅ {len(pois)} destination(s) sent to the vehicle navigation.")
            except NotImplementedError:
                st.error("Navigation is not supported for this vehicle's region.")
            except Exception as e:
                st.error(f"Failed: {e}")

# ── Quick location picker from vehicle position ────────────────────────────────
if vehicle.location_latitude is not None and vehicle.location_longitude is not None:
    st.divider()
    st.subheader("📍 Current Vehicle Position")
    lat = vehicle.location_latitude
    lon = vehicle.location_longitude
    try:
        import folium
        from streamlit_folium import st_folium

        m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB dark_matter")
        folium.Marker([lat, lon], popup="Vehicle", icon=folium.Icon(color="blue", icon="car", prefix="fa")).add_to(m)
        st_folium(m, width="100%", height=300, returned_objects=[])
    except ImportError:
        st.info(f"Vehicle is at {lat:.5f}, {lon:.5f}")
