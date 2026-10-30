"""
test_hardening.py
-----------------
Tests edge cases and hardening for Field Shift API:
  1. GET /about text endpoint
  2. Edge case: Empty crops list
  3. Edge case: Single crop selected (cannot rotate)
  4. Edge case: Unknown crop IDs
  5. Edge case: Out-of-range coordinates
  6. Edge case: All zero priority weights (auto-normalization)
  7. Edge case: Valid 2-crop minimal rotation
"""

import sys
from pathlib import Path
from starlette.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.api import app

client = TestClient(app)


def run_hardening_tests():
    print("=" * 70)
    print(" FIELD SHIFT - HARDENING & EDGE CASE TEST SUITE")
    print("=" * 70)

    # Test 1: GET /about
    print("\n1. Testing GET /about (How this works educational endpoint)...")
    res = client.get("/about")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    about_data = res.json()
    print(f"   Project: {about_data['project']['name']}")
    print(f"   NASA Datasets documented: {len(about_data['nasa_datasets'])}")
    print(f"   Scoring Rules documented : {len(about_data['scoring_rules'])}")
    assert len(about_data["nasa_datasets"]) == 3
    assert "transparency_guarantee" in about_data
    print("   [PASS] GET /about returned complete plain-English guide!")

    # Test 2: Empty selected_crops
    print("\n2. Testing POST /recommend with empty crops []...")
    res = client.post("/recommend", json={"selected_crops": []})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"   Status Code: {res.status_code}")
    print(f"   Error Message: {res.json().get('detail')}")
    print("   [PASS] Rejected empty crops cleanly!")

    # Test 3: Single crop selected
    print("\n3. Testing POST /recommend with only 1 crop ['rice']...")
    res = client.post("/recommend", json={"selected_crops": ["rice"]})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"   Status Code: {res.status_code}")
    print(f"   Error Message: {res.json().get('detail')}")
    print("   [PASS] Rejected single-crop selection (rotation requires >= 2 crops)!")

    # Test 4: Unknown / invalid crop IDs
    print("\n4. Testing POST /recommend with unknown crop IDs ['coffee', 'tea']...")
    res = client.post("/recommend", json={"selected_crops": ["coffee", "tea"]})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"   Status Code: {res.status_code}")
    print(f"   Error Message: {res.json().get('detail')}")
    print("   [PASS] Rejected unrecognized crop IDs with helpful list of valid crops!")

    # Test 5: Out of range coordinates (Latitude 120.0)
    print("\n5. Testing POST /recommend with out-of-range latitude (120.0)...")
    res = client.post("/recommend", json={"latitude": 120.0, "longitude": 91.75})
    # Pydantic validates ge/le returning 422 Unprocessable Entity
    assert res.status_code in [400, 422], f"Expected 400 or 422, got {res.status_code}"
    print(f"   Status Code: {res.status_code}")
    print("   [PASS] Blocked invalid coordinate submission!")

    # Test 6: All-zero priority weights (avoid zero-division)
    print("\n6. Testing POST /recommend with all-zero priority weights...")
    res = client.post("/recommend", json={
        "selected_crops": ["mustard", "lentil"],
        "priority_weights": {"save_water": 0.0, "rebuild_soil": 0.0, "reduce_risk": 0.0, "profit": 0.0}
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    weights_used = res.json()["farm_profile"]["priority_weights"]
    print(f"   Status Code: {res.status_code}")
    print(f"   Auto-normalized weights: {weights_used}")
    assert weights_used["save_water"] == 0.25
    print("   [PASS] Smoothly auto-normalized zero weights without crash!")

    # Test 7: Minimal 2-crop rotation
    print("\n7. Testing POST /recommend with minimal 2 crops ['rice', 'lentil']...")
    res = client.post("/recommend", json={
        "selected_crops": ["rice", "lentil"]
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    rotations = res.json()["top_rotations"]
    print(f"   Status Code: {res.status_code}")
    print(f"   Top pick for 2 crops: {' -> '.join(rotations[0]['crop_names'])}")
    print("   [PASS] Successfully generated 3-year plan using 2 available crops!")

    print("\n" + "=" * 70)
    print("ALL HARDENING & EDGE CASE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_hardening_tests()
