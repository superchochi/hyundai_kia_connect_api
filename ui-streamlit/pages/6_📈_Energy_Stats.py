"""Energy Stats – daily EV driving energy breakdown with charts."""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_UI = os.path.abspath(os.path.join(_HERE, ".."))
for p in (_ROOT, _UI):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.session import render_sidebar
from utils.helpers import fmt_energy, fmt_distance

st.set_page_config(page_title="Energy Stats", page_icon="📈", layout="wide")

vehicle = render_sidebar()
if vehicle is None:
    st.stop()

st.title("📈 Energy Statistics")
st.caption(f"{vehicle.name} · {vehicle.model}")

# ── Lifetime & 30-day summary ──────────────────────────────────────────────────
has_ev_energy = any([
    vehicle.total_power_consumed,
    vehicle.total_power_regenerated,
    vehicle.power_consumption_30d,
])

if has_ev_energy:
    st.subheader("⚡ Lifetime & 30-Day Energy")
    e_cols = st.columns(3)
    with e_cols[0]:
        st.metric("Total Consumed (lifetime)", fmt_energy(vehicle.total_power_consumed))
    with e_cols[1]:
        st.metric("Total Regenerated (lifetime)", fmt_energy(vehicle.total_power_regenerated))
    with e_cols[2]:
        st.metric("Consumed (last 30 days)", fmt_energy(vehicle.power_consumption_30d))

    if any([vehicle.ev_power_consumption_battery_cooling,
            vehicle.ev_power_consumption_battery_heater,
            vehicle.ev_power_consumption_air_conditioning]):
        st.divider()
        st.subheader("Recent Energy Breakdown")
        breakdown_cols = st.columns(3)
        with breakdown_cols[0]:
            st.metric("Battery Cooling", fmt_energy(vehicle.ev_power_consumption_battery_cooling))
        with breakdown_cols[1]:
            st.metric("Battery Heating", fmt_energy(vehicle.ev_power_consumption_battery_heater))
        with breakdown_cols[2]:
            st.metric("Air Conditioning", fmt_energy(vehicle.ev_power_consumption_air_conditioning))

    st.divider()

# ── Daily Driving Stats ────────────────────────────────────────────────────────
daily = vehicle.daily_stats

if not daily:
    st.info("No daily driving statistics available for this vehicle/region.")
    st.stop()

st.subheader(f"📅 Daily Driving Statistics ({len(daily)} days)")

# Build DataFrame
rows = []
for d in daily:
    rows.append({
        "Date": d.date.strftime("%Y-%m-%d") if d.date else "Unknown",
        "Distance": d.distance or 0,
        "Total (Wh)": d.total_consumed or 0,
        "Engine (Wh)": d.engine_consumption or 0,
        "Climate (Wh)": d.climate_consumption or 0,
        "Electronics (Wh)": d.onboard_electronics_consumption or 0,
        "Battery Care (Wh)": d.battery_care_consumption or 0,
        "Regenerated (Wh)": d.regenerated_energy or 0,
    })

df = pd.DataFrame(rows)
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

# KPI row (last 7 days)
recent = df.tail(7)
st.markdown("**Last 7 Days**")
k_cols = st.columns(4)
with k_cols[0]:
    st.metric("Total Distance", fmt_distance(recent["Distance"].sum(), vehicle.odometer_unit))
with k_cols[1]:
    st.metric("Total Consumed", fmt_energy(int(recent["Total (Wh)"].sum())))
with k_cols[2]:
    st.metric("Total Regenerated", fmt_energy(int(recent["Regenerated (Wh)"].sum())))
with k_cols[3]:
    net = recent["Total (Wh)"].sum() - recent["Regenerated (Wh)"].sum()
    st.metric("Net Consumption", fmt_energy(int(net)))

st.divider()

# Chart 1: Distance over time
fig_dist = px.bar(
    df, x="Date", y="Distance",
    title="Daily Distance",
    color="Distance",
    color_continuous_scale="Blues",
    labels={"Distance": f"Distance ({vehicle.odometer_unit or 'km'})"},
)
fig_dist.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font_color="#e0e0e0", showlegend=False,
)
st.plotly_chart(fig_dist, width="stretch")

# Chart 2: Stacked energy breakdown
fig_energy = go.Figure()
categories = [
    ("Engine", "Engine (Wh)", "#00b4d8"),
    ("Climate", "Climate (Wh)", "#48cae4"),
    ("Electronics", "Electronics (Wh)", "#90e0ef"),
    ("Battery Care", "Battery Care (Wh)", "#caf0f8"),
]
for label, col, color in categories:
    fig_energy.add_trace(go.Bar(
        name=label, x=df["Date"], y=df[col], marker_color=color,
    ))

fig_energy.add_trace(go.Scatter(
    name="Regenerated", x=df["Date"], y=df["Regenerated (Wh)"],
    mode="lines+markers", line=dict(color="#ff6b6b", width=2),
    marker=dict(size=6),
))

fig_energy.update_layout(
    title="Daily Energy Breakdown",
    barmode="stack",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font_color="#e0e0e0",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis_title="Energy (Wh)",
)
st.plotly_chart(fig_energy, width="stretch")

# Chart 3: Efficiency (Wh/km)
df["Net (Wh)"] = df["Total (Wh)"] - df["Regenerated (Wh)"]
df["Efficiency"] = df.apply(
    lambda row: round(row["Net (Wh)"] / row["Distance"], 1) if row["Distance"] > 0 else None, axis=1
)
df_eff = df.dropna(subset=["Efficiency"])
if not df_eff.empty:
    fig_eff = px.line(
        df_eff, x="Date", y="Efficiency",
        title="Energy Efficiency (Net Wh/km)",
        markers=True,
        color_discrete_sequence=["#00b4d8"],
    )
    fig_eff.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0", yaxis_title="Wh/km",
    )
    st.plotly_chart(fig_eff, width="stretch")

st.divider()

# Raw table (collapsible)
with st.expander("📊 Raw Daily Data Table"):
    display_df = df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df["Distance"] = display_df["Distance"].apply(lambda x: f"{x:.1f} {vehicle.odometer_unit or 'km'}")
    for col in ["Total (Wh)", "Engine (Wh)", "Climate (Wh)", "Electronics (Wh)", "Battery Care (Wh)", "Regenerated (Wh)", "Net (Wh)"]:
        display_df[col] = display_df[col].apply(lambda x: fmt_energy(int(x)) if pd.notna(x) else "—")
    display_df["Efficiency"] = display_df["Efficiency"].apply(lambda x: f"{x} Wh/km" if pd.notna(x) else "—")
    st.dataframe(display_df, width="stretch", hide_index=True)
