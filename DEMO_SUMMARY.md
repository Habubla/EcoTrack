# EcoTrack Demo Accounts Summary

## Overview
This enhancement adds six realistic demo accounts to EcoTrack with pre-generated data and charts for easy presentation and demonstration purposes.

## Demo Accounts Created

1. **demo_solar** - Solar-rich building, surplus all day (APJ Complex)
2. **demo_campus** - High-variability campus block, evening peak (Block 5)  
3. **demo_admin** - Flat office load, very efficient (Admin)
4. **demo_lab** - High variability laboratory loads (Block 6)
5. **demo_library** - Steady load with evening peak (Library)
6. **demo_block4a** - Mixed residential and office loads (Block 4A)

## Files Generated

### CSV Data Files
- `demo_data/solar_profile.csv`
- `demo_data/campus_profile.csv` 
- `demo_data/admin_profile.csv`
- `demo_data/lab_profile.csv`
- `demo_data/library_profile.csv`
- `demo_data/block4a_profile.csv`

### Chart Images
- `static/images/demo_solar_production_vs_consumption.png`
- `static/images/demo_solar_load_distribution.png`
- `static/images/demo_campus_production_vs_consumption.png`
- `static/images/demo_campus_load_distribution.png`
- `static/images/demo_admin_production_vs_consumption.png`
- `static/images/demo_admin_load_distribution.png`
- `static/images/demo_lab_production_vs_consumption.png`
- `static/images/demo_lab_load_distribution.png`
- `static/images/demo_library_production_vs_consumption.png`
- `static/images/demo_library_load_distribution.png`
- `static/images/demo_block4a_production_vs_consumption.png`
- `static/images/demo_block4a_load_distribution.png`

## How to Use

1. Run the demo seeder: `python seed_demo.py`
2. Register the demo usernames on easy-auth.dev first
3. Log in as any demo account - charts appear immediately without upload step

## Features Added

- Enhanced data profiles with realistic energy consumption patterns
- Pre-generated charts for all accounts
- Comprehensive testing to verify all accounts work correctly
- Updated documentation in README.md
- Unicode-free scripts that work on all systems