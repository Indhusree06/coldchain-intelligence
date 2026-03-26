# Cold Chain Intelligence System

> An AI-powered logistics intelligence platform for real-time cold chain risk prediction, spoilage detection, and natural language analytics.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.41-red.svg)](https://streamlit.io/)

---

## Overview

Cold Chain Intelligence is an end-to-end machine learning system that monitors temperature-sensitive shipments - vaccines, pharmaceuticals, seafood, dairy, and frozen goods - across logistics networks. It combines real-time sensor data, predictive ML models, and a RAG-based AI analyst to help logistics teams proactively prevent spoilage and reduce losses.

---

## Features

### Live Shipment Monitor
- Interactive map showing all active shipments color-coded by risk level (red = high, orange = medium, green = low)
- Real-time temperature, humidity, and refrigeration status per shipment
- Automatic reroute suggestions for high-risk shipments
- Filterable by product type and risk level

### Shipment Detail View
- Per-shipment deep dive with full sensor timeline
- Temperature trend chart with safe zone visualization
- ML-powered spoilage probability gauge (XGBoost Regressor)
- Risk classification with confidence score

### Analytics Dashboard
- Spoilage rate by product type (bar + pie charts)
- Carrier performance scatter plot — on-time rate vs spoilage rate
- Route risk heatmap with weather risk overlay
- Monthly spoilage trend with shipment volume

### AI Analyst (RAG System)
- Natural language query interface — ask questions in plain English
- Text-to-SQL pipeline: GPT-4o-mini generates SQL → executed against live database → LLM generates grounded answer
- Suggested questions for quick exploration
- Full SQL query and raw data visible in expandable panel

### Model Performance
- Comparison table of 5 trained classifiers with color-coded metrics
- Visual bar chart comparing Accuracy, F1-Score, and AUC-ROC
- Feature importance chart for the best model

---

## Machine Learning Models

| Model | Accuracy | F1-Score | AUC-ROC | Role |
|---|---|---|---|---|
| **LightGBM** | 0.9998 | 0.9998 | 1.0000 | Risk Classifier (Production) |
| XGBoost | 0.9998 | 0.9998 | 1.0000 | Spoilage Probability Regressor |
| Random Forest | 0.9986 | 0.9985 | 1.0000 | Comparison |
| Decision Tree | 0.9942 | 0.9941 | 0.9996 | Comparison |
| Logistic Regression | 0.8445 | 0.8410 | 0.9398 | Baseline |

**Features used for risk classification:**
`temp_inside_celsius`, `temp_outside_celsius`, `humidity_percent`, `door_open_event`, `delay_hours_so_far`, `safe_temp_min`, `safe_temp_max`, `temp_deviation`, `fridge_failure`, `reliability_score`, `weather_risk_num`

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Dashboard** | Streamlit, Plotly, Folium |
| **ML Models** | Scikit-learn, XGBoost, LightGBM |
| **AI Analyst** | OpenAI GPT-4o-mini (RAG / Text-to-SQL) |
| **Database** | SQLite |
| **Data Processing** | Pandas, NumPy |
| **Model Persistence** | Joblib |
| **Deployment** | Streamlit Cloud |

---

## Project Structure

```
coldchain-intelligence/
├── dashboard/
│   └── app.py                  # Main Streamlit application (5 pages)
├── data/
│   └── coldchain.db            # SQLite database (5,000 shipments, 50,000+ sensor readings)
├── generator/
│   ├── generate_data.py        # Synthetic data schema and generation logic
│   └── populate_data.py        # Database population script
├── models/
│   ├── train_model.py          # Risk classification model training (5 algorithms)
│   ├── train_spoilage_model.py # Spoilage probability model training
│   ├── risk_model.pkl          # Trained LightGBM risk classifier
│   ├── spoilage_model.pkl      # Trained XGBoost spoilage regressor
│   ├── encoders.pkl            # Label encoders for categorical features
│   ├── feature_list.pkl        # Feature names for inference
│   ├── spoilage_features.pkl   # Spoilage model feature names
│   └── model_results.pkl       # Model comparison results DataFrame
├── simulator/
│   └── simulate_Stream.py      # Real-time data streaming simulator
├── requirements.txt
└── README.md
```

---

## Database Schema

| Table | Description |
|---|---|
| `shipments` | 5,000 records: product type, route, carrier, temperature range, spoilage flag |
| `sensor_readings` | 50,000+ hourly IoT readings per shipment (temp, humidity, GPS, fridge status) |
| `carriers` | Carrier profiles with reliability scores and on-time rates |
| `alerts` | System-generated alerts for temperature excursions and delays |
| `risk_scores` | ML-computed risk scores per sensor reading |

---

## Local Setup

```bash
# Clone the repository
git clone https://github.com/Indhusree06/coldchain-intelligence.git
cd coldchain-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Run the dashboard
streamlit run dashboard/app.py
```

---

## Deployment (Streamlit Cloud)

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account
3. Select `dashboard/app.py` as the main file
4. Add your OpenAI API key in **Settings → Secrets**:
   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   ```
5. Click Deploy

---

## Dataset

The dataset is synthetically generated to simulate realistic cold chain logistics:

- **5,000 shipments** across 7 product types (Vaccine, Seafood, Dairy, Fresh Produce, Pharmaceuticals, Frozen Meat, Ice Cream)
- **50,000+ sensor readings** at hourly intervals per shipment
- **10 carrier companies** with varying reliability profiles
- **Routes** across 15 US cities with weather risk variation
- **Spoilage rate** ~27% reflecting realistic cold chain failure conditions

---

## Author

**Indhusree Katlakanti**  
Master of Science in Data Science - University of Nebraska at Omaha

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/indhusree-katlakanti-a36481328/)
[![GitHub](https://img.shields.io/badge/GitHub-Indhusree06-black)](https://github.com/Indhusree06)
