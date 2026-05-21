"""Trip History – monthly overview and per-day trip breakdown."""
from __future__ import annotations

import os
import sys
from datetime import datetime, date, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_UI = os.path.abspath(os.path.join(_HERE, ".."))
for p in (_ROOT, _UI):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.session import render_sidebar, get_vm
from utils.helpers import fmt_duration, fmt_speed, fmt_distance

st.set_page_config(page_title="Trip History", page_icon="🗺️", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

vm = get_vm()
st.title("🗺️ Trip History")
st.caption(f"{vehicle.name} · {vehicle.model}")

_tz = vehicle.timezone if vehicle.timezone else timezone.utc


def _parse_trip_start(hhmmss: str | None, yyyymmdd: str) -> datetime | None:
    if not hhmmss or len(hhmmss) < 6:
        return None
    try:
        return datetime(
            int(yyyymmdd[0:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]),
            int(hhmmss[0:2]), int(hhmmss[2:4]), int(hhmmss[4:6]),
            tzinfo=_tz,
        )
    except Exception:
        return None


def _fmt_time(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%H:%M")


# ── Month selector ─────────────────────────────────────────────────────────────
today = date.today()
col_m, col_fetch_m, _ = st.columns([2, 1, 4])
with col_m:
    selected_month = st.date_input(
        "Select Month",
        value=date(today.year, today.month, 1),
        help="Pick any day in the desired month",
    )
with col_fetch_m:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_month = st.button("🔍 Load Month", type="primary")

yyyymm = selected_month.strftime("%Y%m")

if fetch_month:
    with st.spinner(f"Loading trip data for {selected_month.strftime('%B %Y')}…"):
        try:
            vm.update_month_trip_info(vehicle.id, yyyymm)
            st.session_state["vehicles"] = list(vm.vehicles.values())
            for v in st.session_state["vehicles"]:
                if v.id == vehicle.id:
                    vehicle = v
                    break
            st.success(f"Loaded trip data for {selected_month.strftime('%B %Y')}")
        except Exception as e:
            st.error(f"Failed to load month data: {e}")

mti = vehicle.month_trip_info

if mti is None:
    st.info("No monthly trip data loaded. Select a month and click **Load Month**.")
    st.stop()

if mti.yyyymm != yyyymm:
    st.info(f"Showing cached data for {mti.yyyymm[:4]}-{mti.yyyymm[4:]} — click **Load Month** to refresh.")

# ── Month Summary ──────────────────────────────────────────────────────────────
st.subheader(f"📅 {mti.yyyymm[:4]}-{mti.yyyymm[4:]} Summary")

if mti.summary:
    s = mti.summary
    m_cols = st.columns(4)
    with m_cols[0]:
        st.metric("Total Distance", fmt_distance(s.distance, vehicle.odometer_unit))
    with m_cols[1]:
        st.metric("Drive Time", fmt_duration(s.drive_time))
    with m_cols[2]:
        st.metric("Idle Time", fmt_duration(s.idle_time))
    with m_cols[3]:
        st.metric("Avg / Max Speed", f"{fmt_speed(s.avg_speed)} / {fmt_speed(s.max_speed)}")

# ── Days with trips (bar chart) ────────────────────────────────────────────────
if mti.day_list:
    st.divider()
    st.subheader("Trip Count per Day")
    df_days = pd.DataFrame([
        {"Date": f"{d.yyyymmdd[:4]}-{d.yyyymmdd[4:6]}-{d.yyyymmdd[6:]}", "Trips": d.trip_count}
        for d in mti.day_list
    ])
    fig = px.bar(df_days, x="Date", y="Trips", title="Daily Trip Count",
                 color="Trips", color_continuous_scale="Blues")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="#e0e0e0", xaxis_tickangle=-45, showlegend=False)
    st.plotly_chart(fig, width="stretch")

st.divider()

# ── Day drill-down ─────────────────────────────────────────────────────────────
st.subheader("🔍 Day Detail")

days_with_trips = sorted([d.yyyymmdd for d in (mti.day_list or [])], reverse=True)
day_options = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days_with_trips]

col_d, col_fetch_d, _ = st.columns([2, 1, 4])
with col_d:
    if day_options:
        selected_day_label = st.selectbox("Day with trips", day_options)
        selected_day_raw = selected_day_label.replace("-", "")
    else:
        manual_day = st.date_input("Pick a day", value=today)
        selected_day_raw = manual_day.strftime("%Y%m%d")
        selected_day_label = manual_day.strftime("%Y-%m-%d")
with col_fetch_d:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_day = st.button("🔍 Load Day", type="primary")

if fetch_day:
    with st.spinner(f"Loading trips for {selected_day_label}…"):
        try:
            vm.update_day_trip_info(vehicle.id, selected_day_raw)
            st.session_state["vehicles"] = list(vm.vehicles.values())
            for v in st.session_state["vehicles"]:
                if v.id == vehicle.id:
                    vehicle = v
                    break
            st.success(f"Loaded {len(vehicle.day_trip_info.trip_list) if vehicle.day_trip_info else 0} trips for {selected_day_label}")
        except Exception as e:
            st.error(f"Failed to load day data: {e}")

dti = vehicle.day_trip_info
if dti is None:
    st.info("Select a day and click **Load Day** to view individual trips.")
    st.stop()

day_label = f"{dti.yyyymmdd[:4]}-{dti.yyyymmdd[4:6]}-{dti.yyyymmdd[6:]}"
st.markdown(f"### Trips on {day_label}")

# Day summary
if dti.summary:
    s = dti.summary
    ds_cols = st.columns(4)
    with ds_cols[0]:
        st.metric("Day Distance", fmt_distance(s.distance, vehicle.odometer_unit))
    with ds_cols[1]:
        st.metric("Drive Time", fmt_duration(s.drive_time))
    with ds_cols[2]:
        st.metric("Idle Time", fmt_duration(s.idle_time))
    with ds_cols[3]:
        st.metric("Avg / Max Speed", f"{fmt_speed(s.avg_speed)} / {fmt_speed(s.max_speed)}")

st.divider()

if not dti.trip_list:
    st.info("No individual trips found for this day.")
    st.stop()

# ── Build enriched trip list ───────────────────────────────────────────────────
trip_data = []
for i, t in enumerate(dti.trip_list, 1):
    start_dt = _parse_trip_start(t.hhmmss, dti.yyyymmdd)
    total_min = (t.drive_time or 0) + (t.idle_time or 0)
    end_dt = (start_dt + timedelta(minutes=total_min)) if start_dt and total_min else None
    trip_data.append((i, t, start_dt, end_dt))

# Trip table
tz_name = str(_tz) if _tz != timezone.utc else "UTC"
st.markdown(f"**{len(dti.trip_list)} trip(s) recorded** · times in {tz_name}")

rows = []
for i, t, start_dt, end_dt in trip_data:
    rows.append({
        "#": i,
        "Start": _fmt_time(start_dt),
        "End": _fmt_time(end_dt),
        "Distance": fmt_distance(t.distance, vehicle.odometer_unit),
        "Drive Time": fmt_duration(t.drive_time),
        "Idle Time": fmt_duration(t.idle_time),
        "Avg Speed": fmt_speed(t.avg_speed),
        "Max Speed": fmt_speed(t.max_speed),
    })

df = pd.DataFrame(rows)
st.dataframe(df, width="stretch", hide_index=True)

# Chart: distance per trip
if len(dti.trip_list) > 1:
    st.markdown("**Distance per Trip**")
    chart_rows = []
    for i, t, start_dt, end_dt in trip_data:
        if start_dt and end_dt:
            label = f"{_fmt_time(start_dt)} – {_fmt_time(end_dt)}"
        elif start_dt:
            label = _fmt_time(start_dt)
        else:
            label = f"Trip {i}"
        chart_rows.append({"Trip": label, "Distance": t.distance or 0})

    df_chart = pd.DataFrame(chart_rows)
    fig2 = px.bar(df_chart, x="Trip", y="Distance", title="Distance per Trip",
                  color="Distance", color_continuous_scale="Blues",
                  labels={"Distance": f"Distance ({vehicle.odometer_unit or 'km'})",
                          "Trip": "Trip (start – end)"})
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                       font_color="#e0e0e0", showlegend=False)
    st.plotly_chart(fig2, width="stretch")
