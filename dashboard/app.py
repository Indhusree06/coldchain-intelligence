import streamlit as st
import sqlite3
import os
import joblib
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import folium
from streamlit_folium import st_folium
import openai
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Cold Chain Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# DARK THEME CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .metric-card {
        background-color: #1c1f26;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 4px 0;
    }
    .risk-high   { color: #ff4b4b; font-weight: bold; }
    .risk-medium { color: #ffa500; font-weight: bold; }
    .risk-low    { color: #00cc66; font-weight: bold; }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
        border-bottom: 1px solid #2d3748;
        padding-bottom: 4px;
    }
    /* Fix button text visibility in dark theme */
    .stButton > button {
        background-color: #1c1f26 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        border-radius: 6px !important;
        font-size: 0.85rem !important;
        padding: 6px 12px !important;
        width: 100% !important;
        text-align: left !important;
        white-space: normal !important;
        height: auto !important;
        min-height: 38px !important;
    }
    .stButton > button:hover {
        background-color: #2d3748 !important;
        border-color: #718096 !important;
        color: #ffffff !important;
    }
    /* Fix sidebar button (Refresh Data) */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #2d3748 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        text-align: center !important;
    }
    /* Fix text input */
    .stTextInput > div > div > input {
        background-color: #1c1f26 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, '..', 'data', 'coldchain.db')
MODELS_DIR  = os.path.join(BASE_DIR, '..', 'models')

# ─────────────────────────────────────────
# LOAD MODELS
# ─────────────────────────────────────────
@st.cache_resource
def load_models():
    risk_model       = joblib.load(os.path.join(MODELS_DIR, 'risk_model.pkl'))
    spoilage_model   = joblib.load(os.path.join(MODELS_DIR, 'spoilage_model.pkl'))
    encoders         = joblib.load(os.path.join(MODELS_DIR, 'encoders.pkl'))
    feature_list     = joblib.load(os.path.join(MODELS_DIR, 'feature_list.pkl'))
    spoilage_feats   = joblib.load(os.path.join(MODELS_DIR, 'spoilage_features.pkl'))
    model_results    = joblib.load(os.path.join(MODELS_DIR, 'model_results.pkl'))
    return risk_model, spoilage_model, encoders, feature_list, spoilage_feats, model_results

risk_model, spoilage_model, encoders, feature_list, spoilage_feats, model_results = load_models()

# ─────────────────────────────────────────
# DATABASE HELPER
# ─────────────────────────────────────────
@st.cache_data(ttl=5)
def run_query(query, params=None):
    conn = sqlite3.connect(DB_PATH)
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df
# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## Cold Chain Intelligence")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        options=["Live Monitor", "Shipment Detail", "Analytics", "AI Analyst", "Model Performance"],
        index=0
    )

    st.markdown("---")
    st.markdown("### Filters")

    product_filter = st.multiselect(
        "Product Type",
        options=["Vaccine", "Seafood", "Dairy", "Fresh Produce", "Pharmaceuticals", "Frozen Meat", "Ice Cream"],
        default=[]
    )

    risk_filter = st.multiselect(
        "Risk Level",
        options=["high", "medium", "low"],
        default=[]
    )

    st.markdown("---")
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ─────────────────────────────────────────
# LOAD CORE DATA
# ─────────────────────────────────────────
shipments_df = run_query("""
    SELECT
        s.shipment_id,
        s.product_type,
        s.origin_city,
        s.destination_city,
        c.carrier_name,
        s.vehicle_type,
        s.shipment_value_usd,
        s.safe_temp_min,
        s.safe_temp_max,
        s.departure_time,
        s.expected_arrival,
        s.actual_arrival,
        s.delay_hours,
        s.spoilage_occurred,
        s.origin_lat,
        s.origin_lon,
        s.dest_lat,
        s.dest_lon,
        s.alt_route,
        s.weather_risk,
        s.carrier_id,
        c.reliability_score,
        c.on_time_rate,
        c.avg_temp_deviation,
        c.spoilage_count
    FROM shipments s
    LEFT JOIN carriers c ON s.carrier_id = c.carrier_id
""")


# Apply sidebar filters
if product_filter:
    shipments_df = shipments_df[shipments_df["product_type"].isin(product_filter)]

# Get latest sensor reading per shipment
latest_readings = run_query("""
    SELECT
        sr.shipment_id,
        sr.temp_inside_celsius,
        sr.temp_outside_celsius,
        sr.humidity_percent,
        sr.refrigerator_status,
        sr.door_open_event,
        sr.weather_condition,
        sr.delay_hours_so_far,
        sr.gps_latitude,
        sr.gps_longitude,
        sr.timestamp
    FROM sensor_readings sr
    INNER JOIN (
        SELECT shipment_id, MAX(timestamp) as max_ts
        FROM sensor_readings
        GROUP BY shipment_id
    ) latest ON sr.shipment_id = latest.shipment_id AND sr.timestamp = latest.max_ts
""")

# Merge shipments with latest readings
df = shipments_df.merge(latest_readings, on="shipment_id", how="left")

# ─────────────────────────────────────────
# COMPUTE RISK SCORE USING ML MODEL
# ─────────────────────────────────────────
def compute_risk(row):
    try:
        temp_dev = abs(row["temp_inside_celsius"] - ((row["safe_temp_min"] + row["safe_temp_max"]) / 2))
        fridge_fail = 1 if row["refrigerator_status"] == "Failed" else 0
        weather_risk_num = {"low": 0, "medium": 1, "high": 2}.get(str(row["weather_risk"]).lower(), 1)

        features = {
            "temp_inside_celsius":  row["temp_inside_celsius"],
            "temp_outside_celsius": row["temp_outside_celsius"],
            "humidity_percent":     row["humidity_percent"],
            "door_open_event":      row["door_open_event"],
            "delay_hours_so_far":   row["delay_hours_so_far"],
            "safe_temp_min":        row["safe_temp_min"],
            "safe_temp_max":        row["safe_temp_max"],
            "temp_deviation":       temp_dev,
            "fridge_failure":       fridge_fail,
            "reliability_score":    row["reliability_score"] if pd.notna(row["reliability_score"]) else 75.0,
            "weather_risk_num":     weather_risk_num
        }

        X = pd.DataFrame([features])
        pred = risk_model.predict(X)[0]
        return pred
    except:
        return "unknown"

df["risk_level"] = df.apply(compute_risk, axis=1)

# Apply risk filter
if risk_filter:
    df = df[df["risk_level"].isin(risk_filter)]

# ─────────────────────────────────────────
# KPI BANNER — shown on all pages
# ─────────────────────────────────────────
total       = len(df)
high_risk   = len(df[df["risk_level"] == "high"])
medium_risk = len(df[df["risk_level"] == "medium"])
low_risk    = len(df[df["risk_level"] == "low"])
spoiled     = len(df[df["spoilage_occurred"] == 1])
alerts_df   = run_query("SELECT * FROM alerts WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 100")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Shipments",  f"{total:,}")
col2.metric("High Risk",        f"{high_risk:,}",   delta=None)
col3.metric("Medium Risk",      f"{medium_risk:,}")
col4.metric("Low Risk",         f"{low_risk:,}")
col5.metric("Spoiled",          f"{spoiled:,}")

st.markdown("---")
# ─────────────────────────────────────────
# PAGE: LIVE MONITOR
# ─────────────────────────────────────────
if page == "Live Monitor":

    st.markdown("## Live Shipment Monitor")
    st.markdown("Real-time risk status of all active shipments across the cold chain network.")

    # ── MAP ──────────────────────────────
    st.markdown("### Shipment Map")

    m = folium.Map(location=[39.5, -98.35], zoom_start=4, tiles="CartoDB dark_matter")

    risk_colors = {"high": "red", "medium": "orange", "low": "green", "unknown": "gray"}

    for _, row in df.iterrows():
        if pd.isna(row["origin_lat"]) or pd.isna(row["dest_lat"]):
            continue

        risk    = str(row["risk_level"]).lower()
        color   = risk_colors.get(risk, "gray")

        # Draw route line
        folium.PolyLine(
            locations=[
                [row["origin_lat"], row["origin_lon"]],
                [row["dest_lat"],   row["dest_lon"]]
            ],
            color=color,
            weight=1.5,
            opacity=0.4
        ).add_to(m)

        # Draw shipment marker at current GPS position
        lat = row["gps_latitude"]  if pd.notna(row["gps_latitude"])  else row["origin_lat"]
        lon = row["gps_longitude"] if pd.notna(row["gps_longitude"]) else row["origin_lon"]

        popup_text = f"""
        <b>{row['shipment_id']}</b>  

        Product: {row['product_type']}  

        Route: {row['origin_city']} to {row['destination_city']}  

        Temp Inside: {row['temp_inside_celsius']:.1f} C  

        Safe Range: {row['safe_temp_min']} - {row['safe_temp_max']} C  

        Risk: <b style='color:{color}'>{risk.upper()}</b>  

        Carrier: {row['carrier_name']}
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_text, max_width=250)
        ).add_to(m)

        # Show reroute line for high risk shipments
        if risk == "high" and pd.notna(row.get("alt_route")):
            folium.PolyLine(
                locations=[
                    [row["origin_lat"], row["origin_lon"]],
                    [row["dest_lat"],   row["dest_lon"]]
                ],
                color="cyan",
                weight=2,
                opacity=0.6,
                dash_array="10",
                tooltip=f"Suggested reroute: {row['alt_route']}"
            ).add_to(m)

    st_folium(m, width=None, height=500, returned_objects=[])

    # ── RISK TABLE ────────────────────────
    st.markdown("### Shipment Risk Table")

    display_cols = [
        "shipment_id", "product_type", "origin_city", "destination_city",
        "carrier_name", "temp_inside_celsius", "safe_temp_min", "safe_temp_max",
        "risk_level", "delay_hours", "spoilage_occurred"
    ]

    table_df = df[display_cols].copy()
    table_df.columns = [
        "Shipment ID", "Product", "Origin", "Destination",
        "Carrier", "Temp Inside (C)", "Safe Min", "Safe Max",
        "Risk Level", "Delay (hrs)", "Spoiled"
    ]

    # Color risk level column
    def color_risk(val):
        colors = {"high": "background-color: #3d0000; color: #ff4b4b",
                  "medium": "background-color: #3d2200; color: #ffa500",
                  "low": "background-color: #003d1a; color: #00cc66"}
        return colors.get(str(val).lower(), "")

    styled = table_df.style.applymap(color_risk, subset=["Risk Level"])
    st.dataframe(styled, use_container_width='stretch', height=400)

    # ── ACTIVE ALERTS ─────────────────────
    st.markdown("### Active Alerts")

    if len(alerts_df) > 0:
        st.dataframe(alerts_df[["shipment_id", "alert_type", "severity", "message", "timestamp"]],
                     use_container_width='stretch', height=200)
    else:
        st.info("No active alerts at this time.")
# ─────────────────────────────────────────
# PAGE: SHIPMENT DETAIL
# ─────────────────────────────────────────
elif page == "Shipment Detail":

    st.markdown("## Shipment Detail")
    st.markdown("Select a shipment to view its full sensor history, risk explanation, and spoilage probability.")

    # Shipment selector
    shipment_ids = df["shipment_id"].tolist()
    selected_id  = st.selectbox("Select Shipment", options=shipment_ids)

    if selected_id:
        row = df[df["shipment_id"] == selected_id].iloc[0]

        # ── SHIPMENT INFO ─────────────────
        st.markdown("### Shipment Information")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Product",        row["product_type"])
        c2.metric("Route",          f"{row['origin_city']} to {row['destination_city']}")
        c3.metric("Carrier",        row["carrier_name"])
        c4.metric("Vehicle",        row["vehicle_type"])

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Safe Temp Range", f"{row['safe_temp_min']} to {row['safe_temp_max']} C")
        c6.metric("Current Temp",    f"{row['temp_inside_celsius']:.1f} C")
        c7.metric("Delay",           f"{row['delay_hours']:.1f} hrs")
        c8.metric("Risk Level",      str(row["risk_level"]).upper())

        st.markdown("---")

        # ── TEMPERATURE HISTORY CHART ─────
        st.markdown("### Temperature History")

        readings = run_query("""
            SELECT timestamp, temp_inside_celsius, temp_outside_celsius,
                   humidity_percent, refrigerator_status, door_open_event
            FROM sensor_readings
            WHERE shipment_id = ?
            ORDER BY timestamp ASC
        """, params=(selected_id,))

        if len(readings) > 0:
            fig = go.Figure()

            # Inside temperature line
            fig.add_trace(go.Scatter(
                x=readings["timestamp"],
                y=readings["temp_inside_celsius"],
                mode="lines",
                name="Temp Inside (C)",
                line=dict(color="#00aaff", width=2)
            ))

            # Outside temperature line
            fig.add_trace(go.Scatter(
                x=readings["timestamp"],
                y=readings["temp_outside_celsius"],
                mode="lines",
                name="Temp Outside (C)",
                line=dict(color="#ff8800", width=1.5, dash="dot")
            ))

            # Safe temperature band
            fig.add_hrect(
                y0=row["safe_temp_min"],
                y1=row["safe_temp_max"],
                fillcolor="rgba(0,200,100,0.1)",
                line_width=0,
                annotation_text="Safe Zone",
                annotation_position="top left"
            )

            # Safe temp boundary lines
            fig.add_hline(y=row["safe_temp_min"], line_dash="dash",
                          line_color="rgba(0,200,100,0.5)", annotation_text="Min Safe")
            fig.add_hline(y=row["safe_temp_max"], line_dash="dash",
                          line_color="rgba(0,200,100,0.5)", annotation_text="Max Safe")

            fig.update_layout(
                template="plotly_dark",
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis_title="Time",
                yaxis_title="Temperature (C)"
            )

            st.plotly_chart(fig, use_container_width='stretch')

            # Door open events
            door_events = readings[readings["door_open_event"] == 1]
            if len(door_events) > 0:
                st.warning(f"Door open events detected: {len(door_events)} times during transit")

            # Fridge failures
            fridge_fail = readings[readings["refrigerator_status"] == "Failed"]
            if len(fridge_fail) > 0:
                st.error(f"Refrigeration unit failure detected: {len(fridge_fail)} readings showed failure status")

        st.markdown("---")

        # ── SPOILAGE PROBABILITY ──────────
        st.markdown("### Spoilage Probability")

        try:
            temp_dev     = abs(row["temp_inside_celsius"] - ((row["safe_temp_min"] + row["safe_temp_max"]) / 2))
            fridge_fail  = 1 if row["refrigerator_status"] == "Failed" else 0
            weather_num  = {"low": 0, "medium": 1, "high": 2}.get(str(row["weather_risk"]).lower(), 1)
            le_p         = encoders["product"]
            le_v         = encoders["vehicle"]

            product_enc  = le_p.transform([row["product_type"]])[0]  if row["product_type"]  in le_p.classes_ else 0
            vehicle_enc  = le_v.transform([row["vehicle_type"]])[0]  if row["vehicle_type"]  in le_v.classes_ else 0

            spoi_feats = {
                "avg_temp_inside":      row["temp_inside_celsius"],
                "max_temp_inside":      row["temp_inside_celsius"],
                "min_temp_inside":      row["temp_inside_celsius"],
                "avg_temp_outside":     row["temp_outside_celsius"],
                "avg_humidity":         row["humidity_percent"],
                "total_door_opens":     row["door_open_event"],
                "fridge_failures":      fridge_fail,
                "fridge_fail_rate":     fridge_fail,
                "hours_above_safe":     max(0, row["temp_inside_celsius"] - row["safe_temp_max"]),
                "hours_below_safe":     max(0, row["safe_temp_min"] - row["temp_inside_celsius"]),
                "temp_breach_rate":     temp_dev / max(1, (row["safe_temp_max"] - row["safe_temp_min"])),
                "temp_range_stress":    temp_dev,
                "delay_hours":          row["delay_hours"],
                "route_distance_km":    1500,
                "weather_risk_num":     weather_num,
                "reliability_score":    row["reliability_score"] if pd.notna(row["reliability_score"]) else 75.0,
                "on_time_rate":         row["on_time_rate"]       if pd.notna(row["on_time_rate"])       else 0.85,
                "avg_temp_deviation":   row["avg_temp_deviation"] if pd.notna(row["avg_temp_deviation"]) else 1.0,
                "product_enc":          product_enc,
                "vehicle_enc":          vehicle_enc
            }

            X_spoi = pd.DataFrame([spoi_feats])
            spoi_prob = float(spoilage_model.predict(X_spoi)[0])
            spoi_prob = max(0.0, min(1.0, spoi_prob))

            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.metric("Spoilage Probability", f"{spoi_prob*100:.1f}%")
                if spoi_prob >= 0.6:
                    st.error("High probability of spoilage. Immediate action recommended.")
                elif spoi_prob >= 0.3:
                    st.warning("Moderate spoilage risk. Monitor closely.")
                else:
                    st.success("Low spoilage risk. Shipment appears stable.")

            with col_b:
                gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=round(spoi_prob * 100, 1),
                    title={"text": "Spoilage Risk %"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar":  {"color": "#ff4b4b" if spoi_prob >= 0.6 else "#ffa500" if spoi_prob >= 0.3 else "#00cc66"},
                        "steps": [
                            {"range": [0,  30],  "color": "#003d1a"},
                            {"range": [30, 60],  "color": "#3d2200"},
                            {"range": [60, 100], "color": "#3d0000"},
                        ]
                    }
                ))
                gauge.update_layout(
                    template="plotly_dark",
                    height=250,
                    margin=dict(l=20, r=20, t=30, b=10)
                )
                st.plotly_chart(gauge, use_container_width='stretch')

        except Exception as e:
            st.warning(f"Could not compute spoilage probability: {e}")

        st.markdown("---")

        # ── REROUTE SUGGESTION ────────────
        if str(row["risk_level"]).lower() == "high":
            st.markdown("### Reroute Recommendation")
            st.error(f"This shipment is HIGH RISK. Consider the following alternative route:")
            st.info(f"Suggested route: {row['alt_route']}")
# ─────────────────────────────────────────
# PAGE: ANALYTICS
# ─────────────────────────────────────────
elif page == "Analytics":

    st.markdown("## Analytics Dashboard")
    st.markdown("Historical performance analysis across carriers, routes, and product types.")

    # ── SPOILAGE BY PRODUCT TYPE ──────────
    st.markdown("### Spoilage Rate by Product Type")

    product_stats = run_query("""
        SELECT
            product_type,
            COUNT(*)                                        AS total_shipments,
            SUM(spoilage_occurred)                          AS total_spoiled,
            ROUND(AVG(spoilage_occurred) * 100, 1)          AS spoilage_rate_pct,
            ROUND(AVG(delay_hours), 1)                      AS avg_delay_hrs,
            ROUND(AVG(shipment_value_usd), 0)               AS avg_value_usd
        FROM shipments
        GROUP BY product_type
        ORDER BY spoilage_rate_pct DESC
    """)

    col1, col2 = st.columns(2)

    with col1:
        fig_prod = px.bar(
            product_stats,
            x="product_type",
            y="spoilage_rate_pct",
            color="spoilage_rate_pct",
            color_continuous_scale="Reds",
            labels={"product_type": "Product Type", "spoilage_rate_pct": "Spoilage Rate (%)"},
            title="Spoilage Rate by Product Type"
        )
        fig_prod.update_layout(template="plotly_dark", height=350,
                               margin=dict(l=20, r=20, t=40, b=20),
                               coloraxis_showscale=False)
        st.plotly_chart(fig_prod, use_container_width='stretch')

    with col2:
        fig_vol = px.pie(
            product_stats,
            names="product_type",
            values="total_shipments",
            title="Shipment Volume by Product Type",
            hole=0.4
        )
        fig_vol.update_layout(template="plotly_dark", height=350,
                              margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_vol, use_container_width='stretch')

    st.dataframe(product_stats, use_container_width='stretch')

    st.markdown("---")

    # ── CARRIER PERFORMANCE ───────────────
    st.markdown("### Carrier Performance")

    carrier_stats = run_query("""
        SELECT
            c.carrier_name,
            COUNT(*)                                        AS total_shipments,
            SUM(s.spoilage_occurred)                        AS total_spoiled,
            ROUND(AVG(s.spoilage_occurred) * 100, 1)        AS spoilage_rate_pct,
            ROUND(AVG(s.delay_hours), 1)                    AS avg_delay_hrs,
            ROUND(c.reliability_score, 1)                   AS reliability_score,
            ROUND(c.on_time_rate * 100, 1)                  AS on_time_pct
        FROM shipments s
        LEFT JOIN carriers c ON s.carrier_id = c.carrier_id
        GROUP BY c.carrier_name
        ORDER BY spoilage_rate_pct DESC
    """)

    fig_carrier = px.scatter(
        carrier_stats,
        x="on_time_pct",
        y="spoilage_rate_pct",
        size="total_shipments",
        color="reliability_score",
        color_continuous_scale="RdYlGn",
        hover_name="carrier_name",
        labels={
            "on_time_pct":       "On-Time Rate (%)",
            "spoilage_rate_pct": "Spoilage Rate (%)",
            "reliability_score": "Reliability Score"
        },
        title="Carrier Performance — On-Time Rate vs Spoilage Rate (bubble size = shipment volume)"
    )
    fig_carrier.update_layout(template="plotly_dark", height=400,
                              margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_carrier, use_container_width='stretch')

    st.dataframe(carrier_stats, use_container_width='stretch')

    st.markdown("---")

    # ── ROUTE RISK HEATMAP ────────────────
    st.markdown("### Route Risk Analysis")

    route_stats = run_query("""
        SELECT
            origin_city || ' to ' || destination_city       AS route,
            COUNT(*)                                        AS total_shipments,
            SUM(spoilage_occurred)                          AS total_spoiled,
            ROUND(AVG(spoilage_occurred) * 100, 1)          AS spoilage_rate_pct,
            ROUND(AVG(delay_hours), 1)                      AS avg_delay_hrs,
            weather_risk
        FROM shipments
        GROUP BY origin_city, destination_city
        ORDER BY spoilage_rate_pct DESC
    """)

    fig_route = px.bar(
        route_stats,
        x="spoilage_rate_pct",
        y="route",
        orientation="h",
        color="weather_risk",
        color_discrete_map={"high": "#ff4b4b", "medium": "#ffa500", "low": "#00cc66"},
        labels={"spoilage_rate_pct": "Spoilage Rate (%)", "route": "Route"},
        title="Spoilage Rate by Route (colored by weather risk)"
    )
    fig_route.update_layout(template="plotly_dark", height=400,
                            margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_route, use_container_width='stretch')

    st.markdown("---")

    # ── MONTHLY TREND ─────────────────────
    st.markdown("### Monthly Spoilage Trend")

    monthly = run_query("""
        SELECT
            SUBSTR(departure_time, 1, 7)                    AS month,
            COUNT(*)                                        AS total_shipments,
            SUM(spoilage_occurred)                          AS total_spoiled,
            ROUND(AVG(spoilage_occurred) * 100, 1)          AS spoilage_rate_pct
        FROM shipments
        GROUP BY month
        ORDER BY month ASC
    """)

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=monthly["month"],
        y=monthly["spoilage_rate_pct"],
        mode="lines+markers",
        name="Spoilage Rate (%)",
        line=dict(color="#ff4b4b", width=2),
        marker=dict(size=6)
    ))
    fig_trend.add_trace(go.Bar(
        x=monthly["month"],
        y=monthly["total_shipments"],
        name="Total Shipments",
        marker_color="rgba(0,150,255,0.3)",
        yaxis="y2"
    ))
    fig_trend.update_layout(
        template="plotly_dark",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(title="Spoilage Rate (%)"),
        yaxis2=dict(title="Total Shipments", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig_trend, use_container_width='stretch')
# ─────────────────────────────────────────
# PAGE: AI ANALYST
# ─────────────────────────────────────────
elif page == "AI Analyst":

    st.markdown("## AI Analyst")
    st.markdown("Ask questions about your cold chain data in plain English. The AI retrieves real data from the database and generates grounded answers.")

    # Load OpenAI API key — from Streamlit secrets (cloud) or .env (local)
    openai_api_key = None
    try:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    if not openai_api_key:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        st.error("OpenAI API key not found. Please add OPENAI_API_KEY to your .env file.")
        st.stop()

    client = openai.OpenAI(api_key=openai_api_key)

    # ── DATABASE SCHEMA CONTEXT ───────────
    DB_SCHEMA = """
    You have access to a SQLite cold chain logistics database with these tables:

    TABLE shipments:
        shipment_id TEXT, product_type TEXT, product_count INTEGER,
        shipment_size_kg REAL, shipment_value_usd REAL,
        safe_temp_min REAL, safe_temp_max REAL,
        origin_city TEXT, destination_city TEXT, route_distance_km REAL,
        carrier_id TEXT, vehicle_type TEXT, vehicle_number TEXT,
        departure_time TEXT, expected_arrival TEXT, actual_arrival TEXT,
        delay_hours REAL, spoilage_occurred INTEGER, weather_risk TEXT,
        origin_lat REAL, origin_lon REAL, dest_lat REAL, dest_lon REAL,
        alt_route TEXT

    TABLE sensor_readings:
        reading_id TEXT, shipment_id TEXT, timestamp TEXT,
        temp_inside_celsius REAL, temp_outside_celsius REAL,
        humidity_percent REAL, refrigerator_status TEXT,
        door_open_event INTEGER, vehicle_speed_kmh REAL,
        gps_latitude REAL, gps_longitude REAL,
        weather_condition TEXT, delay_hours_so_far REAL

    TABLE carriers:
        carrier_id TEXT, carrier_name TEXT, total_shipments INTEGER,
        spoilage_count INTEGER, on_time_rate REAL,
        avg_temp_deviation REAL, reliability_score REAL

    TABLE alerts:
        alert_id TEXT, shipment_id TEXT, timestamp TEXT,
        alert_type TEXT, severity TEXT, message TEXT, resolved INTEGER

    TABLE risk_scores:
        score_id TEXT, shipment_id TEXT, reading_id TEXT,
        timestamp TEXT, risk_score REAL, risk_category TEXT

    IMPORTANT JOIN RULES:
    - shipments does NOT have carrier_name; JOIN carriers ON s.carrier_id = c.carrier_id to get c.carrier_name
    - carriers does NOT have spoilage_rate; use spoilage_count or compute rate as ROUND(spoilage_count*100.0/total_shipments,1)
    - Always alias tables: shipments as s, carriers as c, sensor_readings as sr

    Rules:
    - Always write valid SQLite SQL
    - Use ROUND() for decimal values
    - Use LIMIT 20 unless the user asks for more
    - Return only the SQL query, nothing else
    """

    # ── SUGGESTED QUESTIONS ───────────────
    st.markdown("### Suggested Questions")
    suggestions = [
        "Which carrier has the highest spoilage rate?",
        "Show me all high risk vaccine shipments",
        "What is the average delay by product type?",
        "Which route has the most spoiled shipments?",
        "Show me the top 10 most delayed shipments",
        "Which shipments had refrigeration failures?"
    ]

    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i % 3].button(suggestion, key=f"sugg_{i}"):
            st.session_state["analyst_question"] = suggestion

    st.markdown("---")

    # ── CHAT INPUT ────────────────────────
    if "analyst_history" not in st.session_state:
        st.session_state["analyst_history"] = []

    question = st.text_input(
        "Ask a question about your cold chain data",
        value=st.session_state.get("analyst_question", ""),
        placeholder="e.g. Which carrier has the worst spoilage rate this month?"
    )

    if st.button("Ask") and question.strip():
        st.session_state["analyst_question"] = ""

        with st.spinner("Retrieving data and generating answer..."):
            try:
                # Step 1: Convert question to SQL using LLM (Text-to-SQL)
                sql_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"You are a SQL expert. Convert the user's question to a SQLite query using this schema:\n{DB_SCHEMA}"},
                        {"role": "user",   "content": question}
                    ],
                    temperature=0
                )

                sql_query = sql_response.choices[0].message.content.strip()
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

                # Step 2: Execute SQL against real database (RAG — Retrieval)
                conn_ai = sqlite3.connect(DB_PATH)
                try:
                    result_df = pd.read_sql_query(sql_query, conn_ai)
                    conn_ai.close()
                    data_context = result_df.to_string(index=False) if len(result_df) > 0 else "No results found."
                except Exception as sql_err:
                    conn_ai.close()
                    data_context = f"SQL error: {sql_err}"
                    result_df    = pd.DataFrame()

                # Step 3: Generate natural language answer using retrieved data (Augmented Generation)
                answer_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a cold chain logistics analyst. Answer the user's question based on the data retrieved from the database. Be concise, specific, and actionable. Reference actual numbers from the data."},
                        {"role": "user",   "content": f"Question: {question}\n\nData retrieved from database:\n{data_context}"}
                    ],
                    temperature=0.3
                )

                answer = answer_response.choices[0].message.content.strip()

                # Store in history
                st.session_state["analyst_history"].append({
                    "question":   question,
                    "sql":        sql_query,
                    "answer":     answer,
                    "data":       result_df
                })

            except Exception as e:
                st.error(f"Error: {e}")

    # ── DISPLAY HISTORY ───────────────────
    for item in reversed(st.session_state["analyst_history"]):
        st.markdown(f"**Question:** {item['question']}")
        st.markdown(f"**Answer:** {item['answer']}")

        with st.expander("View SQL query and raw data"):
            st.code(item["sql"], language="sql")
            if len(item["data"]) > 0:
                st.dataframe(item["data"], use_container_width='stretch')

        st.markdown("---")
# ─────────────────────────────────────────
# PAGE: MODEL PERFORMANCE
# ─────────────────────────────────────────
elif page == "Model Performance":

    st.markdown("## Model Performance")
    st.markdown("Comparison of all machine learning models trained on the cold chain dataset.")

    # ── MODEL COMPARISON TABLE ────────────
    st.markdown("### Model Comparison")

    try:
        import matplotlib  # type: ignore
        styled_results = model_results.style.background_gradient(
            subset=["Accuracy", "F1-Score", "AUC-ROC"],
            cmap="Greens"
        ).format({
            "Accuracy":  "{:.4f}",
            "F1-Score":  "{:.4f}",
            "AUC-ROC":   "{:.4f}",
        })
    except Exception:
        # matplotlib isn't available in the runtime (Streamlit Cloud minimal env).
        # Fall back to simple Styler formatting without background gradient.
        styled_results = model_results.style.format({
            "Accuracy":  "{:.4f}",
            "F1-Score":  "{:.4f}",
            "AUC-ROC":   "{:.4f}",
        })

    st.dataframe(styled_results, use_container_width='stretch')

    st.markdown("---")

    # ── MODEL COMPARISON CHART ────────────
    st.markdown("### Visual Comparison")

    fig_models = go.Figure()

    metrics = ["Accuracy", "F1-Score", "AUC-ROC"]
    colors  = ["#00aaff", "#00cc66", "#ffa500"]

    for metric, color in zip(metrics, colors):
        fig_models.add_trace(go.Bar(
            name=metric,
            x=model_results["Model"],
            y=model_results[metric],
            marker_color=color,
            opacity=0.85
        ))

    fig_models.update_layout(
        template="plotly_dark",
        barmode="group",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(range=[0.7, 1.0], title="Score"),
        xaxis_title="Model",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        title="Model Performance Comparison — Accuracy, F1-Score, AUC-ROC"
    )

    st.plotly_chart(fig_models, use_container_width='stretch')

    st.markdown("---")

    # ── FEATURE IMPORTANCE ────────────────
    st.markdown("### Feature Importance (Best Model)")

    try:
        importance_vals = risk_model.feature_importances_
        importance_df   = pd.DataFrame({
            "Feature":    feature_list,
            "Importance": importance_vals
        }).sort_values("Importance", ascending=True).tail(15)

        fig_imp = px.bar(
            importance_df,
            x="Importance",
            y="Feature",
            orientation="h",
            color="Importance",
            color_continuous_scale="Blues",
            title="Top 15 Most Important Features for Risk Prediction"
        )
        fig_imp.update_layout(
            template="plotly_dark",
            height=450,
            margin=dict(l=20, r=20, t=40, b=20),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_imp, use_container_width='stretch')

    except AttributeError:
        st.info("Feature importance is not available for this model type.")

    st.markdown("---")

    # ── DATASET SUMMARY ───────────────────
    st.markdown("### Dataset Summary")

    dataset_stats = run_query("""
        SELECT
            (SELECT COUNT(*) FROM shipments)        AS total_shipments,
            (SELECT COUNT(*) FROM sensor_readings)  AS total_sensor_readings,
            (SELECT COUNT(*) FROM alerts)           AS total_alerts,
            (SELECT COUNT(*) FROM carriers)         AS total_carriers,
            (SELECT ROUND(AVG(spoilage_occurred)*100,1) FROM shipments) AS overall_spoilage_rate_pct,
            (SELECT ROUND(AVG(delay_hours),1) FROM shipments)           AS avg_delay_hours
    """)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Shipments",      f"{int(dataset_stats['total_shipments'][0]):,}")
    c2.metric("Sensor Readings",      f"{int(dataset_stats['total_sensor_readings'][0]):,}")
    c3.metric("Total Alerts",         f"{int(dataset_stats['total_alerts'][0]):,}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Carriers",             f"{int(dataset_stats['total_carriers'][0]):,}")
    c5.metric("Overall Spoilage Rate",f"{dataset_stats['overall_spoilage_rate_pct'][0]}%")
    c6.metric("Avg Delay",            f"{dataset_stats['avg_delay_hours'][0]} hrs")

    st.markdown("---")
    st.markdown("### Model Architecture Notes")
    st.markdown("""
    The risk classification model was trained on aggregated features derived from hourly sensor readings
    joined with shipment metadata. Five algorithms were evaluated using 80/20 train-test split with
    stratified sampling. The best performing model (LightGBM) was selected based on AUC-ROC score
    and saved for production inference.

    The spoilage probability model is an XGBoost Regressor trained on shipment-level aggregated features,
    predicting a continuous probability score between 0 and 1. An Isolation Forest anomaly detector
    runs independently on raw sensor readings to flag sudden temperature excursions outside the
    expected distribution.

    High accuracy scores reflect the deterministic nature of the synthetic dataset. In production
    with real IoT sensor data, expected accuracy would be 85-93% with appropriate retuning.
    """)
