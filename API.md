# Field Shift — API Contract & React Integration Guide

This document defines the complete REST API contract for the **Field Shift** backend, designed to power your React frontend for the NASA Space Apps Challenge ("Adapting Farms with NASA Data").

---

## 1. Quick Start & Server URL

- **Base URL**: `http://localhost:8000` (or `http://127.0.0.1:8000`)
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **CORS Allowed Origins**: `http://localhost:5173` (Vite), `http://localhost:3000` (Create React App), and `http://127.0.0.1:*`

---

## 2. API Endpoints

### Endpoint 1: Health Check
Verify that the backend service and Python environment are running.

- **Method**: `GET`
- **Path**: `/health`
- **Request Headers**: None required

#### Sample Response (`200 OK`)
```json
{
  "status": "healthy",
  "service": "Field Shift API",
  "version": "1.0.0",
  "region_default": "Kamrup, Assam, India"
}
```

---

### Endpoint 2: Get Crops Catalog
Fetch all available crops and their agronomic attributes to populate checkboxes, crop pickers, and filter pills in your React UI.

- **Method**: `GET`
- **Path**: `/crops`
- **Request Headers**: None required

#### Sample Response (`200 OK`)
```json
{
  "total_crops": 5,
  "crops": [
    {
      "id": "rice",
      "name": "Rice (Sali / Kharif Paddy)",
      "category": "Cereal",
      "season": "kharif",
      "duration_days_est": [120, 140],
      "water_need": "high",
      "water_requirement_mm_est": 1100,
      "heat_tolerance": "medium",
      "drought_tolerance": "low",
      "root_type": "shallow",
      "nitrogen_role": "heavy_feeder",
      "soil_effect": "Heavy nutrient depletion (N-P-K); continuous flooding can cause subsoil compaction.",
      "soil_organic_matter_impact": "negative",
      "profit_potential_est": "medium"
    },
    {
      "id": "mustard",
      "name": "Mustard (Toria / Rapeseed)",
      "category": "Oilseed",
      "season": "rabi",
      "duration_days_est": [90, 105],
      "water_need": "low",
      "water_requirement_mm_est": 300,
      "heat_tolerance": "low",
      "drought_tolerance": "medium",
      "root_type": "deep_taproot",
      "nitrogen_role": "neutral",
      "soil_effect": "Deep taproot breaks hard soil layers and accesses deep nutrients; pest-break crop after rice.",
      "soil_organic_matter_impact": "neutral",
      "profit_potential_est": "medium_high"
    },
    {
      "id": "lentil",
      "name": "Lentil (Masoor Dal)",
      "category": "Pulse / Legume",
      "season": "rabi",
      "duration_days_est": [100, 120],
      "water_need": "low",
      "water_requirement_mm_est": 250,
      "heat_tolerance": "low",
      "drought_tolerance": "high",
      "root_type": "taproot",
      "nitrogen_role": "fixer",
      "soil_effect": "Fixes atmospheric nitrogen (~30-40 kg N/ha) via root nodules, restoring depleted soil after heavy feeders.",
      "soil_organic_matter_impact": "positive",
      "profit_potential_est": "high"
    },
    {
      "id": "potato",
      "name": "Potato (Aloo)",
      "category": "Tuber / Cash Crop",
      "season": "rabi",
      "duration_days_est": [85, 105],
      "water_need": "medium",
      "water_requirement_mm_est": 500,
      "heat_tolerance": "low",
      "drought_tolerance": "low",
      "root_type": "shallow",
      "nitrogen_role": "heavy_feeder",
      "soil_effect": "High potassium and nitrogen consumer; soil loosening from earthing up and harvesting improves tilth.",
      "soil_organic_matter_impact": "negative",
      "profit_potential_est": "high"
    },
    {
      "id": "jute",
      "name": "Jute (Pat / Fiber Crop)",
      "category": "Fiber",
      "season": "zaid_pre_monsoon",
      "duration_days_est": [110, 130],
      "water_need": "high",
      "water_requirement_mm_est": 600,
      "heat_tolerance": "high",
      "drought_tolerance": "medium",
      "root_type": "deep_taproot",
      "nitrogen_role": "neutral",
      "soil_effect": "Massive leaf shedding adds 2-3 tons/ha of rich organic mulch; strong taproot aerates dense subsoil.",
      "soil_organic_matter_impact": "positive",
      "profit_potential_est": "medium"
    }
  ]
}
```

---

### Endpoint 3: Generate Crop Rotation Recommendations
The core decision-support engine. Sends farmer selections and receives ranked 3-year rotations, plain-English "why" cards, climate verdicts, and chart time-series.

- **Method**: `POST`
- **Path**: `/recommend`
- **Content-Type**: `application/json`

#### Request Body Structure
```json
{
  "latitude": 26.18,
  "longitude": 91.75,
  "soil_type": "Alluvial Soil",
  "selected_crops": ["rice", "mustard", "lentil", "potato", "jute"],
  "priority_weights": {
    "save_water": 0.30,
    "rebuild_soil": 0.35,
    "reduce_risk": 0.20,
    "profit": 0.15
  }
}
```

| Field | Type | Description |
|---|---|---|
| `latitude` | `float` | Farm latitude (Default: `26.18` for Kamrup, Assam) |
| `longitude` | `float` | Farm longitude (Default: `91.75` for Kamrup, Assam) |
| `soil_type` | `string` | Local soil description (e.g. `"Alluvial"`, `"Clay"`, `"Sandy Loam"`) |
| `selected_crops` | `array[string]` | Crop IDs chosen by farmer (minimum 2 crops required) |
| `priority_weights` | `object` | Relative weights between `0.0` and `1.0` (auto-normalized) |

#### Sample Response Structure (`200 OK`)
```json
{
  "farm_profile": {
    "latitude": 26.18,
    "longitude": 91.75,
    "district": "Kamrup",
    "state": "Assam",
    "country": "India",
    "soil_type": "Alluvial Soil",
    "selected_crops": ["rice", "mustard", "lentil", "potato", "jute"],
    "priority_weights": {
      "save_water": 0.3,
      "rebuild_soil": 0.35,
      "reduce_risk": 0.2,
      "profit": 0.15
    }
  },
  "top_rotations": [
    {
      "rotation": ["mustard", "potato", "lentil"],
      "crop_names": [
        "Mustard (Toria / Rapeseed)",
        "Potato (Aloo)",
        "Lentil (Masoor Dal)"
      ],
      "scores": {
        "water_score": 100.0,
        "soil_score": 100.0,
        "risk_score": 89.0,
        "profit_score": 100.0
      },
      "composite_score": 97.8,
      "reasons": [
        "[NASA POWER] Decreasing rainfall trend (-25.1 mm/yr) rewards water-efficient crops (Mustard, Lentil).",
        "[NASA SMAP] High dry-spell risk (16.7% low-moisture months) favors drought-resilient crops in the rotation.",
        "[Agronomy] Rotating nitrogen-fixing Lentil after heavy-feeder Potato naturally replenishes soil nitrogen.",
        "[Agronomy] Combining deep taproots (subsoil aeration) with shallow roots balances soil profile utilization.",
        "[NASA MODIS] Moderate canopy vigour (0.488 NDVI) prioritizes soil organic matter builders (Lentil).",
        "[NASA POWER] High rainfall variability (16.1% CV) is mitigated by diversified root depths and moisture buffers."
      ]
    }
  ],
  "climate_verdicts": [
    {
      "topic": "Temperature Trend",
      "verdict": "Getting cooler (-0.63 C/decade)",
      "dataset": "NASA POWER",
      "status": "REAL NASA DATA"
    },
    {
      "topic": "Rainfall Trend",
      "verdict": "Rainfall is decreasing (-25.1 mm/year)",
      "dataset": "NASA POWER",
      "status": "REAL NASA DATA"
    },
    {
      "topic": "Rainfall Variability",
      "verdict": "Rain is more unpredictable (variability: 16.1%)",
      "dataset": "NASA POWER",
      "status": "REAL NASA DATA"
    },
    {
      "topic": "Soil Moisture Level",
      "verdict": "Moderate soil moisture (0.271 m3/m3 - adequate for standard crops)",
      "dataset": "NASA SMAP",
      "status": "SAMPLE BASELINE"
    },
    {
      "topic": "Dry-Spell Risk",
      "verdict": "Elevated dry-spell risk (16.7% of months experience low moisture)",
      "dataset": "NASA SMAP",
      "status": "SAMPLE BASELINE"
    },
    {
      "topic": "Vegetation Health Level",
      "verdict": "Moderate vegetation canopy (Mean NDVI: 0.488)",
      "dataset": "NASA MODIS",
      "status": "SAMPLE BASELINE"
    }
  ],
  "indicators_summary": {
    "rainfall_trend_mm_yr": -25.1,
    "rainfall_cv_pct": 16.1,
    "temperature_slope_c_decade": -0.63,
    "mean_soil_moisture_m3m3": 0.271,
    "dry_spell_pct": 16.7,
    "mean_ndvi": 0.488
  },
  "data_provenance": {
    "nasa_power": {
      "source": "LOCAL_CACHE",
      "status": "REAL NASA DATA",
      "parameters": "Temperature (T2M), Rainfall (PRECTOTCORR), Solar Irradiance"
    },
    "nasa_smap": {
      "source": "SAMPLE_BASELINE",
      "status": "SAMPLE BASELINE",
      "parameters": "Root Zone Soil Moisture (0-100cm), Surface Moisture (0-5cm)"
    },
    "nasa_modis": {
      "source": "SAMPLE_BASELINE",
      "status": "SAMPLE BASELINE",
      "parameters": "16-day 250m NDVI Vegetation Greenness Index"
    }
  },
  "chart_time_series": {
    "weather_series": {
      "dataset": "NASA POWER",
      "status": "REAL NASA DATA",
      "total_points": 120,
      "records": [
        {"date": "2015-01", "year": 2015, "month": 1, "temperature_c": 16.74, "rainfall_mm_day": 0.29, "solar_radiation_mj": 13.37}
      ]
    },
    "soil_moisture_series": {
      "dataset": "NASA SMAP",
      "status": "SAMPLE BASELINE",
      "total_points": 48,
      "records": [
        {"date": "2021-01", "year": 2021, "month": 1, "sm_rootzone_m3m3": 0.222, "sm_surface_m3m3": 0.174, "saturation_pct": 49.3}
      ]
    },
    "vegetation_ndvi_series": {
      "dataset": "NASA MODIS",
      "status": "SAMPLE BASELINE",
      "total_points": 69,
      "records": [
        {"date": "2022-01-01", "year": 2022, "month": 1, "ndvi": 0.334}
      ]
    }
  }
}
```

---

## 3. Error Responses

If fewer than 2 crops are selected or invalid coordinates are passed:

#### Response (`400 Bad Request`)
```json
{
  "detail": "At least 2 valid crops must be selected. Valid options are: ['rice', 'mustard', 'lentil', 'potato', 'jute']"
}
```

---

## 4. React Integration Code Examples

You can copy and paste these standard snippets into your React frontend.

### A. Fetching Crops List in a React Component (`useEffect`)
```jsx
import React, { useState, useEffect } from "react";

export function CropSelector({ onSelectCrops }) {
  const [crops, setCrops] = useState([]);
  const [selected, setSelected] = useState(["rice", "mustard", "lentil"]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/crops")
      .then((res) => res.json())
      .then((data) => {
        setCrops(data.crops);
        setLoading(false);
      })
      .catch((err) => console.error("Error loading crops:", err));
  }, []);

  const handleToggle = (cropId) => {
    const updated = selected.includes(cropId)
      ? selected.filter((id) => id !== cropId)
      : [...selected, cropId];
    setSelected(updated);
    onSelectCrops(updated);
  };

  if (loading) return <div>Loading NASA crop catalog...</div>;

  return (
    <div className="crop-grid">
      {crops.map((crop) => (
        <label key={crop.id} className="crop-card">
          <input
            type="checkbox"
            checked={selected.includes(crop.id)}
            onChange={() => handleToggle(crop.id)}
          />
          <span>{crop.name}</span>
          <small>Water: {crop.water_need} | N-Role: {crop.nitrogen_role}</small>
        </label>
      ))}
    </div>
  );
}
```

---

### B. Calling `/recommend` on Form Submit
```jsx
export async function getRotationPlan(farmData) {
  const payload = {
    latitude: farmData.lat || 26.18,
    longitude: farmData.lon || 91.75,
    soil_type: farmData.soilType || "Alluvial Soil",
    selected_crops: farmData.selectedCrops,
    priority_weights: farmData.weights || {
      save_water: 0.30,
      rebuild_soil: 0.35,
      reduce_risk: 0.20,
      profit: 0.15
    }
  };

  const response = await fetch("http://localhost:8000/recommend", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to generate rotation plan");
  }

  return await response.json();
}
```

---

### C. Displaying NASA Data Provenance Badges
NASA judges look for transparency on data sources. Use this JSX pattern:

```jsx
export function NasaStatusBadge({ dataset, status }) {
  const isReal = status === "REAL NASA DATA";
  return (
    <span
      style={{
        padding: "4px 8px",
        borderRadius: "4px",
        fontSize: "12px",
        fontWeight: "bold",
        backgroundColor: isReal ? "#e6ffed" : "#fff8e6",
        color: isReal ? "#155724" : "#856404",
        border: `1px solid ${isReal ? "#c3e6cb" : "#ffeeba"}`
      }}
    >
      {dataset}: {isReal ? "REAL NASA OBSERVATION" : "SAMPLE BASELINE"}
    </span>
  );
}
```
