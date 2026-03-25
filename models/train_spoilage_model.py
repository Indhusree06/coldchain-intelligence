import sqlite3
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import warnings
warnings.filterwarnings("ignore")

db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'coldchain.db')
conn = sqlite3.connect(db_path)

print(" Loading data...")

query = """
    SELECT
        s.shipment_id,
        s.spoilage_occurred,
        s.safe_temp_min,
        s.safe_temp_max,
        s.weather_risk,
        s.route_distance_km,
        s.delay_hours,
        s.vehicle_type,
        s.product_type,
        c.reliability_score,
        c.on_time_rate,
        c.avg_temp_deviation,
        AVG(sr.temp_inside_celsius)                         AS avg_temp_inside,
        MAX(sr.temp_inside_celsius)                         AS max_temp_inside,
        MIN(sr.temp_inside_celsius)                         AS min_temp_inside,
        AVG(sr.temp_outside_celsius)                        AS avg_temp_outside,
        AVG(sr.humidity_percent)                            AS avg_humidity,
        SUM(sr.door_open_event)                             AS total_door_opens,
        SUM(CASE WHEN sr.refrigerator_status='Failed' THEN 1 ELSE 0 END) AS fridge_failures,
        COUNT(sr.reading_id)                                AS total_readings,
        SUM(CASE WHEN sr.temp_inside_celsius > s.safe_temp_max THEN 1 ELSE 0 END) AS hours_above_safe,
        SUM(CASE WHEN sr.temp_inside_celsius < s.safe_temp_min THEN 1 ELSE 0 END) AS hours_below_safe
    FROM shipments s
    JOIN sensor_readings sr ON s.shipment_id = sr.shipment_id
    JOIN carriers c ON s.carrier_id = c.carrier_id
    GROUP BY s.shipment_id
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f" Loaded {len(df):,} shipments")

# Feature engineering
df["temp_breach_rate"]   = df["hours_above_safe"] / df["total_readings"].clip(lower=1)
df["fridge_fail_rate"]   = df["fridge_failures"]  / df["total_readings"].clip(lower=1)
df["temp_range_stress"]  = df["max_temp_inside"]   - df["safe_temp_max"]
df["weather_risk_num"]   = df["weather_risk"].map({"low": 0, "medium": 1, "high": 2})

from sklearn.preprocessing import LabelEncoder
le_p = LabelEncoder()
le_v = LabelEncoder()
df["product_enc"] = le_p.fit_transform(df["product_type"])
df["vehicle_enc"] = le_v.fit_transform(df["vehicle_type"])

FEATURES = [
    "avg_temp_inside", "max_temp_inside", "min_temp_inside",
    "avg_temp_outside", "avg_humidity",
    "total_door_opens", "fridge_failures", "fridge_fail_rate",
    "hours_above_safe", "hours_below_safe", "temp_breach_rate",
    "temp_range_stress", "delay_hours", "route_distance_km",
    "weather_risk_num", "reliability_score", "on_time_rate",
    "avg_temp_deviation", "product_enc", "vehicle_enc"
]

X = df[FEATURES]
y = df["spoilage_occurred"].astype(float)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42)

model = XGBRegressor(n_estimators=200, learning_rate=0.1,
                     max_depth=6, random_state=42, verbosity=0)
model.fit(X_train, y_train)

y_pred = model.predict(X_test).clip(0, 1)
mae    = mean_absolute_error(y_test, y_pred)
r2     = r2_score(y_test, y_pred)

print(f"Spoilage model trained")
print(f"   MAE: {mae:.4f}  |  R²: {r2:.4f}")

# Save model
joblib.dump(model,    os.path.join(os.path.dirname(__file__), 'spoilage_model.pkl'))
joblib.dump(FEATURES, os.path.join(os.path.dirname(__file__), 'spoilage_features.pkl'))
print(" Spoilage model saved to models/spoilage_model.pkl")
print(" Done!")
