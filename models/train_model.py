import sqlite3
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# STEP 1: LOAD DATA FROM SQLITE
# ─────────────────────────────────────────
db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'coldchain.db')
conn = sqlite3.connect(db_path)

print(" Loading data from database...")

# Load sensor readings joined with shipment info
query = """
    SELECT
        sr.reading_id,
        sr.shipment_id,
        sr.temp_inside_celsius,
        sr.temp_outside_celsius,
        sr.humidity_percent,
        sr.refrigerator_status,
        sr.door_open_event,
        sr.vehicle_speed_kmh,
        sr.weather_condition,
        sr.delay_hours_so_far,
        s.safe_temp_min,
        s.safe_temp_max,
        s.product_type,
        s.weather_risk,
        s.vehicle_type,
        s.route_distance_km,
        s.spoilage_occurred,
        c.reliability_score,
        c.on_time_rate,
        c.avg_temp_deviation
    FROM sensor_readings sr
    JOIN shipments s ON sr.shipment_id = s.shipment_id
    JOIN carriers c ON s.carrier_id = c.carrier_id
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f" Loaded {len(df):,} rows with {df.shape[1]} columns")

# ─────────────────────────────────────────
# STEP 2: FEATURE ENGINEERING
# ─────────────────────────────────────────
print(" Engineering features...")

# How far is the current temperature from the safe range?
df["temp_deviation_above"] = (df["temp_inside_celsius"] - df["safe_temp_max"]).clip(lower=0)
df["temp_deviation_below"] = (df["safe_temp_min"] - df["temp_inside_celsius"]).clip(lower=0)
df["temp_deviation_total"] = df["temp_deviation_above"] + df["temp_deviation_below"]

# Is the temperature currently inside the safe range?
df["temp_in_safe_range"] = (
    (df["temp_inside_celsius"] >= df["safe_temp_min"]) &
    (df["temp_inside_celsius"] <= df["safe_temp_max"])
).astype(int)

# Temperature stress — how hot is it outside relative to safe max?
df["outside_temp_stress"] = (df["temp_outside_celsius"] - df["safe_temp_max"]).clip(lower=0)

# Refrigerator failed? Convert to binary
df["fridge_failed"] = (df["refrigerator_status"] == "Failed").astype(int)

# Weather risk to number
weather_risk_map = {"low": 0, "medium": 1, "high": 2}
df["weather_risk_num"] = df["weather_risk"].map(weather_risk_map)

# Encode categorical columns
le_product  = LabelEncoder()
le_vehicle  = LabelEncoder()
le_weather  = LabelEncoder()

df["product_type_enc"]    = le_product.fit_transform(df["product_type"])
df["vehicle_type_enc"]    = le_vehicle.fit_transform(df["vehicle_type"])
df["weather_condition_enc"] = le_weather.fit_transform(df["weather_condition"])

print(" Features engineered")

# ─────────────────────────────────────────
# STEP 3: CREATE RISK LABELS
# ─────────────────────────────────────────
print(" Creating risk labels...")

def assign_risk(row):
    score = 0

    # Temperature deviation — most important factor
    if row["temp_deviation_above"] > 2.0 or row["temp_deviation_below"] > 2.0:
        score += 3
    elif row["temp_deviation_above"] > 0.5 or row["temp_deviation_below"] > 0.5:
        score += 2
    elif row["temp_deviation_total"] > 0:
        score += 1

    # Refrigerator failure
    if row["fridge_failed"] == 1:
        score += 2

    # Door opened
    if row["door_open_event"] == 1:
        score += 1

    # Carrier reliability
    if row["reliability_score"] < 70:
        score += 2
    elif row["reliability_score"] < 85:
        score += 1

    # Weather risk
    score += row["weather_risk_num"]

    # Delay
    if row["delay_hours_so_far"] > 6:
        score += 2
    elif row["delay_hours_so_far"] > 2:
        score += 1

    # Assign label
    if score >= 6:
        return 2   # High
    elif score >= 3:
        return 1   # Medium
    else:
        return 0   # Low

df["risk_label"] = df.apply(assign_risk, axis=1)

# Show distribution
counts = df["risk_label"].value_counts().sort_index()
total  = len(df)
print(f"   Low Risk:    {counts.get(0,0):,} ({counts.get(0,0)/total*100:.1f}%)")
print(f"   Medium Risk: {counts.get(1,0):,} ({counts.get(1,0)/total*100:.1f}%)")
print(f"   High Risk:   {counts.get(2,0):,} ({counts.get(2,0)/total*100:.1f}%)")

# ─────────────────────────────────────────
# STEP 4: PREPARE FEATURES FOR TRAINING
# ─────────────────────────────────────────

FEATURES = [
    "temp_inside_celsius",
    "temp_outside_celsius",
    "humidity_percent",
    "fridge_failed",
    "door_open_event",
    "vehicle_speed_kmh",
    "delay_hours_so_far",
    "temp_deviation_above",
    "temp_deviation_below",
    "temp_deviation_total",
    "temp_in_safe_range",
    "outside_temp_stress",
    "weather_risk_num",
    "reliability_score",
    "on_time_rate",
    "avg_temp_deviation",
    "route_distance_km",
    "product_type_enc",
    "vehicle_type_enc",
    "weather_condition_enc",
]

X = df[FEATURES]
y = df["risk_label"]

# Train/test split — 80% train, 20% test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n Training set: {len(X_train):,} rows")
print(f" Test set:     {len(X_test):,} rows")

# ─────────────────────────────────────────
# STEP 5: TRAIN AND COMPARE MODELS
# ─────────────────────────────────────────
print("\n⏳ Training models...\n")

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Decision Tree":       DecisionTreeClassifier(max_depth=8, random_state=42),
    "Random Forest":       RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    "XGBoost":             XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=6,
                                         random_state=42, eval_metric="mlogloss",
                                         verbosity=0),
    "LightGBM":            LGBMClassifier(n_estimators=200, learning_rate=0.1,
                                          random_state=42, verbose=-1),
}

results = []
trained_models = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    f1  = f1_score(y_test, y_pred, average="weighted")
    auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="weighted")

    results.append({"Model": name, "Accuracy": acc, "F1-Score": f1, "AUC-ROC": auc})
    trained_models[name] = model

    print(f"  {name:<22} → Accuracy: {acc*100:.1f}%  F1: {f1:.3f}  AUC: {auc:.3f}")

# ─────────────────────────────────────────
# STEP 6: PICK BEST MODEL AND SAVE
# ─────────────────────────────────────────
results_df = pd.DataFrame(results).sort_values("AUC-ROC", ascending=False)
best_name  = results_df.iloc[0]["Model"]
best_model = trained_models[best_name]

print(f"\n Best model: {best_name} (AUC: {results_df.iloc[0]['AUC-ROC']:.3f})")

# Save best model
model_path = os.path.join(os.path.dirname(__file__), 'risk_model.pkl')
joblib.dump(best_model, model_path)
print(f"Model saved to models/risk_model.pkl")

# Save feature list so dashboard knows which features to use
feature_path = os.path.join(os.path.dirname(__file__), 'feature_list.pkl')
joblib.dump(FEATURES, feature_path)
print(f" Feature list saved to models/feature_list.pkl")

# Save label encoders for use in dashboard
encoders_path = os.path.join(os.path.dirname(__file__), 'encoders.pkl')
joblib.dump({
    "product":  le_product,
    "vehicle":  le_vehicle,
    "weather":  le_weather
}, encoders_path)
print(f"Encoders saved to models/encoders.pkl")

# Save model comparison results
results_path = os.path.join(os.path.dirname(__file__), 'model_results.pkl')
joblib.dump(results_df, results_path)
print(f" Model comparison results saved")

# Save risk label mapping
joblib.dump({"low": 0, "medium": 1, "high": 2}, 
            os.path.join(os.path.dirname(__file__), 'risk_map.pkl'))

print(f"\n Training complete!")
print(f"\n{'='*50}")
print(f"MODEL COMPARISON SUMMARY")
print(f"{'='*50}")
print(results_df.to_string(index=False))
print(f"{'='*50}")
