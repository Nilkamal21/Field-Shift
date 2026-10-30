"""
api.py
------
FastAPI backend service for Field Shift.
Provides REST API endpoints for the React frontend:
  - GET  /health     : Health check
  - GET  /about      : "How this works" educational text & NASA datasets guide
  - GET  /crops      : Returns list of supported crops and agronomic traits
  - POST /recommend  : Generates top 3 crop rotations, climate indicators,
                       and chart time-series with NASA data provenance flags.

CORS enabled for http://localhost:5173 (Vite) and http://localhost:3000 (Create React App).
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.scoring import recommend_rotations, load_crop_database
from src.climate_trends import analyze_climate_and_land, load_dataset_records

app = FastAPI(
    title="Field Shift API",
    description="NASA Earth Observation-driven Crop Rotation Decision Support Tool (NASA Space Apps Challenge)",
    version="1.0.0"
)

# Enable CORS for React frontends
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*"  # Allow all during hackathon local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------
class PriorityWeights(BaseModel):
    save_water: float = Field(0.30, ge=0.0, le=1.0, description="Weight for water conservation priority")
    rebuild_soil: float = Field(0.35, ge=0.0, le=1.0, description="Weight for soil health restoration priority")
    reduce_risk: float = Field(0.20, ge=0.0, le=1.0, description="Weight for climate risk mitigation priority")
    profit: float = Field(0.15, ge=0.0, le=1.0, description="Weight for economic profit priority")


class RecommendRequest(BaseModel):
    latitude: float = Field(26.18, ge=-90.0, le=90.0, description="Farm latitude (-90 to +90)")
    longitude: float = Field(91.75, ge=-180.0, le=180.0, description="Farm longitude (-180 to +180)")
    soil_type: Optional[str] = Field("Alluvial Soil", description="Local soil type (e.g. Alluvial, Sandy Loam, Clay)")
    selected_crops: List[str] = Field(
        default=["rice", "mustard", "lentil", "potato", "jute"],
        description="List of crop IDs chosen by the farmer (minimum 2 crops required)"
    )
    priority_weights: PriorityWeights = Field(
        default_factory=PriorityWeights,
        description="Farmer priority weights (save_water, rebuild_soil, reduce_risk, profit)"
    )


# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check():
    """Simple healthcheck endpoint to verify backend status."""
    return {
        "status": "healthy",
        "service": "Field Shift API",
        "version": "1.0.0",
        "region_default": "Kamrup, Assam, India"
    }


@app.get("/about", tags=["Educational"])
def get_about_info():
    """
    Returns an educational explanation of the project, the three NASA datasets used,
    and how the rule-based scoring engine works, formatted in plain English for frontend display.
    """
    return {
        "project": {
            "name": "Field Shift",
            "challenge": "NASA Space Apps Challenge — Adapting Farms with NASA Data",
            "target_region": "Kamrup District, Assam, India",
            "supported_crops": ["Rice", "Mustard", "Lentil", "Potato", "Jute"],
            "core_mission": "Help smallholder farmers adapt crop rotation strategies to changing rainfall, temperature, and soil conditions using authentic NASA satellite data."
        },
        "nasa_datasets": [
            {
                "name": "NASA POWER (Agroclimatology)",
                "dataset_id": "POWER Monthly Point API",
                "role": "Tracks 10-year meteorological trends (2015-2024): 2-meter air temperature, monthly precipitation, and solar radiation.",
                "agronomic_impact": "Identifies warming trends, long-term rainfall deficits, and monsoon unpredictability to favor drought-resilient or heat-tolerant crops.",
                "access": "Public REST API (no login required)."
            },
            {
                "name": "NASA SMAP (Soil Moisture Active Passive)",
                "dataset_id": "SPL4SMGP.008",
                "role": "Monitors root zone soil moisture (0-100 cm depth) and surface moisture (top 5 cm) at 9 km spatial resolution.",
                "agronomic_impact": "Detects winter/spring dry-spell frequencies and subsoil water deficits, penalizing water-demanding crops during depleted moisture cycles.",
                "access": "NASA AppEEARS API via Earthdata Login, with offline verified baseline fallback."
            },
            {
                "name": "NASA MODIS (Vegetation Indices)",
                "dataset_id": "MOD13Q1 (250m 16-Day)",
                "role": "Measures Normalized Difference Vegetation Index (NDVI) to assess seasonal crop canopy greenness and vegetative vigor.",
                "agronomic_impact": "Tracks multi-year canopy decline to trigger soil-restoration incentives, prioritizing nitrogen-fixing legumes and organic matter builders.",
                "access": "NASA ORNL DAAC REST Web Service, with offline verified baseline fallback."
            }
        ],
        "scoring_rules": [
            {
                "rule": "Legume After Heavy Feeder (+22 pts)",
                "explanation": "Planting a nitrogen-fixing legume (Lentil) immediately after heavy nutrient extractors (Rice or Potato) restores soil nitrogen naturally and reduces fertilizer expenses."
            },
            {
                "rule": "Consecutive Crop Penalty (-30 pts)",
                "explanation": "Planting the exact same crop two years in a row is heavily penalized to stop soil-borne disease cycles, insect buildup, and specific nutrient exhaustion."
            },
            {
                "rule": "Root Profile Diversity (+10 pts)",
                "explanation": "Alternating shallow fibrous root systems (Rice, Potato) with deep taproots (Mustard, Jute) breaks plough pan compaction and utilizes different soil horizons."
            },
            {
                "rule": "NASA Climate Adaptation Adjustment (Up to +28 pts)",
                "explanation": "Decreasing rainfall and elevated dry-spell frequency award bonuses to low-water, drought-tolerant crops; temperature warming trends reward heat-tolerant crops like Jute."
            }
        ],
        "transparency_guarantee": "Scoring uses transparent, deterministic agronomic rules—not black-box AI. Every recommendation explains the exact NASA data trend that triggered it."
    }


@app.get("/crops", tags=["Agronomy"])
def get_crops():
    """
    Returns all crops in the database with their agronomic characteristics,
    water requirements, tolerances, and soil impacts.
    """
    crops_path = BASE_DIR / "data" / "crops.json"
    if not crops_path.exists():
        raise HTTPException(status_code=500, detail="Crops database file not found.")

    with open(crops_path, "r", encoding="utf-8") as f:
        crops_list = json.load(f)

    return {
        "total_crops": len(crops_list),
        "crops": crops_list
    }


@app.post("/recommend", tags=["Decision Support"])
def get_recommendations(req: RecommendRequest):
    """
    Core Decision-Support Endpoint:
      1. Validates inputs and coordinates.
      2. Analyzes 10-year NASA POWER weather trends, NASA SMAP soil moisture, and NASA MODIS NDVI.
      3. Evaluates 3-year crop rotations and returns the top 3 with plain-English NASA-driven explanations.
      4. Returns chart time-series for frontend visualizations with transparent REAL/SAMPLE data tags.
    """
    crops_db = load_crop_database()

    # 1. Edge Case: Empty or missing selected crops
    if not req.selected_crops:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No crops were selected. Please select at least 2 crops to plan a rotation."
        )

    # 2. Edge Case: Check for unrecognized crop IDs
    unknown_crops = [cid for cid in req.selected_crops if cid not in crops_db]
    if unknown_crops:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unrecognized crop ID(s): {unknown_crops}. Available crops are: {list(crops_db.keys())}"
        )

    # 3. Edge Case: Fewer than 2 distinct valid crops
    valid_selected = list(dict.fromkeys(req.selected_crops))  # deduplicate preserving order
    if len(valid_selected) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least 2 distinct crops must be selected to plan a rotation. Valid options: {list(crops_db.keys())}"
        )

    # 4. Edge Case: Coordinate validation
    if not (-90.0 <= req.latitude <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Latitude must be between -90.0 and +90.0. Received: {req.latitude}"
        )
    if not (-180.0 <= req.longitude <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Longitude must be between -180.0 and +180.0. Received: {req.longitude}"
        )

    try:
        # Run combined NASA climate analysis (falls back to sample baseline automatically if offline)
        climate_analysis = analyze_climate_and_land(lat=req.latitude, lon=req.longitude)

        # Score and rank 3-year rotations
        weights_dict = req.priority_weights.dict()
        ranking_result = recommend_rotations(
            selected_crops=valid_selected,
            priority_weights=weights_dict,
            lat=req.latitude,
            lon=req.longitude,
            top_n=3,
            climate_analysis=climate_analysis
        )

        # Pull time-series for frontend charts
        power_raw, smap_raw, modis_raw = load_dataset_records(lat=req.latitude, lon=req.longitude)

        # Weather chart series (monthly temp & rain from POWER)
        power_time_series = [
            {
                "date": r["date"],
                "year": r["year"],
                "month": r["month"],
                "temperature_c": r["temperature_c"],
                "rainfall_mm_day": r["rainfall_mm_day"],
                "solar_radiation_mj": r["solar_radiation_mj"]
            }
            for r in power_raw.get("monthly_records", [])
        ]

        # Soil moisture chart series (monthly rootzone & surface moisture from SMAP)
        smap_time_series = [
            {
                "date": r["date"],
                "year": r["year"],
                "month": r["month"],
                "sm_rootzone_m3m3": r["sm_rootzone_m3m3"],
                "sm_surface_m3m3": r["sm_surface_m3m3"],
                "saturation_pct": round(r["sm_rootzone_wetness"] * 100, 1)
            }
            for r in smap_raw.get("monthly_records", [])
        ]

        # Vegetation NDVI chart series (16-day composites from MODIS)
        modis_time_series = [
            {
                "date": r["date"],
                "year": r["year"],
                "month": r["month"],
                "ndvi": r["ndvi"]
            }
            for r in modis_raw.get("records", [])
        ]

        return {
            "farm_profile": {
                "latitude": req.latitude,
                "longitude": req.longitude,
                "district": climate_analysis["region"]["district"],
                "state": climate_analysis["region"]["state"],
                "country": climate_analysis["region"]["country"],
                "soil_type": req.soil_type,
                "selected_crops": valid_selected,
                "priority_weights": ranking_result["priority_weights_used"]
            },
            "top_rotations": ranking_result["top_rotations"],
            "climate_verdicts": climate_analysis["summary_verdicts"],
            "indicators_summary": ranking_result["nasa_indicators_summary"],
            "data_provenance": {
                "nasa_power": {
                    "source": climate_analysis["datasets"]["power"]["dataset_source"],
                    "status": climate_analysis["datasets"]["power"]["data_status"],
                    "parameters": "Temperature (T2M), Rainfall (PRECTOTCORR), Solar Irradiance"
                },
                "nasa_smap": {
                    "source": climate_analysis["datasets"]["smap"]["dataset_source"],
                    "status": climate_analysis["datasets"]["smap"]["data_status"],
                    "parameters": "Root Zone Soil Moisture (0-100cm), Surface Moisture (0-5cm)"
                },
                "nasa_modis": {
                    "source": climate_analysis["datasets"]["modis"]["dataset_source"],
                    "status": climate_analysis["datasets"]["modis"]["data_status"],
                    "parameters": "16-day 250m NDVI Vegetation Greenness Index"
                }
            },
            "chart_time_series": {
                "weather_series": {
                    "dataset": "NASA POWER",
                    "status": climate_analysis["datasets"]["power"]["data_status"],
                    "total_points": len(power_time_series),
                    "records": power_time_series
                },
                "soil_moisture_series": {
                    "dataset": "NASA SMAP",
                    "status": climate_analysis["datasets"]["smap"]["data_status"],
                    "total_points": len(smap_time_series),
                    "records": smap_time_series
                },
                "vegetation_ndvi_series": {
                    "dataset": "NASA MODIS",
                    "status": climate_analysis["datasets"]["modis"]["data_status"],
                    "total_points": len(modis_time_series),
                    "records": modis_time_series
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Field Shift recommendation engine error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    print("Starting Field Shift API server on http://localhost:8000...")
    print("Interactive Swagger UI docs available at: http://localhost:8000/docs")
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
