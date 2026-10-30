"""
test_crops.py
-------------
Validates data/crops.json structure, required fields, and agronomic values.
"""

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CROPS_FILE = BASE_DIR / "data" / "crops.json"

REQUIRED_FIELDS = [
    "id",
    "name",
    "category",
    "season",
    "water_need",
    "water_requirement_mm_est",
    "heat_tolerance",
    "drought_tolerance",
    "root_type",
    "nitrogen_role",
    "soil_effect",
    "profit_potential_est",
    "notes"
]

VALID_WATER_NEEDS = ["low", "medium", "high"]
VALID_TOLERANCES = ["low", "medium", "high"]
VALID_NITROGEN_ROLES = ["heavy_feeder", "neutral", "fixer"]


def validate_crop_database():
    print("=" * 70)
    print(" FIELD SHIFT - CROP DATABASE VERIFICATION")
    print("=" * 70)

    if not CROPS_FILE.exists():
        print(f"FAILED: {CROPS_FILE} does not exist!")
        sys.exit(1)

    with open(CROPS_FILE, "r", encoding="utf-8") as f:
        crops = json.load(f)

    print(f"Loaded {len(crops)} crops from {CROPS_FILE.name}")
    print("-" * 70)

    expected_crop_ids = {"rice", "mustard", "lentil", "potato", "jute"}
    found_ids = set()

    for idx, crop in enumerate(crops, 1):
        cid = crop.get("id")
        found_ids.add(cid)
        cname = crop.get("name")
        print(f"{idx}. [{cid.upper()}] {cname}")

        # Check required fields
        missing = [rf for rf in REQUIRED_FIELDS if rf not in crop]
        if missing:
            print(f"   ERROR: Missing required fields: {missing}")
            sys.exit(1)

        # Check valid enum values
        assert crop["water_need"] in VALID_WATER_NEEDS, f"Invalid water_need: {crop['water_need']}"
        assert crop["heat_tolerance"] in VALID_TOLERANCES, f"Invalid heat_tolerance: {crop['heat_tolerance']}"
        assert crop["drought_tolerance"] in VALID_TOLERANCES, f"Invalid drought_tolerance: {crop['drought_tolerance']}"
        assert crop["nitrogen_role"] in VALID_NITROGEN_ROLES, f"Invalid nitrogen_role: {crop['nitrogen_role']}"

        print(f"   Season: {crop['season']} | Water: {crop['water_need']} (~{crop['water_requirement_mm_est']} mm)")
        print(f"   Root: {crop['root_type']} | N-Role: {crop['nitrogen_role']} | Heat/Drought: {crop['heat_tolerance']}/{crop['drought_tolerance']}")
        print(f"   Soil Impact: {crop['soil_effect']}")
        print()

    missing_crops = expected_crop_ids - found_ids
    if missing_crops:
        print(f"FAILED: Missing expected crops: {missing_crops}")
        sys.exit(1)

    print("-" * 70)
    print("SUCCESS: All 5 crops verified with complete agronomic attributes!")
    print("=" * 70)


if __name__ == "__main__":
    validate_crop_database()
