"""
nasa_smap.py
------------
Handles fetching and processing soil moisture data from NASA SMAP
(Soil Moisture Active Passive) mission.

Product: SPL4SMGP.008 (Global 3-hourly 9km Surface and Root Zone Soil Moisture)
Parameters:
  - sm_rootzone: Root zone soil moisture (0-100 cm depth) in m^3/m^3
  - sm_surface:  Surface soil moisture (0-5 cm depth) in m^3/m^3
  - sm_rootzone_wetness: Relative saturation (0 = bone dry, 1 = fully saturated)

Authentication:
  NASA Earthdata Login (credentials read from .env via EARTHDATA_USERNAME and EARTHDATA_PASSWORD).
  If credentials are missing or AppEEARS tasks are queued in the background, this module
  automatically provides a clearly labeled SAMPLE DATA fallback for Kamrup, Assam.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

# AppEEARS API endpoints
APPEEARS_API_URL = "https://appeears.earthdatacloud.nasa.gov/api"
LOGIN_URL = f"{APPEEARS_API_URL}/login"
TASK_URL = f"{APPEEARS_API_URL}/task"
BUNDLE_URL = f"{APPEEARS_API_URL}/bundle"

# Default coordinates: Kamrup district, Assam, India
DEFAULT_LAT = 26.18
DEFAULT_LON = 91.75
DEFAULT_START_YEAR = 2021
DEFAULT_END_YEAR = 2024


def get_cache_filepath(lat: float, lon: float, start_year: int, end_year: int, cache_dir: str = "cache") -> Path:
    """Generate local cache filename based on coordinates and years."""
    filename = f"smap_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json"
    return Path(cache_dir) / filename


def load_sample_smap_data(reason: str, sample_dir: str = "data/sample") -> Dict[str, Any]:
    """Load the verified Kamrup baseline sample data and label it clearly."""
    sample_path = Path(sample_dir) / "smap_sample.json"
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample SMAP data file not found at {sample_path}")

    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["metadata"]["source"] = "SAMPLE_DATA"
    data["metadata"]["is_sample_data"] = True
    data["metadata"]["reason"] = reason
    return data


def authenticate_earthdata() -> Optional[str]:
    """
    Authenticate against NASA Earthdata via AppEEARS API using credentials from .env.
    Returns Bearer token string if successful, or None if credentials are missing/invalid.
    """
    # Load .env file
    load_dotenv()
    username = os.getenv("EARTHDATA_USERNAME")
    password = os.getenv("EARTHDATA_PASSWORD")

    if not username or not password:
        return None

    try:
        response = requests.post(
            LOGIN_URL,
            auth=(username, password),
            timeout=15
        )
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("token")
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def fetch_smap_data(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    start_year: int = DEFAULT_START_YEAR,
    end_year: int = DEFAULT_END_YEAR,
    cache_dir: str = "cache",
    use_cache: bool = True,
    sample_dir: str = "data/sample"
) -> Dict[str, Any]:
    """
    Fetch soil moisture data for a given lat/lon.

    Process:
      1. Check local cache.
      2. If not cached, attempt NASA Earthdata authentication.
      3. Check for completed AppEEARS tasks or submit a new point extraction task.
      4. If NASA task is queued/processing or authentication fails, return labeled SAMPLE DATA.
    """
    cache_path = get_cache_filepath(lat, lon, start_year, end_year, cache_dir)

    # 1. Local Cache Check
    if use_cache and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                cached_data["metadata"]["source"] = "LOCAL_CACHE"
                return cached_data
        except (json.JSONDecodeError, IOError):
            pass

    # 2. Check credentials & authenticate
    load_dotenv()
    username = os.getenv("EARTHDATA_USERNAME")
    password = os.getenv("EARTHDATA_PASSWORD")

    if not username or not password:
        return load_sample_smap_data(
            reason="Missing EARTHDATA_USERNAME or EARTHDATA_PASSWORD in .env file.",
            sample_dir=sample_dir
        )

    token = authenticate_earthdata()
    if not token:
        return load_sample_smap_data(
            reason="Earthdata login failed. Please verify credentials in .env.",
            sample_dir=sample_dir
        )

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Check AppEEARS for existing completed tasks for this location
    try:
        tasks_resp = requests.get(TASK_URL, headers=headers, timeout=15)
        if tasks_resp.status_code == 200:
            tasks = tasks_resp.json()
            for t in tasks:
                # If we have a completed task for SMAP at these coordinates
                if t.get("status") == "done" and "smap" in t.get("task_name", "").lower():
                    task_id = t.get("task_id")
                    bundle_resp = requests.get(f"{BUNDLE_URL}/{task_id}", headers=headers, timeout=15)
                    if bundle_resp.status_code == 200:
                        files = bundle_resp.json().get("files", [])
                        # Locate CSV file in bundle
                        csv_file = next((f for f in files if f.get("file_name", "").endswith(".csv")), None)
                        if csv_file:
                            file_id = csv_file.get("file_id")
                            data_resp = requests.get(f"{BUNDLE_URL}/{task_id}/{file_id}", headers=headers, timeout=30)
                            if data_resp.status_code == 200:
                                parsed = parse_appeears_csv(data_resp.text, lat, lon, start_year, end_year)
                                parsed["metadata"]["source"] = "NASA_SMAP_APPEEARS"
                                parsed["metadata"]["is_sample_data"] = False
                                os.makedirs(cache_dir, exist_ok=True)
                                with open(cache_path, "w", encoding="utf-8") as cf:
                                    json.dump(parsed, cf, indent=2)
                                return parsed

            # Check if there is already a queued or processing task
            active_task = next(
                (t for t in tasks if t.get("status") in ["queued", "processing", "pending"] and "smap" in t.get("task_name", "").lower()),
                None
            )

            if not active_task:
                # Submit a point extraction task for SMAP SPL4SMGP.008
                payload = {
                    "task_type": "point",
                    "task_name": f"field_shift_smap_{int(lat*100)}_{int(lon*100)}",
                    "params": {
                        "dates": [{"startDate": f"01-01-{start_year}", "endDate": f"12-31-{end_year}"}],
                        "layers": [
                            {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_rootzone"},
                            {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_surface"}
                        ],
                        "coordinates": [{"id": "farm_location", "latitude": lat, "longitude": lon}]
                    }
                }
                sub_resp = requests.post(TASK_URL, json=payload, headers=headers, timeout=15)
                task_info = sub_resp.json() if sub_resp.status_code in [200, 201, 202] else {}
                active_id = task_info.get("task_id", "submitted")
            else:
                active_id = active_task.get("task_id")

            # AppEEARS processes tasks in a cloud queue which can take a few minutes.
            # While it processes, provide the labeled sample data so execution is not blocked.
            return load_sample_smap_data(
                reason=(
                    f"NASA AppEEARS task is currently queued/processing on NASA's servers (Task ID: {active_id}). "
                    "Serving verified offline sample data for Kamrup, Assam in the meantime."
                ),
                sample_dir=sample_dir
            )

    except requests.exceptions.RequestException as e:
        return load_sample_smap_data(
            reason=f"Network request to NASA AppEEARS failed ({type(e).__name__}: {e}). Using sample data.",
            sample_dir=sample_dir
        )

    return load_sample_smap_data(
        reason="AppEEARS point sampling pending. Using verified sample baseline.",
        sample_dir=sample_dir
    )


def parse_appeears_csv(csv_text: str, lat: float, lon: float, start_year: int, end_year: int) -> Dict[str, Any]:
    """Parse extracted AppEEARS CSV content into monthly soil moisture records."""
    import io
    import pandas as pd

    df = pd.read_csv(io.StringIO(csv_text))
    # Extract date and moisture columns
    date_col = next((c for c in df.columns if "date" in c.lower()), df.columns[0])
    root_col = next((c for c in df.columns if "rootzone" in c.lower()), None)
    surf_col = next((c for c in df.columns if "surface" in c.lower()), None)

    df["dt"] = pd.to_datetime(df[date_col])
    df["year"] = df["dt"].dt.year
    df["month"] = df["dt"].dt.month

    monthly = df.groupby(["year", "month"]).agg({
        root_col: "mean" if root_col else lambda x: 0.25,
        surf_col: "mean" if surf_col else lambda x: 0.20,
    }).reset_index()

    records = []
    for _, row in monthly.iterrows():
        y = int(row["year"])
        m = int(row["month"])
        rz = round(float(row[root_col]), 3) if root_col else 0.25
        sf = round(float(row[surf_col]), 3) if surf_col else 0.20
        records.append({
            "date": f"{y}-{m:02d}",
            "year": y,
            "month": m,
            "sm_rootzone_m3m3": rz,
            "sm_surface_m3m3": sf,
            "sm_rootzone_wetness": round(min(1.0, rz / 0.45), 3),
            "sm_surface_wetness": round(min(1.0, sf / 0.45), 3),
        })

    avg_root = round(sum(r["sm_rootzone_m3m3"] for r in records) / len(records), 3) if records else 0.0
    avg_surf = round(sum(r["sm_surface_m3m3"] for r in records) / len(records), 3) if records else 0.0

    return {
        "metadata": {
            "dataset": "NASA SMAP (SPL4SMGP.008)",
            "product": "SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture",
            "latitude": lat,
            "longitude": lon,
            "start_year": start_year,
            "end_year": end_year,
            "total_months": len(records),
            "is_sample_data": False,
            "units": {
                "sm_surface_m3m3": "m^3/m^3 (volumetric water content in top 0-5 cm)",
                "sm_rootzone_m3m3": "m^3/m^3 (volumetric water content in root zone 0-100 cm)",
                "wetness": "0 to 1 (relative saturation)"
            }
        },
        "summary": {
            "mean_rootzone_moisture_m3m3": avg_root,
            "mean_surface_moisture_m3m3": avg_surf,
            "min_rootzone_moisture_m3m3": min(r["sm_rootzone_m3m3"] for r in records) if records else 0.0,
            "max_rootzone_moisture_m3m3": max(r["sm_rootzone_m3m3"] for r in records) if records else 0.0
        },
        "monthly_records": records
    }


def print_smap_summary(data: Dict[str, Any]):
    """Print an easy-to-read terminal summary of the SMAP soil moisture data."""
    meta = data["metadata"]
    summary = data["summary"]
    records = data["monthly_records"]

    is_sample = meta.get("is_sample_data", False)
    badge = "[SAMPLE DATA]" if is_sample else "[REAL NASA DATA]"

    print("=" * 65)
    print(f" FIELD SHIFT - NASA SMAP SOIL MOISTURE SUMMARY {badge}")
    print("=" * 65)
    print(f" Region         : Lat {meta['latitude']} N, Lon {meta['longitude']} E (Kamrup, Assam)")
    print(f" Time Period    : {meta['start_year']} to {meta['end_year']} ({meta['total_months']} monthly records)")
    print(f" Data Source    : {meta.get('source')} {badge}")
    if is_sample and "reason" in meta:
        print(f" Status Reason  : {meta['reason']}")
    print("-" * 65)
    print(" SOIL MOISTURE METRICS (Volumetric Water Content):")
    print(f"   * Mean Root Zone Moisture (0-100cm) : {summary['mean_rootzone_moisture_m3m3']} m3/m3")
    print(f"   * Mean Surface Moisture (0-5cm)     : {summary['mean_surface_moisture_m3m3']} m3/m3")
    print(f"   * Root Zone Min / Max               : {summary['min_rootzone_moisture_m3m3']} / {summary['max_rootzone_moisture_m3m3']} m3/m3")
    if "dry_season_avg_m3m3" in summary:
        print(f"   * Dry Season Average (Dec-Mar)      : {summary['dry_season_avg_m3m3']} m3/m3")
        print(f"   * Monsoon Season Average (Jun-Sep)   : {summary['monsoon_season_avg_m3m3']} m3/m3")
    print("-" * 65)
    print(" SAMPLE MONTHLY DATA (First 3 and Last 3 records):")
    sample_rows = records[:3] + records[-3:]
    print(f"   {'Date':<10} | {'Root Zone (m3/m3)':<18} | {'Surface (m3/m3)':<16} | {'Saturation':<10}")
    print("   " + "-" * 60)
    for r in sample_rows:
        rz = f"{r['sm_rootzone_m3m3']:.3f}"
        sf = f"{r['sm_surface_m3m3']:.3f}"
        wet = f"{int(r['sm_rootzone_wetness'] * 100)}%"
        print(f"   {r['date']:<10} | {rz:<18} | {sf:<16} | {wet:<10}")
    print("=" * 65)


if __name__ == "__main__":
    print("Connecting to NASA Earthdata and fetching SMAP soil moisture data...")
    data = fetch_smap_data(lat=DEFAULT_LAT, lon=DEFAULT_LON)
    print_smap_summary(data)
