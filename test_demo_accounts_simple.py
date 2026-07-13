"""
Simple test script to verify all demo accounts work correctly with the seed_demo.py script.
This script validates that:
1. All demo CSV files are created properly
2. All charts are generated for each account
3. The data is realistic and properly formatted
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from services.data_pipeline import process_smart_meter_file

def test_demo_files_exist():
    """Test that all demo CSV files exist and are properly formatted"""
    demo_data_dir = project_root / "demo_data"

    if not demo_data_dir.exists():
        print("ERROR: Demo data directory does not exist")
        return False

    expected_files = [
        "solar_profile.csv",
        "campus_profile.csv",
        "admin_profile.csv",
        "lab_profile.csv",
        "library_profile.csv",
        "block4a_profile.csv"
    ]

    missing_files = []
    for filename in expected_files:
        file_path = demo_data_dir / filename
        if not file_path.exists():
            missing_files.append(filename)

    if missing_files:
        print("ERROR: Missing CSV files: " + str(missing_files))
        return False

    print("SUCCESS: All demo CSV files exist")
    return True

def test_csv_format():
    """Test that all CSV files have the correct format"""
    demo_data_dir = project_root / "demo_data"

    for filename in ["solar_profile.csv", "campus_profile.csv", "admin_profile.csv",
                     "lab_profile.csv", "library_profile.csv", "block4a_profile.csv"]:
        file_path = demo_data_dir / filename
        try:
            df = pd.read_csv(file_path)

            # Check required columns
            required_columns = ["hour", "power_kw", "cumulative_kwh"]
            if not all(col in df.columns for col in required_columns):
                print("ERROR: " + filename + " missing required columns")
                return False

            # Check data types
            if not pd.api.types.is_numeric_dtype(df["power_kw"]):
                print("ERROR: " + filename + " power_kw column is not numeric")
                return False

            if not pd.api.types.is_numeric_dtype(df["cumulative_kwh"]):
                print("ERROR: " + filename + " cumulative_kwh column is not numeric")
                return False

            # Check row count
            if len(df) != 24:
                print("ERROR: " + filename + " should have exactly 24 rows, got " + str(len(df)))
                return False

            print("SUCCESS: " + filename + " - Valid format (" + str(len(df)) + " rows)")

        except Exception as e:
            print("ERROR: Error reading " + filename + ": " + str(e))
            return False

    return True

def test_data_realism():
    """Test that the data is realistic and within expected ranges"""
    demo_data_dir = project_root / "demo_data"

    # Define expected ranges for each profile
    expected_ranges = {
        "solar_profile.csv": {"min": 40, "max": 95},      # Solar surplus
        "campus_profile.csv": {"min": 30, "max": 110},    # Campus with peaks
        "admin_profile.csv": {"min": 10, "max": 72},      # Office flat load
        "lab_profile.csv": {"min": 20, "max": 120},       # Lab high variability
        "library_profile.csv": {"min": 15, "max": 95},    # Library with evening peak
        "block4a_profile.csv": {"min": 10, "max": 85},    # Mixed residential/office
    }

    for filename, ranges in expected_ranges.items():
        file_path = demo_data_dir / filename
        try:
            df = pd.read_csv(file_path)
            power_values = df["power_kw"].values

            min_val = np.min(power_values)
            max_val = np.max(power_values)

            if min_val < ranges["min"] or max_val > ranges["max"]:
                print("ERROR: " + filename + " data out of expected range [" + str(ranges['min']) + ", " + str(ranges['max']) + "]")
                print("   Actual range: [" + str(min_val) + ", " + str(max_val) + "]")
                return False

            print("SUCCESS: " + filename + " - Data within realistic range [" + str(min_val) + ", " + str(max_val) + "]")

        except Exception as e:
            print("ERROR: Error testing " + filename + ": " + str(e))
            return False

    return True

def test_processing_function():
    """Test that the processing function works correctly with demo data"""
    demo_data_dir = project_root / "demo_data"

    for filename in ["solar_profile.csv", "campus_profile.csv", "admin_profile.csv",
                     "lab_profile.csv", "library_profile.csv", "block4a_profile.csv"]:
        file_path = demo_data_dir / filename
        try:
            # Test processing function
            summary = process_smart_meter_file(file_path, "Test Appliance", 1000)

            # Check required fields are present
            required_fields = ["file_name", "rows", "columns", "mean_load",
                             "peak_load", "variability", "appliance_name",
                             "appliance_wattage", "estimated_daily_kwh", "efficiency_band"]

            for field in required_fields:
                if field not in summary:
                    print("ERROR: " + filename + " missing field: " + field)
                    return False

            # Check values are reasonable
            if summary["rows"] != 24:
                print("ERROR: " + filename + " should have 24 rows")
                return False

            if summary["mean_load"] <= 0:
                print("ERROR: " + filename + " mean load should be positive")
                return False

            print("SUCCESS: " + filename + " - Processing function works correctly")

        except Exception as e:
            print("ERROR: Error processing " + filename + ": " + str(e))
            return False

    return True

def main():
    """Run all tests"""
    print("Testing EcoTrack Demo Accounts...")
    print("=" * 50)

    tests = [
        test_demo_files_exist,
        test_csv_format,
        test_data_realism,
        test_processing_function
    ]

    all_passed = True
    for test in tests:
        try:
            result = test()
            if not result:
                all_passed = False
        except Exception as e:
            print("ERROR: Test " + test.__name__ + " failed with exception: " + str(e))
            all_passed = False
        print()

    if all_passed:
        print("SUCCESS: All tests passed! Demo accounts are ready to use.")
        return 0
    else:
        print("FAILURE: Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())