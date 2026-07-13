"""
EcoTrack — Demo Account Seeder
==============================
Run this ONCE from inside the EcoTrack-main folder before your presentation:

    python seed_demo.py

It will:
  1. Write three realistic CSV data files to  demo_data/
  2. Pre-generate all charts for each demo account into  static/images/

After running, just log in as any demo user and the dashboard charts
are already there — no upload step needed during the presentation.

Demo accounts (register these on easy-auth.dev first):
  ┌─────────────────┬──────────────────────────────────────────┐
  │ Username        │ Profile story                            │
  ├─────────────────┼──────────────────────────────────────────┤
  │ demo_solar      │ Solar-rich building, surplus all day     │
  │ demo_campus     │ High-variability campus block, eve peak  │
  │ demo_admin      │ Flat office load, very efficient         │
  └─────────────────┴──────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ── Adjust this if you run the script from outside EcoTrack-main ──────────
BASE_DIR = Path(__file__).resolve().parent
DEMO_DATA_DIR = BASE_DIR / "demo_data"
STATIC_IMAGE_DIR = BASE_DIR / "static" / "images"
# ──────────────────────────────────────────────────────────────────────────

# Import EcoTrack's own pipeline so charts are 100% identical to what
# the app would produce after a real upload.
import sys
sys.path.insert(0, str(BASE_DIR))
from services.data_pipeline import generate_user_charts, DEFAULT_BUILDING_LOADS


# ──────────────────────────────────────────────────────────────────────────
# 1.  Define the three demo profiles
# ──────────────────────────────────────────────────────────────────────────

hours = np.arange(24)

def _solar_profile() -> np.ndarray:
    """APJ Complex — rooftop solar array, large surplus midday."""
    base = 58 + 18 * np.sin((hours - 5) * np.pi / 13)   # slow morning ramp
    noise = np.random.default_rng(1).normal(0, 1.2, 24)
    return np.clip(base + noise, 40, 95)


def _campus_profile() -> np.ndarray:
    """Block 5 — heavy evening peak (labs, canteen, events)."""
    base = 45 + 10 * np.sin((hours - 8) * np.pi / 12)
    evening_spike = np.where((hours >= 17) & (hours <= 22), 30, 0)
    noise = np.random.default_rng(2).normal(0, 3.5, 24)
    return np.clip(base + evening_spike + noise, 30, 110)


def _admin_profile() -> np.ndarray:
    """Admin Block — flat office load, efficient, minimal after-hours."""
    base = 48 + 6 * np.sin((hours - 9) * np.pi / 8)
    after_hours = np.where((hours < 7) | (hours > 19), -25, 0)
    noise = np.random.default_rng(3).normal(0, 0.8, 24)
    return np.clip(base + after_hours + noise, 10, 72)


# Enhanced profiles with new features
def _lab_profile() -> np.ndarray:
    """Block 6 — high variability laboratory loads, peak during lab hours."""
    base = 55 + 15 * np.sin((hours - 7) * np.pi / 12)
    lab_peak = np.where((hours >= 10) & (hours <= 16), 35, 0)
    noise = np.random.default_rng(4).normal(0, 2.8, 24)
    return np.clip(base + lab_peak + noise, 20, 120)


def _library_profile() -> np.ndarray:
    """Library — steady load with evening peak."""
    base = 40 + 8 * np.sin((hours - 6) * np.pi / 10)
    evening_peak = np.where((hours >= 18) & (hours <= 22), 25, 0)
    noise = np.random.default_rng(5).normal(0, 2.2, 24)
    return np.clip(base + evening_peak + noise, 15, 95)


def _block_4a_profile() -> np.ndarray:
    """Block 4A — mixed residential and office loads."""
    base = 38 + 12 * np.sin((hours - 5) * np.pi / 14)
    evening_spike = np.where((hours >= 19) & (hours <= 23), 20, 0)
    noise = np.random.default_rng(6).normal(0, 1.8, 24)
    return np.clip(base + evening_spike + noise, 10, 85)


DEMO_ACCOUNTS: list[dict] = [
    {
        "username":     "demo_solar",
        "building":     "APJ Complex",
        "csv_filename": "solar_profile.csv",
        "values_fn":    _solar_profile,
        "appliance":    "Rooftop Solar Inverter",
        "wattage":      3500,
    },
    {
        "username":     "demo_campus",
        "building":     "Block 5",
        "csv_filename": "campus_profile.csv",
        "values_fn":    _campus_profile,
        "appliance":    "HVAC Central Unit",
        "wattage":      4200,
    },
    {
        "username":     "demo_admin",
        "building":     "Admin",
        "csv_filename": "admin_profile.csv",
        "values_fn":    _admin_profile,
        "appliance":    "Lighting & Workstations",
        "wattage":      1800,
    },
    {
        "username":     "demo_lab",
        "building":     "Block 6",
        "csv_filename": "lab_profile.csv",
        "values_fn":    _lab_profile,
        "appliance":    "Laboratory Equipment",
        "wattage":      3800,
    },
    {
        "username":     "demo_library",
        "building":     "Library",
        "csv_filename": "library_profile.csv",
        "values_fn":    _library_profile,
        "appliance":    "Library HVAC & Lighting",
        "wattage":      2500,
    },
    {
        "username":     "demo_block4a",
        "building":     "Block 4A",
        "csv_filename": "block4a_profile.csv",
        "values_fn":    _block_4a_profile,
        "appliance":    "Residential & Office Loads",
        "wattage":      2100,
    },
]


# ──────────────────────────────────────────────────────────────────────────
# 2.  Write CSV files
# ──────────────────────────────────────────────────────────────────────────

def write_csv(account: dict) -> Path:
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    values = account["values_fn"]()
    df = pd.DataFrame({
        "hour":              [f"{h:02d}:00" for h in hours],
        "power_kw":          np.round(values, 3),
        "cumulative_kwh":    np.round(np.cumsum(values), 3),
    })
    path = DEMO_DATA_DIR / account["csv_filename"]
    df.to_csv(path, index=False)
    return path


# ──────────────────────────────────────────────────────────────────────────
# 3.  Pre-generate charts for each account
# ──────────────────────────────────────────────────────────────────────────

def seed_charts(account: dict, csv_path: Path) -> None:
    generate_user_charts(
        file_path=csv_path,
        building_name=account["building"],
        username=account["username"],
        image_dir=STATIC_IMAGE_DIR,
        current_building_loads=dict(DEFAULT_BUILDING_LOADS),
    )


# ──────────────────────────────────────────────────────────────────────────
# 4.  Main
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    STATIC_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    print("\nEcoTrack demo seeder starting...\n")

    for account in DEMO_ACCOUNTS:
        username = account["username"]
        print(f"  [{username}]")

        csv_path = write_csv(account)
        print(f"    OK  CSV written  ->  {csv_path.relative_to(BASE_DIR)}")

        seed_charts(account, csv_path)
        slug = "".join(c if c.isalnum() else "_" for c in username.lower())
        for kind in ("production_vs_consumption", "load_distribution"):
            img = STATIC_IMAGE_DIR / f"{slug}_{kind}.png"
            status = "OK" if img.exists() else "MISSING"
            print(f"    {status}  chart  ->  static/images/{img.name}")
        print()

    print("DONE! All demo charts are ready.")
    print("   Log in as any demo account - charts appear immediately.\n")
    print("   Reminder: register these usernames on easy-auth.dev first:")
    for a in DEMO_ACCOUNTS:
        print(f"     -> {a['username']}")
    print()


if __name__ == "__main__":
    main()