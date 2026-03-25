import sqlite3
import os
import time
import random
from datetime import datetime

random.seed(None)  # No fixed seed — different each run for true randomness

db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'coldchain.db')

print(" Cold Chain Simulator Starting...")
print("   New sensor readings will be inserted every 3 seconds")
print("   Press Ctrl+C to stop\n")

# Get all reading IDs in order of timestamp
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT reading_id FROM sensor_readings
    ORDER BY timestamp ASC
""")
all_reading_ids = [row[0] for row in cursor.fetchall()]
conn.close()

print(f"  Found {len(all_reading_ids):,} readings to replay")
print(f"   Estimated replay time at 3s/reading: {len(all_reading_ids)*3/3600:.1f} hours")
print(f"   (You can stop and restart anytime — dashboard reads latest data)\n")

# Create a separate table to track "live" readings
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS live_readings (
        reading_id          TEXT PRIMARY KEY,
        shipment_id         TEXT,
        timestamp           TEXT,
        temp_inside_celsius REAL,
        temp_outside_celsius REAL,
        humidity_percent    REAL,
        refrigerator_status TEXT,
        door_open_event     INTEGER,
        vehicle_speed_kmh   REAL,
        gps_latitude        REAL,
        gps_longitude       REAL,
        weather_condition   TEXT,
        delay_hours_so_far  REAL,
        inserted_at         TEXT
    )
""")
conn.commit()

# Clear previous live readings so we start fresh
cursor.execute("DELETE FROM live_readings")
conn.commit()
print(" Live readings table ready (cleared for fresh start)\n")

# ─────────────────────────────────────────
# MAIN SIMULATION LOOP
# ─────────────────────────────────────────
batch_size = 1   # Insert 1 reading at a time for true real-time feel
counter    = 0

try:
    for reading_id in all_reading_ids:

        # Fetch the reading from sensor_readings
        cursor.execute("""
            SELECT reading_id, shipment_id, timestamp, temp_inside_celsius,
                   temp_outside_celsius, humidity_percent, refrigerator_status,
                   door_open_event, vehicle_speed_kmh, gps_latitude, gps_longitude,
                   weather_condition, delay_hours_so_far
            FROM sensor_readings
            WHERE reading_id = ?
        """, (reading_id,))

        row = cursor.fetchone()
        if not row:
            continue

        # Insert into live_readings with current wall-clock time
        cursor.execute("""
            INSERT OR IGNORE INTO live_readings
            (reading_id, shipment_id, timestamp, temp_inside_celsius,
             temp_outside_celsius, humidity_percent, refrigerator_status,
             door_open_event, vehicle_speed_kmh, gps_latitude, gps_longitude,
             weather_condition, delay_hours_so_far, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row + (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

        conn.commit()
        counter += 1

        # Print status every 10 readings
        if counter % 10 == 0:
            cursor.execute("SELECT COUNT(*) FROM live_readings")
            live_count = cursor.fetchone()[0]
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Live readings: {live_count:,} / {len(all_reading_ids):,} "
                  f"({live_count/len(all_reading_ids)*100:.1f}%)")

        time.sleep(3)   # Wait 3 seconds before next reading

except KeyboardInterrupt:
    print(f"\n Simulator stopped. {counter:,} readings inserted into live_readings table.")
finally:
    conn.close()
