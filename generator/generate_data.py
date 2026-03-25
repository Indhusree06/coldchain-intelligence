import sqlite3
import random
import os
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)  # Makes results reproducible — same data every time you run it

# ─────────────────────────────────────────
# STEP 1: Connect to SQLite Database
# ─────────────────────────────────────────
# This creates the file coldchain.db inside your data/ folder
# If the file already exists, it just connects to it
db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'coldchain.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("✅ Connected to database")

# ─────────────────────────────────────────
# STEP 2: Create Tables
# ─────────────────────────────────────────

# TABLE 1: carriers
cursor.execute("""
CREATE TABLE IF NOT EXISTS carriers (
    carrier_id          TEXT PRIMARY KEY,
    carrier_name        TEXT NOT NULL,
    total_shipments     INTEGER DEFAULT 0,
    spoilage_count      INTEGER DEFAULT 0,
    on_time_rate        REAL DEFAULT 1.0,
    avg_temp_deviation  REAL DEFAULT 0.0,
    reliability_score   REAL DEFAULT 100.0
)
""")

# TABLE 2: shipments (master table)
cursor.execute("""
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id         TEXT PRIMARY KEY,
    product_type        TEXT NOT NULL,
    product_count       INTEGER,
    shipment_size_kg    REAL,
    shipment_value_usd  REAL,
    safe_temp_min       REAL,
    safe_temp_max       REAL,
    origin_city         TEXT,
    destination_city    TEXT,
    route_distance_km   REAL,
    carrier_id          TEXT,
    vehicle_type        TEXT,
    vehicle_number      TEXT,
    driver_id           TEXT,
    departure_time      TEXT,
    expected_arrival    TEXT,
    actual_arrival      TEXT,
    spoilage_occurred   INTEGER DEFAULT 0,
    FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id)
)
""")

# TABLE 3: sensor_readings
cursor.execute("""
CREATE TABLE IF NOT EXISTS sensor_readings (
    reading_id              TEXT PRIMARY KEY,
    shipment_id             TEXT NOT NULL,
    timestamp               TEXT,
    temp_inside_celsius     REAL,
    temp_outside_celsius    REAL,
    humidity_percent        REAL,
    refrigerator_status     TEXT,
    door_open_event         INTEGER DEFAULT 0,
    vehicle_speed_kmh       REAL,
    gps_latitude            REAL,
    gps_longitude           REAL,
    weather_condition       TEXT,
    delay_hours_so_far      REAL DEFAULT 0.0,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
)
""")

# TABLE 4: risk_scores
cursor.execute("""
CREATE TABLE IF NOT EXISTS risk_scores (
    score_id        TEXT PRIMARY KEY,
    shipment_id     TEXT NOT NULL,
    reading_id      TEXT NOT NULL,
    timestamp       TEXT,
    risk_score      REAL,
    risk_category   TEXT,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (reading_id) REFERENCES sensor_readings(reading_id)
)
""")

# TABLE 5: alerts
cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    alert_id        TEXT PRIMARY KEY,
    shipment_id     TEXT NOT NULL,
    timestamp       TEXT,
    alert_type      TEXT,
    severity        TEXT,
    message         TEXT,
    resolved        INTEGER DEFAULT 0,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
)
""")

conn.commit()
print("All 5 tables created successfully")
conn.close()
print("Database connection closed")
print("\n Database saved at: data/coldchain.db")
print("Open DB Browser for SQLite and load this file to see your tables!")
