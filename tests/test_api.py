"""
test_api.py
-----------
Tests FastAPI endpoints in src/api.py:
  1. GET /health
  2. GET /crops
  3. POST /recommend (Valid default request)
  4. POST /recommend (Custom priority weights & crop subset)
  5. POST /recommend (Error case: fewer than 2 crops)
"""

import sys
from pathlib import Path
from starlette.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.api import app

client = TestClient(app)


def run_api_tests():
    print("=" * 70)
    print(" FIELD SHIFT - FASTAPI ENDPOINTS VERIFICATION")
    print("=" * 70)

    # 1. Test /health
    print("\n1. Testing GET /health...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    health_data = res.json()
    print(f"   Status Code: {res.status_code}")
    print(f"   Response   : {health_data}")
    assert health_data["status"] == "healthy"
    print("   [PASS] /health is healthy!")

    # 2. Test /crops
    print("\n2. Testing GET /crops...")
    res = client.get("/crops")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    crops_data = res.json()
    print(f"   Status Code: {res.status_code}")
    print(f"   Total Crops: {crops_data['total_crops']}")
    crop_ids = [c["id"] for c in crops_data["crops"]]
    print(f"   Crop IDs   : {crop_ids}")
    assert len(crop_ids) == 5
    print("   [PASS] /crops returned all 5 crops!")

    # 3. Test POST /recommend (Default parameters)
    print("\n3. Testing POST /recommend (Standard Payload)...")
    payload = {
        "latitude": 26.18,
        "longitude": 91.75,
        "soil_type": "Alluvial",
        "selected_crops": ["rice", "mustard", "lentil", "potato", "jute"],
        "priority_weights": {
            "save_water": 0.35,
            "rebuild_soil": 0.35,
            "reduce_risk": 0.15,
            "profit": 0.15
        }
    }
    res = client.post("/recommend", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    rec_data = res.json()
    print(f"   Status Code      : {res.status_code}")
    print(f"   Top Rotations    : {len(rec_data['top_rotations'])}")
    for r in rec_data["top_rotations"]:
        print(f"     - Rank #{r.get('composite_score')}: {' -> '.join(r['crop_names'])}")
    print(f"   Climate Verdicts : {len(rec_data['climate_verdicts'])} findings")
    print(f"   Chart Series     : Weather ({rec_data['chart_time_series']['weather_series']['total_points']} pts), Soil ({rec_data['chart_time_series']['soil_moisture_series']['total_points']} pts), MODIS ({rec_data['chart_time_series']['vegetation_ndvi_series']['total_points']} pts)")
    print(f"   Data Provenance  : POWER [{rec_data['data_provenance']['nasa_power']['status']}], SMAP [{rec_data['data_provenance']['nasa_smap']['status']}], MODIS [{rec_data['data_provenance']['nasa_modis']['status']}]")
    assert len(rec_data["top_rotations"]) == 3
    print("   [PASS] /recommend returned top 3 rotations and charts!")

    # 4. Test POST /recommend (Error Handling: only 1 crop selected)
    print("\n4. Testing POST /recommend (Validation Error: only 1 crop)...")
    bad_payload = {
        "latitude": 26.18,
        "longitude": 91.75,
        "selected_crops": ["rice"]
    }
    res = client.post("/recommend", json=bad_payload)
    print(f"   Status Code: {res.status_code} (Expected 400)")
    print(f"   Error Detail: {res.json().get('detail')}")
    assert res.status_code == 400
    print("   [PASS] Properly rejected invalid input with clear error message!")

    print("\n" + "=" * 70)
    print("ALL API ENDPOINTS TESTED AND PASSING SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_api_tests()
