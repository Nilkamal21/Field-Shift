"""
climate_trends.py
-----------------
Combined Climate and Land Analysis engine for Field Shift.
Processes NASA Earth Observation datasets using pandas and numpy to compute:
  1. NASA POWER: 10-year temperature trend, rainfall trend, rainfall variability
  2. NASA SMAP: Soil moisture level, moisture trend, dry-spell risk indicator
  3. NASA MODIS: Vegetation health (NDVI) level and multi-year trend

Returns numeric indicators AND plain English farmer verdicts, clearly tagging
the NASA dataset and data status (REAL or SAMPLE) for every verdict.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

# Ensure project root is in sys.path for direct script execution
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.nasa_power import fetch_power_data
from src.nasa_smap import fetch_smap_data
from src.nasa_modis import fetch_modis_data

DEFAULT_LAT = 26.18
DEFAULT_LON = 91.75


def load_dataset_records(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Load data for all three NASA datasets.
    Prefers real cached data; seamlessly falls back to verified multi-year sample baselines.
    """
    # 1. NASA POWER (Weather)
    power_data = fetch_power_data(lat=lat, lon=lon)

    # 2. NASA SMAP (Soil Moisture)
    # Check if local cache has full multi-month series; otherwise use verified 4-year sample baseline
    smap_data = fetch_smap_data(lat=lat, lon=lon)
    if len(smap_data.get("monthly_records", [])) < 12:
        sample_smap_path = Path("data/sample/smap_sample.json")
        if sample_smap_path.exists():
            with open(sample_smap_path, "r", encoding="utf-8") as f:
                smap_data = json.load(f)
                smap_data["metadata"]["source"] = "SAMPLE_BASELINE"
                smap_data["metadata"]["is_sample_data"] = True

    # 3. NASA MODIS (NDVI Vegetation Health)
    modis_data = fetch_modis_data(lat=lat, lon=lon)
    if len(modis_data.get("records", [])) < 20:
        sample_modis_path = Path("data/sample/modis_sample.json")
        if sample_modis_path.exists():
            with open(sample_modis_path, "r", encoding="utf-8") as f:
                modis_data = json.load(f)
                modis_data["metadata"]["source"] = "SAMPLE_BASELINE"
                modis_data["metadata"]["is_sample_data"] = True

    return power_data, smap_data, modis_data


def compute_power_trends(power_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze 10-year NASA POWER data for temperature and rainfall trends.
    """
    records = power_data.get("monthly_records", [])
    if not records:
        raise ValueError("NASA POWER records are empty.")

    df = pd.DataFrame(records)

    # Annual aggregations
    # rainfall_mm_day converted to estimated annual total: sum(mm/day * ~30.4 days)
    annual = df.groupby("year").agg(
        mean_temp=("temperature_c", "mean"),
        total_rain=("rainfall_mm_day", lambda x: np.sum(x * 30.4375))
    ).reset_index()

    years = annual["year"].to_numpy()
    temps = annual["mean_temp"].to_numpy()
    rains = annual["total_rain"].to_numpy()

    # Linear regression slopes (using numpy.polyfit)
    temp_slope_yr, _ = np.polyfit(years, temps, 1)
    temp_slope_decade = temp_slope_yr * 10.0  # °C change per decade

    rain_slope_yr, _ = np.polyfit(years, rains, 1)  # mm change per year

    # Rainfall Variability: Coefficient of Variation (CV) across years
    rain_mean = float(np.mean(rains))
    rain_std = float(np.std(rains))
    rain_cv = (rain_std / rain_mean * 100.0) if rain_mean > 0 else 0.0

    # Temperature verdict
    if temp_slope_decade > 0.15:
        temp_verdict = f"Getting hotter (+{temp_slope_decade:.2f} C/decade)"
    elif temp_slope_decade < -0.15:
        temp_verdict = f"Getting cooler ({temp_slope_decade:.2f} C/decade)"
    else:
        temp_verdict = "Stable temperature (minor fluctuations)"

    # Rainfall trend verdict
    if rain_slope_yr < -15.0:
        rain_trend_verdict = f"Rainfall is decreasing ({rain_slope_yr:.1f} mm/year)"
    elif rain_slope_yr > 15.0:
        rain_trend_verdict = f"Rainfall is increasing (+{rain_slope_yr:.1f} mm/year)"
    else:
        rain_trend_verdict = "Stable rainfall (no drastic long-term drift)"

    # Rainfall variability verdict
    if rain_cv > 15.0:
        rain_var_verdict = f"Rain is more unpredictable (variability: {rain_cv:.1f}%)"
    else:
        rain_var_verdict = f"Rain patterns are consistent (variability: {rain_cv:.1f}%)"

    source_badge = "SAMPLE DATA" if power_data.get("metadata", {}).get("is_sample_data", False) else "REAL NASA DATA"

    return {
        "dataset_name": "NASA POWER",
        "dataset_source": power_data.get("metadata", {}).get("source", "NASA_POWER_API"),
        "data_status": source_badge,
        "metrics": {
            "temp_slope_decade_c": round(float(temp_slope_decade), 2),
            "rain_slope_annual_mm": round(float(rain_slope_yr), 1),
            "rain_variability_cv_pct": round(float(rain_cv), 1),
            "mean_annual_rainfall_mm": round(rain_mean, 1)
        },
        "verdicts": [
            {
                "topic": "Temperature Trend",
                "verdict": temp_verdict,
                "dataset": "NASA POWER",
                "status": source_badge
            },
            {
                "topic": "Rainfall Trend",
                "verdict": rain_trend_verdict,
                "dataset": "NASA POWER",
                "status": source_badge
            },
            {
                "topic": "Rainfall Variability",
                "verdict": rain_var_verdict,
                "dataset": "NASA POWER",
                "status": source_badge
            }
        ]
    }


def compute_smap_trends(smap_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze NASA SMAP soil moisture data for root zone moisture and dry-spell risk.
    """
    records = smap_data.get("monthly_records", [])
    if not records:
        raise ValueError("NASA SMAP records are empty.")

    df = pd.DataFrame(records)

    mean_sm = float(df["sm_rootzone_m3m3"].mean())

    # Multi-month slope
    df["idx"] = np.arange(len(df))
    slope, _ = np.polyfit(df["idx"], df["sm_rootzone_m3m3"], 1)
    annual_sm_slope = slope * 12.0  # change per year

    # Dry-spell risk: percentage of months where root zone moisture < 0.20 m3/m3
    dry_threshold = 0.20
    dry_months_count = int((df["sm_rootzone_m3m3"] < dry_threshold).sum())
    dry_months_pct = (dry_months_count / len(df)) * 100.0

    # Soil moisture level verdict
    if mean_sm < 0.22:
        level_verdict = f"Low soil moisture ({mean_sm:.3f} m3/m3 - dry ground)"
    elif mean_sm > 0.32:
        level_verdict = f"High soil moisture ({mean_sm:.3f} m3/m3 - high moisture / waterlogging prone)"
    else:
        level_verdict = f"Moderate soil moisture ({mean_sm:.3f} m3/m3 - adequate for standard crops)"

    # Soil moisture trend verdict
    if annual_sm_slope < -0.005:
        trend_verdict = "Soil is getting drier (depleting root zone reserves)"
    elif annual_sm_slope > 0.005:
        trend_verdict = "Soil moisture increasing (recharging profile)"
    else:
        trend_verdict = "Soil moisture is stable"

    # Dry-spell indicator verdict
    if dry_months_pct >= 15.0:
        dry_verdict = f"Elevated dry-spell risk ({dry_months_pct:.1f}% of months experience low moisture)"
    else:
        dry_verdict = f"Low dry-spell risk ({dry_months_pct:.1f}% dry months)"

    source_badge = "SAMPLE BASELINE" if smap_data.get("metadata", {}).get("is_sample_data", False) else "REAL NASA DATA"

    return {
        "dataset_name": "NASA SMAP",
        "dataset_source": smap_data.get("metadata", {}).get("source", "NASA_SMAP"),
        "data_status": source_badge,
        "metrics": {
            "mean_rootzone_moisture_m3m3": round(mean_sm, 3),
            "annual_moisture_slope": round(float(annual_sm_slope), 4),
            "dry_months_count": dry_months_count,
            "dry_months_pct": round(dry_months_pct, 1)
        },
        "verdicts": [
            {
                "topic": "Soil Moisture Level",
                "verdict": level_verdict,
                "dataset": "NASA SMAP",
                "status": source_badge
            },
            {
                "topic": "Soil Moisture Trend",
                "verdict": trend_verdict,
                "dataset": "NASA SMAP",
                "status": source_badge
            },
            {
                "topic": "Dry-Spell Risk",
                "verdict": dry_verdict,
                "dataset": "NASA SMAP",
                "status": source_badge
            }
        ]
    }


def compute_modis_trends(modis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze NASA MODIS NDVI data for vegetation health levels and trends.
    """
    records = modis_data.get("records", [])
    if not records:
        raise ValueError("NASA MODIS records are empty.")

    df = pd.DataFrame(records)

    mean_ndvi = float(df["ndvi"].mean())
    max_ndvi = float(df["ndvi"].max())
    min_ndvi = float(df["ndvi"].min())

    # Multi-year trend: annual average NDVI slope
    annual_ndvi = df.groupby("year")["ndvi"].mean().reset_index()
    if len(annual_ndvi) > 1:
        slope_yr, _ = np.polyfit(annual_ndvi["year"], annual_ndvi["ndvi"], 1)
    else:
        slope_yr = 0.0

    # Vegetation health level verdict
    if mean_ndvi >= 0.50:
        level_verdict = f"Robust vegetation vigour (Mean NDVI: {mean_ndvi:.3f})"
    elif mean_ndvi >= 0.35:
        level_verdict = f"Moderate vegetation canopy (Mean NDVI: {mean_ndvi:.3f})"
    else:
        level_verdict = f"Low / sparse vegetation vigour (Mean NDVI: {mean_ndvi:.3f})"

    # Vegetation health trend verdict
    if slope_yr < -0.01:
        trend_verdict = f"Vegetation health is declining ({slope_yr:.3f}/year)"
    elif slope_yr > 0.01:
        trend_verdict = f"Vegetation health is improving (+{slope_yr:.3f}/year)"
    else:
        trend_verdict = "Vegetation health is stable"

    source_badge = "SAMPLE BASELINE" if modis_data.get("metadata", {}).get("is_sample_data", False) else "REAL NASA DATA"

    return {
        "dataset_name": "NASA MODIS",
        "dataset_source": modis_data.get("metadata", {}).get("source", "NASA_MODIS_ORNL_DAAC"),
        "data_status": source_badge,
        "metrics": {
            "mean_ndvi": round(mean_ndvi, 3),
            "peak_ndvi": round(max_ndvi, 3),
            "min_ndvi": round(min_ndvi, 3),
            "annual_ndvi_slope": round(float(slope_yr), 4)
        },
        "verdicts": [
            {
                "topic": "Vegetation Health Level",
                "verdict": level_verdict,
                "dataset": "NASA MODIS",
                "status": source_badge
            },
            {
                "topic": "Vegetation Health Trend",
                "verdict": trend_verdict,
                "dataset": "NASA MODIS",
                "status": source_badge
            }
        ]
    }


def analyze_climate_and_land(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> Dict[str, Any]:
    """
    Master function: Loads all 3 NASA datasets and executes combined climate & land analysis.
    Returns structured numbers, plain verdicts, and data source tags.
    """
    power_data, smap_data, modis_data = load_dataset_records(lat, lon)

    power_analysis = compute_power_trends(power_data)
    smap_analysis = compute_smap_trends(smap_data)
    modis_analysis = compute_modis_trends(modis_data)

    # Combine all plain verdicts into a single list
    all_verdicts = (
        power_analysis["verdicts"] +
        smap_analysis["verdicts"] +
        modis_analysis["verdicts"]
    )

    return {
        "region": {
            "latitude": lat,
            "longitude": lon,
            "district": "Kamrup",
            "state": "Assam",
            "country": "India"
        },
        "summary_verdicts": all_verdicts,
        "datasets": {
            "power": power_analysis,
            "smap": smap_analysis,
            "modis": modis_analysis
        }
    }


def print_climate_analysis(analysis: Dict[str, Any]):
    """Print a clean dashboard in the terminal displaying all NASA indicators and verdicts."""
    region = analysis["region"]
    verdicts = analysis["summary_verdicts"]
    ds = analysis["datasets"]

    print("=" * 75)
    print(" FIELD SHIFT - COMBINED CLIMATE & LAND ANALYSIS DASHBOARD")
    print("=" * 75)
    print(f" Region : {region['district']}, {region['state']}, {region['country']} (Lat {region['latitude']} N, Lon {region['longitude']} E)")
    print("-" * 75)
    print(f" {'Topic':<24} | {'Verdict / Finding':<35} | {'NASA Source'}")
    print(" " + "-" * 73)
    for v in verdicts:
        src_tag = f"{v['dataset']} [{v['status']}]"
        print(f" {v['topic']:<24} | {v['verdict']:<35} | {src_tag}")
    print("-" * 75)
    print(" NUMERICAL INDICATOR SUMMARY:")
    p_m = ds["power"]["metrics"]
    s_m = ds["smap"]["metrics"]
    m_m = ds["modis"]["metrics"]
    print(f"   * Temperature 10-Yr Trend : {p_m['temp_slope_decade_c']} C/decade  ({ds['power']['data_status']})")
    print(f"   * Annual Rainfall Trend   : {p_m['rain_slope_annual_mm']} mm/year    ({ds['power']['data_status']})")
    print(f"   * Rainfall Variability    : {p_m['rain_variability_cv_pct']}% CV           ({ds['power']['data_status']})")
    print(f"   * Mean Rootzone Moisture  : {s_m['mean_rootzone_moisture_m3m3']} m3/m3        ({ds['smap']['data_status']})")
    print(f"   * Dry-Spell Frequency     : {s_m['dry_months_pct']}% of months      ({ds['smap']['data_status']})")
    print(f"   * Mean Vegetation NDVI    : {m_m['mean_ndvi']} (Peak: {m_m['peak_ndvi']})   ({ds['modis']['data_status']})")
    print("=" * 75)


if __name__ == "__main__":
    print("Running Combined Climate & Land Analysis across all 3 NASA datasets...")
    analysis = analyze_climate_and_land(DEFAULT_LAT, DEFAULT_LON)
    print_climate_analysis(analysis)
