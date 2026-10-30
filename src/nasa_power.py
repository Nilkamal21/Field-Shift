"""
nasa_power.py
-------------
Fetches and processes 10 years of monthly weather data from NASA POWER API.
Parameters:
  - T2M: Mean Temperature at 2 Meters (°C)
  - PRECTOTCORR: Corrected Precipitation / Rainfall (mm/day)
  - ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Irradiance (MJ/m^2/day)

Source: NASA POWER API (https://power.larc.nasa.gov/)
Free, public access (no Earthdata login required).
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# NASA POWER monthly point API endpoint
POWER_API_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

# Default target location: Kamrup district, Assam, India
DEFAULT_LAT = 26.18
DEFAULT_LON = 91.75
DEFAULT_START_YEAR = 2015
DEFAULT_END_YEAR = 2024


def get_cache_filepath(lat: float, lon: float, start_year: int, end_year: int, cache_dir: str = "cache") -> Path:
    """Generate a consistent cache file path based on coordinates and years."""
    filename = f"power_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json"
    return Path(cache_dir) / filename


def fetch_power_data(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    start_year: int = DEFAULT_START_YEAR,
    end_year: int = DEFAULT_END_YEAR,
    cache_dir: str = "cache",
    use_cache: bool = True,
    sample_dir: str = "data/sample"
) -> Dict[str, Any]:
    """
    Fetch 10 years of monthly weather data from NASA POWER for a given lat/lon.

    Returns a structured dictionary containing:
      - metadata (coordinates, period, source: 'NASA_POWER_API' | 'LOCAL_CACHE' | 'SAMPLE_DATA')
      - monthly_records (list of monthly dicts: date, year, month, temperature_c, rainfall_mm_day, solar_radiation_mj)
      - summary (annual and multi-year averages)
    """
    cache_path = get_cache_filepath(lat, lon, start_year, end_year, cache_dir)
    sample_path = Path(sample_dir) / "power_sample.json"

    # Step 1: Check local cache first if caching is enabled
    if use_cache and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["metadata"]["source"] = "LOCAL_CACHE"
                data["metadata"]["cache_file"] = str(cache_path)
                return data
        except (json.JSONDecodeError, IOError):
            # Corrupted cache file, ignore and fetch fresh data
            pass

    # Step 2: Fetch live data from NASA POWER API
    params = {
        "parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
        "community": "AG",  # Agroclimatology
        "longitude": lon,
        "latitude": lat,
        "start": str(start_year),
        "end": str(end_year),
        "format": "JSON",
    }

    try:
        response = requests.get(POWER_API_URL, params=params, timeout=30)
        response.raise_for_status()
        raw_json = response.json()

        # Step 3: Parse raw NASA POWER JSON into clean structure
        parsed_data = parse_power_response(raw_json, lat, lon, start_year, end_year)
        parsed_data["metadata"]["source"] = "NASA_POWER_API"

        # Step 4: Save to cache
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=2)

        # Also store as sample data baseline if not already present
        if not sample_path.exists():
            os.makedirs(sample_dir, exist_ok=True)
            with open(sample_path, "w", encoding="utf-8") as sf:
                sample_copy = json.loads(json.dumps(parsed_data))
                sample_copy["metadata"]["source"] = "SAMPLE_DATA"
                sample_copy["metadata"]["note"] = "NASA POWER recorded baseline for Kamrup, Assam"
                json.dump(sample_copy, sf, indent=2)

        return parsed_data

    except (requests.exceptions.RequestException, KeyError, ValueError) as err:
        # Step 5: Fallback to sample data if live fetch fails and cache is unavailable
        if sample_path.exists():
            try:
                with open(sample_path, "r", encoding="utf-8") as sf:
                    sample_data = json.load(sf)
                    sample_data["metadata"]["source"] = "SAMPLE_DATA"
                    sample_data["metadata"]["warning"] = (
                        f"Live NASA POWER fetch failed ({type(err).__name__}: {err}). "
                        "Serving verified offline sample data for Kamrup, Assam."
                    )
                    return sample_data
            except Exception:
                pass

        # If even sample data is not present, re-raise with clear explanation
        raise RuntimeError(
            f"Failed to fetch data from NASA POWER ({err}) and no cache or sample data file was found."
        )


def parse_power_response(
    raw_json: Dict[str, Any],
    lat: float,
    lon: float,
    start_year: int,
    end_year: int
) -> Dict[str, Any]:
    """Parse raw NASA POWER JSON into monthly records and clean summary metrics."""
    prop_params = raw_json.get("properties", {}).get("parameter", {})

    t2m_dict = prop_params.get("T2M", {})
    rain_dict = prop_params.get("PRECTOTCORR", {})
    solar_dict = prop_params.get("ALLSKY_SFC_SW_DWN", {})

    monthly_records = []
    temps = []
    rains = []
    solars = []

    # NASA keys are formatted as YYYYMM (e.g., '201501')
    # Keys ending in '13' (e.g., '201513') represent NASA's annual aggregate and are excluded from monthly series.
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            key = f"{year}{month:02d}"

            # NASA uses -999.0 or -99.0 for missing data
            t_val = t2m_dict.get(key)
            r_val = rain_dict.get(key)
            s_val = solar_dict.get(key)

            temp_c = None if (t_val is None or t_val <= -99.0) else round(float(t_val), 2)
            rain_mm = None if (r_val is None or r_val < 0) else round(float(r_val), 2)
            solar_mj = None if (s_val is None or s_val <= -99.0) else round(float(s_val), 2)

            if temp_c is not None:
                temps.append(temp_c)
            if rain_mm is not None:
                rains.append(rain_mm)
            if solar_mj is not None:
                solars.append(solar_mj)

            monthly_records.append({
                "date": f"{year}-{month:02d}",
                "year": year,
                "month": month,
                "temperature_c": temp_c,
                "rainfall_mm_day": rain_mm,
                "solar_radiation_mj": solar_mj
            })

    # Summary statistics
    avg_temp = round(sum(temps) / len(temps), 2) if temps else None
    min_temp = round(min(temps), 2) if temps else None
    max_temp = round(max(temps), 2) if temps else None

    avg_rain_day = round(sum(rains) / len(rains), 2) if rains else None
    est_annual_rain = round(avg_rain_day * 365.25, 1) if avg_rain_day else None

    avg_solar = round(sum(solars) / len(solars), 2) if solars else None

    return {
        "metadata": {
            "dataset": "NASA POWER (Agroclimatology)",
            "latitude": lat,
            "longitude": lon,
            "start_year": start_year,
            "end_year": end_year,
            "total_months": len(monthly_records),
            "units": {
                "temperature": "°C (monthly mean at 2m)",
                "rainfall": "mm/day (monthly mean daily precipitation)",
                "solar_radiation": "MJ/m^2/day (monthly mean daily irradiance)"
            }
        },
        "summary": {
            "mean_temperature_c": avg_temp,
            "min_monthly_temp_c": min_temp,
            "max_monthly_temp_c": max_temp,
            "mean_rainfall_mm_day": avg_rain_day,
            "est_annual_rainfall_mm": est_annual_rain,
            "mean_solar_radiation_mj": avg_solar
        },
        "monthly_records": monthly_records
    }


def print_power_summary(data: Dict[str, Any]):
    """Print an easy-to-read summary of NASA POWER data in the terminal."""
    meta = data["metadata"]
    summary = data["summary"]
    records = data["monthly_records"]

    print("=" * 65)
    print(" FIELD SHIFT - NASA POWER WEATHER DATA SUMMARY")
    print("=" * 65)
    print(f" Region         : Lat {meta['latitude']} N, Lon {meta['longitude']} E (Kamrup, Assam)")
    print(f" Time Period    : {meta['start_year']} to {meta['end_year']} (10 Years, {meta['total_months']} months)")
    print(f" Data Source    : {meta.get('source', 'NASA_POWER_API')}")
    if "warning" in meta:
        print(f" Note           : {meta['warning']}")
    print("-" * 65)
    print(" CLIMATE METRICS (10-Year Averages):")
    print(f"   * Average Temperature : {summary['mean_temperature_c']} C")
    print(f"     - Coolest Month     : {summary['min_monthly_temp_c']} C")
    print(f"     - Warmest Month     : {summary['max_monthly_temp_c']} C")
    print(f"   * Average Daily Rain  : {summary['mean_rainfall_mm_day']} mm/day")
    print(f"   * Estimated Annual    : {summary['est_annual_rainfall_mm']} mm/year")
    print(f"   * Solar Radiation     : {summary['mean_solar_radiation_mj']} MJ/m2/day")
    print("-" * 65)
    print(" SAMPLE MONTHLY DATA (First 3 and Last 3 records):")
    sample_rows = records[:3] + records[-3:]
    print(f"   {'Date':<10} | {'Temp (C)':<12} | {'Rain (mm/day)':<15} | {'Solar (MJ/m2)':<12}")
    print("   " + "-" * 57)
    for r in sample_rows:
        t_str = f"{r['temperature_c']:.2f}" if r['temperature_c'] is not None else "N/A"
        rn_str = f"{r['rainfall_mm_day']:.2f}" if r['rainfall_mm_day'] is not None else "N/A"
        s_str = f"{r['solar_radiation_mj']:.2f}" if r['solar_radiation_mj'] is not None else "N/A"
        print(f"   {r['date']:<10} | {t_str:<12} | {rn_str:<15} | {s_str:<12}")
    print("=" * 65)


if __name__ == "__main__":
    print("Fetching NASA POWER weather data for Kamrup, Assam...")
    data = fetch_power_data(lat=DEFAULT_LAT, lon=DEFAULT_LON)
    print_power_summary(data)
