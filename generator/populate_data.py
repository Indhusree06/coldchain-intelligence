import sqlite3
import random
import os
import uuid
from datetime import datetime, timedelta

random.seed(42)  # Same seed = same data every time you run it

# ─────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────
db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'coldchain.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
print("Connected to database")

# ─────────────────────────────────────────
# REFERENCE DATA — The "rules" of our world
# ─────────────────────────────────────────

PRODUCT_TYPES = {
    "Vaccine":          {"temp_min": 2.0,   "temp_max": 8.0,   "sensitivity": "very_high", "avg_value": 15000},
    "Seafood":          {"temp_min": 0.0,   "temp_max": 4.0,   "sensitivity": "very_high", "avg_value": 8000},
    "Dairy":            {"temp_min": 1.0,   "temp_max": 6.0,   "sensitivity": "high",      "avg_value": 3000},
    "Fresh Produce":    {"temp_min": 1.0,   "temp_max": 7.0,   "sensitivity": "medium",    "avg_value": 2000},
    "Pharmaceuticals":  {"temp_min": 15.0,  "temp_max": 25.0,  "sensitivity": "high",      "avg_value": 20000},
    "Frozen Food":      {"temp_min": -20.0, "temp_max": -15.0, "sensitivity": "medium",    "avg_value": 4000},
    "Blood Products":   {"temp_min": 1.0,   "temp_max": 6.0,   "sensitivity": "very_high", "avg_value": 25000},
}

ROUTES = [
    {
        "origin": "Chicago, IL",         "origin_lat": 41.8781,  "origin_lon": -87.6298,
        "destination": "Dallas, TX",     "dest_lat": 32.7767,    "dest_lon": -96.7970,
        "distance_km": 1500,             "weather_risk": "medium",
        "alt_route": "Chicago → Indianapolis → Nashville → Dallas"
    },
    {
        "origin": "Miami, FL",           "origin_lat": 25.7617,  "origin_lon": -80.1918,
        "destination": "New York, NY",   "dest_lat": 40.7128,    "dest_lon": -74.0060,
        "distance_km": 2000,             "weather_risk": "high",
        "alt_route": "Miami → Charlotte → Washington DC → New York"
    },
    {
        "origin": "Los Angeles, CA",     "origin_lat": 34.0522,  "origin_lon": -118.2437,
        "destination": "Seattle, WA",    "dest_lat": 47.6062,    "dest_lon": -122.3321,
        "distance_km": 1800,             "weather_risk": "low",
        "alt_route": "Los Angeles → San Francisco → Portland → Seattle"
    },
    {
        "origin": "Houston, TX",         "origin_lat": 29.7604,  "origin_lon": -95.3698,
        "destination": "Chicago, IL",    "dest_lat": 41.8781,    "dest_lon": -87.6298,
        "distance_km": 1700,             "weather_risk": "medium",
        "alt_route": "Houston → Little Rock → St. Louis → Chicago"
    },
    {
        "origin": "Atlanta, GA",         "origin_lat": 33.7490,  "origin_lon": -84.3880,
        "destination": "Boston, MA",     "dest_lat": 42.3601,    "dest_lon": -71.0589,
        "distance_km": 1800,             "weather_risk": "medium",
        "alt_route": "Atlanta → Charlotte → Philadelphia → Boston"
    },
    {
        "origin": "Phoenix, AZ",         "origin_lat": 33.4484,  "origin_lon": -112.0740,
        "destination": "Denver, CO",     "dest_lat": 39.7392,    "dest_lon": -104.9903,
        "distance_km": 1200,             "weather_risk": "high",
        "alt_route": "Phoenix → Flagstaff → Albuquerque → Denver"
    },
    {
        "origin": "New York, NY",        "origin_lat": 40.7128,  "origin_lon": -74.0060,
        "destination": "Los Angeles, CA","dest_lat": 34.0522,    "dest_lon": -118.2437,
        "distance_km": 4500,             "weather_risk": "medium",
        "alt_route": "New York → Pittsburgh → St. Louis → Albuquerque → Los Angeles"
    },
    {
        "origin": "Seattle, WA",         "origin_lat": 47.6062,  "origin_lon": -122.3321,
        "destination": "Miami, FL",      "dest_lat": 25.7617,    "dest_lon": -80.1918,
        "distance_km": 5000,             "weather_risk": "high",
        "alt_route": "Seattle → Portland → Sacramento → Phoenix → Dallas → Miami"
    },
    {
        "origin": "Denver, CO",          "origin_lat": 39.7392,  "origin_lon": -104.9903,
        "destination": "Atlanta, GA",    "dest_lat": 33.7490,    "dest_lon": -84.3880,
        "distance_km": 2200,             "weather_risk": "medium",
        "alt_route": "Denver → Kansas City → Memphis → Atlanta"
    },
    {
        "origin": "Boston, MA",          "origin_lat": 42.3601,  "origin_lon": -71.0589,
        "destination": "Houston, TX",    "dest_lat": 29.7604,    "dest_lon": -95.3698,
        "distance_km": 2800,             "weather_risk": "low",
        "alt_route": "Boston → New York → Philadelphia → Charlotte → Atlanta → Houston"
    },
]

VEHICLE_TYPES = {
    "Refrigerated Truck": {"reliability": 0.90},
    "Air Freight":        {"reliability": 0.97},
    "Rail Freight":       {"reliability": 0.85},
    "Refrigerated Van":   {"reliability": 0.88},
}

WEATHER_CONDITIONS = ["Clear", "Cloudy", "Rain", "Extreme Heat", "Snow", "Storm", "Fog"]

print(" Reference data loaded")

# ─────────────────────────────────────────
# SECTION 2: GENERATE CARRIERS
# ─────────────────────────────────────────

CARRIER_NAMES = [
    "FrostLine Logistics",     "Arctic Express",          "CoolChain Transport",
    "PolarFreight Inc",        "ChillRoute Carriers",     "IceWay Logistics",
    "SubZero Shipping",        "ThermoGuard Freight",     "ColdPath Solutions",
    "GlacierMove Transport",   "SnowCap Logistics",       "FreezeFleet Inc",
    "CryoShip Carriers",       "NorthChill Express",      "BlueFrost Freight",
    "ArcticFlow Transport",    "ColdLink Logistics",      "FrostBridge Inc",
    "IcePeak Carriers",        "TundraFreight Solutions", "CoolWave Logistics",
    "PolarPath Express",       "ChillStream Transport",   "FrostGuard Freight",
    "ColdEdge Logistics"
]

carriers = []

for i, name in enumerate(CARRIER_NAMES):
    carrier_id = f"CARR-{str(i+1).zfill(3)}"

    reliability_tier = random.choice(["high", "medium", "low"])

    if reliability_tier == "high":
        on_time_rate       = round(random.uniform(0.90, 0.98), 2)
        spoilage_rate      = round(random.uniform(0.02, 0.08), 2)
        avg_temp_deviation = round(random.uniform(0.1, 0.8), 2)
    elif reliability_tier == "medium":
        on_time_rate       = round(random.uniform(0.75, 0.89), 2)
        spoilage_rate      = round(random.uniform(0.09, 0.18), 2)
        avg_temp_deviation = round(random.uniform(0.9, 1.8), 2)
    else:
        on_time_rate       = round(random.uniform(0.55, 0.74), 2)
        spoilage_rate      = round(random.uniform(0.19, 0.35), 2)
        avg_temp_deviation = round(random.uniform(1.9, 3.5), 2)

    total_shipments   = random.randint(200, 1500)
    spoilage_count    = int(total_shipments * spoilage_rate)
    reliability_score = round((on_time_rate * 0.6 + (1 - spoilage_rate) * 0.4) * 100, 1)

    carriers.append({
        "carrier_id":          carrier_id,
        "carrier_name":        name,
        "total_shipments":     total_shipments,
        "spoilage_count":      spoilage_count,
        "on_time_rate":        on_time_rate,
        "avg_temp_deviation":  avg_temp_deviation,
        "reliability_score":   reliability_score
    })

cursor.executemany("""
    INSERT OR IGNORE INTO carriers
    (carrier_id, carrier_name, total_shipments, spoilage_count,
     on_time_rate, avg_temp_deviation, reliability_score)
    VALUES
    (:carrier_id, :carrier_name, :total_shipments, :spoilage_count,
     :on_time_rate, :avg_temp_deviation, :reliability_score)
""", carriers)

conn.commit()
print(f" {len(carriers)} carriers inserted")

# ─────────────────────────────────────────
# SECTION 3: GENERATE SHIPMENTS
# ─────────────────────────────────────────

NUM_SHIPMENTS = 5000
shipments = []
base_date = datetime(2024, 1, 1)

for i in range(NUM_SHIPMENTS):
    shipment_id  = f"SHP-{str(i+1).zfill(5)}"
    product_type = random.choice(list(PRODUCT_TYPES.keys()))
    product_info = PRODUCT_TYPES[product_type]
    route        = random.choice(ROUTES)
    carrier      = random.choice(carriers)
    vehicle_type = random.choice(list(VEHICLE_TYPES.keys()))

    product_count      = random.randint(50, 1000)
    shipment_size_kg   = round(random.uniform(50, 2000), 1)
    shipment_value_usd = round(product_info["avg_value"] * random.uniform(0.7, 1.3), 2)

    days_offset    = random.randint(0, 364)
    hours_offset   = random.randint(0, 23)
    departure_time = base_date + timedelta(days=days_offset, hours=hours_offset)

    base_hours       = route["distance_km"] / 80
    expected_arrival = departure_time + timedelta(hours=base_hours)

    delay_chance = 0.2
    if route["weather_risk"] == "high":
        delay_chance += 0.15
    if carrier["reliability_score"] < 70:
        delay_chance += 0.20
    elif carrier["reliability_score"] < 85:
        delay_chance += 0.10

    delay_hours = 0
    if random.random() < delay_chance:
        delay_hours = round(random.uniform(1, 12), 1)

    actual_arrival = expected_arrival + timedelta(hours=delay_hours)
    driver_id      = f"DRV-{random.randint(100, 999)}"
    vehicle_number = f"VH-{random.randint(1000, 9999)}"

    shipments.append({
        "shipment_id":        shipment_id,
        "product_type":       product_type,
        "product_count":      product_count,
        "shipment_size_kg":   shipment_size_kg,
        "shipment_value_usd": shipment_value_usd,
        "safe_temp_min":      product_info["temp_min"],
        "safe_temp_max":      product_info["temp_max"],
        "origin_city":        route["origin"],
        "origin_lat":         route["origin_lat"],
        "origin_lon":         route["origin_lon"],
        "destination_city":   route["destination"],
        "dest_lat":           route["dest_lat"],
        "dest_lon":           route["dest_lon"],
        "route_distance_km":  route["distance_km"],
        "weather_risk":       route["weather_risk"],
        "alt_route":          route["alt_route"],
        "carrier_id":         carrier["carrier_id"],
        "vehicle_type":       vehicle_type,
        "vehicle_number":     vehicle_number,
        "driver_id":          driver_id,
        "departure_time":     departure_time.strftime("%Y-%m-%d %H:%M:%S"),
        "expected_arrival":   expected_arrival.strftime("%Y-%m-%d %H:%M:%S"),
        "actual_arrival":     actual_arrival.strftime("%Y-%m-%d %H:%M:%S"),
        "delay_hours":        delay_hours,
        "spoilage_occurred":  0
    })

    if (i + 1) % 500 == 0:
        print(f"   → {i+1} shipments prepared...")

print(f" {NUM_SHIPMENTS} shipments prepared")

# Add extra columns to shipments table if they don't exist yet
extra_columns = [
    ("origin_lat",   "REAL"),
    ("origin_lon",   "REAL"),
    ("dest_lat",     "REAL"),
    ("dest_lon",     "REAL"),
    ("weather_risk", "TEXT"),
    ("alt_route",    "TEXT"),
    ("delay_hours",  "REAL DEFAULT 0"),
]
for col_name, col_type in extra_columns:
    try:
        cursor.execute(f"ALTER TABLE shipments ADD COLUMN {col_name} {col_type}")
    except:
        pass

conn.commit()
print(" Shipments table columns verified")

cursor.executemany("""
    INSERT OR IGNORE INTO shipments
    (shipment_id, product_type, product_count, shipment_size_kg, shipment_value_usd,
     safe_temp_min, safe_temp_max, origin_city, origin_lat, origin_lon,
     destination_city, dest_lat, dest_lon, route_distance_km, weather_risk, alt_route,
     carrier_id, vehicle_type, vehicle_number, driver_id,
     departure_time, expected_arrival, actual_arrival, delay_hours, spoilage_occurred)
    VALUES
    (:shipment_id, :product_type, :product_count, :shipment_size_kg, :shipment_value_usd,
     :safe_temp_min, :safe_temp_max, :origin_city, :origin_lat, :origin_lon,
     :destination_city, :dest_lat, :dest_lon, :route_distance_km, :weather_risk, :alt_route,
     :carrier_id, :vehicle_type, :vehicle_number, :driver_id,
     :departure_time, :expected_arrival, :actual_arrival, :delay_hours, :spoilage_occurred)
""", shipments)

conn.commit()
print(f" {NUM_SHIPMENTS} shipments inserted into database")

# ─────────────────────────────────────────
# SECTION 4: GENERATE SENSOR READINGS
# ─────────────────────────────────────────

print("⏳ Generating sensor readings (this may take 1-2 minutes)...")

all_readings    = []
all_alerts      = []
reading_counter = 0
alert_counter   = 0

for shipment in shipments:

    s_id         = shipment["shipment_id"]
    safe_min     = shipment["safe_temp_min"]
    safe_max     = shipment["safe_temp_max"]
    weather_risk = shipment["weather_risk"]
    vehicle_type = shipment["vehicle_type"]
    carrier      = next(c for c in carriers if c["carrier_id"] == shipment["carrier_id"])
    departure    = datetime.strptime(shipment["departure_time"], "%Y-%m-%d %H:%M:%S")
    arrival      = datetime.strptime(shipment["actual_arrival"],  "%Y-%m-%d %H:%M:%S")

    transit_hours = max(1, int((arrival - departure).total_seconds() / 3600))
    transit_hours = min(transit_hours, 120)

    lat      = shipment["origin_lat"]
    lon      = shipment["origin_lon"]
    lat_step = (shipment["dest_lat"] - shipment["origin_lat"]) / transit_hours
    lon_step = (shipment["dest_lon"] - shipment["origin_lon"]) / transit_hours

    hours_above_safe   = 0
    hours_below_safe   = 0
    spoilage_triggered = False

    safe_midpoint = (safe_min + safe_max) / 2
    inside_temp   = round(safe_midpoint + random.uniform(-0.5, 0.5), 2)

    for hour in range(transit_hours):

        timestamp  = departure + timedelta(hours=hour)
        reading_id = f"RDG-{str(reading_counter).zfill(8)}"
        reading_counter += 1

        month = timestamp.month
        if month in [6, 7, 8]:
            base_outside = random.uniform(25, 38)
        elif month in [12, 1, 2]:
            base_outside = random.uniform(-10, 10)
        else:
            base_outside = random.uniform(10, 25)

        if weather_risk == "high":
            base_outside += random.uniform(3, 10)
        elif weather_risk == "medium":
            base_outside += random.uniform(0, 4)

        outside_temp = round(base_outside, 2)

        if weather_risk == "high":
            weather_condition = random.choices(
                WEATHER_CONDITIONS, weights=[10, 15, 20, 30, 10, 10, 5], k=1)[0]
        elif weather_risk == "medium":
            weather_condition = random.choices(
                WEATHER_CONDITIONS, weights=[25, 25, 20, 10, 10, 5, 5], k=1)[0]
        else:
            weather_condition = random.choices(
                WEATHER_CONDITIONS, weights=[40, 30, 15, 5, 5, 3, 2], k=1)[0]

        if carrier["reliability_score"] < 70:
            fridge_fail_chance = 0.05
        elif carrier["reliability_score"] < 85:
            fridge_fail_chance = 0.02
        else:
            fridge_fail_chance = 0.005

        refrigerator_status = "Failed" if random.random() < fridge_fail_chance else "Running"
        door_open           = 1 if random.random() < 0.08 else 0

        if refrigerator_status == "Failed":
            inside_temp += random.uniform(1.5, 4.0)
        elif door_open:
            inside_temp += random.uniform(0.5, 2.5)
        elif outside_temp > 35:
            inside_temp += random.uniform(-0.2, 0.8)
        else:
            inside_temp += random.uniform(-0.4, 0.4)

        inside_temp = inside_temp * 0.85 + safe_midpoint * 0.15
        inside_temp = round(inside_temp, 2)

        if inside_temp > safe_max:
            hours_above_safe += 1
        elif inside_temp < safe_min:
            hours_below_safe += 1

        humidity     = round(random.uniform(40, 90), 1)
        speed        = 0.0 if random.random() < 0.10 else round(random.uniform(60, 110), 1)
        delay_so_far = max(0, round(shipment["delay_hours"] * (hour / max(transit_hours, 1)), 1))

        lat = round(lat + lat_step + random.uniform(-0.05, 0.05), 4)
        lon = round(lon + lon_step + random.uniform(-0.05, 0.05), 4)

        all_readings.append({
            "reading_id":           reading_id,
            "shipment_id":          s_id,
            "timestamp":            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "temp_inside_celsius":  inside_temp,
            "temp_outside_celsius": outside_temp,
            "humidity_percent":     humidity,
            "refrigerator_status":  refrigerator_status,
            "door_open_event":      door_open,
            "vehicle_speed_kmh":    speed,
            "gps_latitude":         lat,
            "gps_longitude":        lon,
            "weather_condition":    weather_condition,
            "delay_hours_so_far":   delay_so_far
        })

        if inside_temp > safe_max + 1.0:
            alert_id = f"ALT-{str(alert_counter).zfill(6)}"
            alert_counter += 1
            all_alerts.append({
                "alert_id":    alert_id,
                "shipment_id": s_id,
                "timestamp":   timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "alert_type":  "Temperature Breach",
                "severity":    "Critical" if inside_temp > safe_max + 2.0 else "Warning",
                "message":     f"Temp {inside_temp}°C exceeded safe max {safe_max}°C",
                "resolved":    0
            })

    # Determine spoilage outcome
    product_info = PRODUCT_TYPES[shipment["product_type"]]
    if product_info["sensitivity"] == "very_high" and hours_above_safe >= 2:
        spoilage_triggered = True
    elif product_info["sensitivity"] == "high" and hours_above_safe >= 4:
        spoilage_triggered = True
    elif product_info["sensitivity"] == "medium" and hours_above_safe >= 6:
        spoilage_triggered = True

    if spoilage_triggered:
        shipment["spoilage_occurred"] = 1

# Batch insert sensor readings
BATCH_SIZE = 10000
for i in range(0, len(all_readings), BATCH_SIZE):
    batch = all_readings[i:i + BATCH_SIZE]
    cursor.executemany("""
        INSERT OR IGNORE INTO sensor_readings
        (reading_id, shipment_id, timestamp, temp_inside_celsius, temp_outside_celsius,
         humidity_percent, refrigerator_status, door_open_event, vehicle_speed_kmh,
         gps_latitude, gps_longitude, weather_condition, delay_hours_so_far)
        VALUES
        (:reading_id, :shipment_id, :timestamp, :temp_inside_celsius, :temp_outside_celsius,
         :humidity_percent, :refrigerator_status, :door_open_event, :vehicle_speed_kmh,
         :gps_latitude, :gps_longitude, :weather_condition, :delay_hours_so_far)
    """, batch)
    conn.commit()
    print(f"   → {min(i+BATCH_SIZE, len(all_readings)):,} / {len(all_readings):,} readings inserted...")

print(f" {len(all_readings):,} sensor readings inserted")

# Insert alerts
cursor.executemany("""
    INSERT OR IGNORE INTO alerts
    (alert_id, shipment_id, timestamp, alert_type, severity, message, resolved)
    VALUES
    (:alert_id, :shipment_id, :timestamp, :alert_type, :severity, :message, :resolved)
""", all_alerts)
conn.commit()
print(f" {len(all_alerts):,} alerts inserted")

# Update spoilage outcomes in shipments table
spoiled = [(s["spoilage_occurred"], s["shipment_id"]) for s in shipments]
cursor.executemany(
    "UPDATE shipments SET spoilage_occurred = ? WHERE shipment_id = ?", spoiled)
conn.commit()
print("Spoilage outcomes updated in shipments table")

# ─────────────────────────────────────────
# DONE
# ─────────────────────────────────────────
conn.close()

spoiled_count = sum(1 for s in shipments if s["spoilage_occurred"] == 1)
print(f"\n Data generation complete!")
print(f"   Shipments:       {NUM_SHIPMENTS:,}")
print(f"   Sensor readings: {len(all_readings):,}")
print(f"   Alerts:          {len(all_alerts):,}")
print(f"   Spoiled:         {spoiled_count:,} ({round(spoiled_count/NUM_SHIPMENTS*100,1)}%)")
