"""
nasa_modis.py
-------------
Fetches and processes Normalized Difference Vegetation Index (NDVI) time-series
from NASA MODIS (MOD13Q1: 250m 16-day Vegetation Indices).

Source: NASA ORNL DAAC MODIS REST Web Service (https://modis.ornl.gov/rst/api/v1/)
Parameters:
  - 250m_16_days_NDVI: Normalized Difference Vegetation Index (scale factor: 0.0001)
  - Indicates canopy greenness, biomass density, and crop vegetative health.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

ORNL_DAAC_API_URL = "https://modis.ornl.gov/rst/api/v1"
PRODUCT_NAME = "MOD13Q1"
BAND_NAME = "250m_16_days_NDVI"

# Default coordinates: Kamrup district, Assam, India
DEFAULT_LAT = 26.18
DEFAULT_LON = 91.75
DEFAULT_START_YEAR = 2022
DEFAULT_END_YEAR = 2024


def get_cache_filepath(lat: float, lon: float, start_year: int, end_year: int, cache_dir: str = "cache") -> Path:
    """Generate local cache filename based on coordinates and years."""
    filename = f"modis_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json"
    return Path(cache_dir) / filename


def load_sample_modis_data(reason: str, sample_dir: str = "data/sample") -> Dict[str, Any]:
    """Load verified Kamrup MODIS baseline sample data and label it clearly."""
    sample_path = Path(sample_dir) / "modis_sample.json"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample MODIS data file not found at {sample_path}")

    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["metadata"]["source"] = "SAMPLE_DATA"
    data["metadata"]["is_sample_data"] = True
    data["metadata"]["reason"] = reason
    return data


def fetch_modis_data(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    start_year: int = DEFAULT_START_YEAR,
    end_year: int = DEFAULT_END_YEAR,
    cache_dir: str = "cache",
    use_cache: bool = True,
    sample_dir: str = "data/sample"
) -> Dict[str, Any]:
    """
    Fetch NDVI vegetation health time-series from NASA MODIS for a given lat/lon.

    Returns a structured dictionary with:
      - metadata (coordinates, period, source: 'NASA_MODIS_ORNL_DAAC' | 'LOCAL_CACHE' | 'SAMPLE_DATA')
      - records (16-day composite records with calendar date, year, month, and scaled NDVI)
      - summary (mean NDVI, peak greenness, minimum greenness, health status)
    """
    cache_path = get_cache_filepath(lat, lon, start_year, end_year, cache_dir)

    # 1. Check local cache first
    if use_cache and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["metadata"]["source"] = "LOCAL_CACHE"
                return data
        except (json.JSONDecodeError, IOError):
            pass

    # 2. Try fetching from NASA ORNL DAAC REST API
    try:
        # Step A: Get available dates list
        url = f"{ORNL_DAAC_API_URL}/{PRODUCT_NAME}/dates"
        params = {"latitude": lat, "longitude": lon}
        headers = {"Accept": "application/json"}

        dates_res = requests.get(url, params=params, headers=headers, timeout=15)
        dates_res.raise_for_status()
        all_dates = [d["modis_date"] for d in dates_res.json().get("dates", [])]

        # Filter target dates within target year range
        target_dates = [
            d for d in all_dates
            if len(d) >= 5 and start_year <= int(d[1:5]) <= end_year
        ]

        if not target_dates:
            return load_sample_modis_data(
                reason=f"No MODIS composite dates found for range {start_year}-{end_year}.",
                sample_dir=sample_dir
            )

        # ORNL DAAC accepts maximum 10 dates per subset request.
        # We request the latest 10 available composites for an immediate, reliable query.
        query_chunk = target_dates[-10:] if len(target_dates) >= 10 else target_dates

        subset_url = f"{ORNL_DAAC_API_URL}/{PRODUCT_NAME}/subset"
        subset_params = {
            "latitude": lat,
            "longitude": lon,
            "band": BAND_NAME,
            "startDate": query_chunk[0],
            "endDate": query_chunk[-1],
            "kmAboveBelow": 0,
            "kmLeftRight": 0
        }

        sub_res = requests.get(subset_url, params=subset_params, headers=headers, timeout=20)
        sub_res.raise_for_status()

        raw_subsets = sub_res.json().get("subset", [])
        if not raw_subsets:
            return load_sample_modis_data(
                reason="NASA ORNL DAAC returned an empty subset for these coordinates.",
                sample_dir=sample_dir
            )

        parsed_data = parse_modis_response(raw_subsets, lat, lon, start_year, end_year)
        parsed_data["metadata"]["source"] = "NASA_MODIS_ORNL_DAAC"
        parsed_data["metadata"]["is_sample_data"] = False

        # Save to local cache
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as cf:
            json.dump(parsed_data, cf, indent=2)

        return parsed_data

    except requests.exceptions.RequestException as err:
        # Fallback to verified baseline sample data
        return load_sample_modis_data(
            reason=f"NASA ORNL DAAC query timed out or unavailable ({type(err).__name__}). Using verified Kamrup sample data.",
            sample_dir=sample_dir
        )


def parse_modis_response(
    subsets: List[Dict[str, Any]],
    lat: float,
    lon: float,
    start_year: int,
    end_year: int
) -> Dict[str, Any]:
    """Parse raw MODIS subset items and calculate vegetation metrics."""
    records = []
    ndvi_values = []

    for item in subsets:
        c_date = item.get("calendar_date")
        data_vals = item.get("data", [])
        if not data_vals or not c_date:
            continue

        raw_val = data_vals[0]
        # MODIS NDVI valid range is -2000 to 10000 with a 0.0001 scale factor.
        if raw_val <= -2000 or raw_val > 10000:
            continue

        ndvi = round(raw_val * 0.0001, 3)
        parts = c_date.split("-")
        year = int(parts[0])
        month = int(parts[1])

        ndvi_values.append(ndvi)
        records.append({
            "date": c_date,
            "year": year,
            "month": month,
            "modis_date": item.get("modis_date"),
            "ndvi": ndvi
        })

    avg_ndvi = round(sum(ndvi_values) / len(ndvi_values), 3) if ndvi_values else 0.0
    min_ndvi = round(min(ndvi_values), 3) if ndvi_values else 0.0
    max_ndvi = round(max(ndvi_values), 3) if ndvi_values else 0.0

    if avg_ndvi >= 0.50:
        health_status = "Robust / High Vegetation Vigour"
    elif avg_ndvi >= 0.35:
        health_status = "Moderate Crop Canopy"
    else:
        health_status = "Low / Sparse Canopy"

    return {
        "metadata": {
            "dataset": "NASA MODIS (MOD13Q1)",
            "product": "250m 16-Day Vegetation Indices",
            "latitude": lat,
            "longitude": lon,
            "start_year": start_year,
            "end_year": end_year,
            "total_records": len(records),
            "scale_factor": 0.0001,
            "is_sample_data": False,
            "units": "NDVI (-1.0 to +1.0, dimensionless greenness index)"
        },
        "summary": {
            "mean_ndvi": avg_ndvi,
            "min_ndvi": min_ndvi,
            "max_ndvi": max_ndvi,
            "canopy_status": health_status
        },
        "records": records
    }


def print_modis_summary(data: Dict[str, Any]):
    """Print an easy-to-read terminal summary of NASA MODIS NDVI data."""
    meta = data["metadata"]
    summary = data["summary"]
    records = data["records"]

    is_sample = meta.get("is_sample_data", False)
    badge = "[SAMPLE DATA]" if is_sample else "[REAL NASA DATA]"

    print("=" * 65)
    print(f" FIELD SHIFT - NASA MODIS NDVI VEGETATION HEALTH {badge}")
    print("=" * 65)
    print(f" Region         : Lat {meta['latitude']} N, Lon {meta['longitude']} E (Kamrup, Assam)")
    print(f" Time Period    : {meta['start_year']} to {meta['end_year']} ({meta['total_records']} composites)")
    print(f" Data Source    : {meta.get('source')} {badge}")
    if is_sample and "reason" in meta:
        print(f" Status Reason  : {meta['reason']}")
    print("-" * 65)
    print(" VEGETATION HEALTH METRICS:")
    print(f"   * Mean NDVI Greenness  : {summary['mean_ndvi']} ({summary['canopy_status']})")
    print(f"   * Peak Greenness (Max) : {summary['max_ndvi']}")
    print(f"   * Minimum Dip (Tillage): {summary['min_ndvi']}")
    print("-" * 65)
    print(" SAMPLE 16-DAY NDVI RECORDS (First 3 and Last 3 composites):")
    sample_rows = records[:3] + records[-3:] if len(records) >= 6 else records
    print(f"   {'Calendar Date':<15} | {'MODIS Code':<12} | {'NDVI (Greenness)':<16} | {'Visual'}")
    print("   " + "-" * 60)
    for r in sample_rows:
        val = r["ndvi"]
        bars = int(val * 25)
        bar_chart = "#" * max(0, bars)
        print(f"   {r['date']:<15} | {r.get('modis_date', 'N/A'):<12} | {val:<16.3f} | {bar_chart}")
    print("=" * 65)


if __name__ == "__main__":
    print("Connecting to NASA ORNL DAAC and fetching MODIS NDVI data for Kamrup, Assam...")
    data = fetch_modis_data(lat=DEFAULT_LAT, lon=DEFAULT_LON)
    print_modis_summary(data)
