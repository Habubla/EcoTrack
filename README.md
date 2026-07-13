# EcoTrack

EcoTrack is an Energy Management System (EMS) Flask application for Electrical Engineering project evaluation.

## Core Pages

- Dashboard (`/`): Energy Overview KPIs and Matplotlib chart placeholders.
- Input / Upload (`/upload`): Smart Meter CSV upload and appliance wattage form (POST handling).
- Optimization Scheduler (`/optimization`): 24-hour electricity price cycle with "Best Time to Save" highlighted in green.
- Safety Alerts (`/alerts`): anomaly warnings generated from Python exceptions.

## Building Set

- APJ Complex
- Block 5
- Block 6
- Admin
- Library
- Block 4A
- SAC
- SC

## Demo Accounts

The demo seeder creates six accounts with realistic energy profiles:

1. `demo_solar` - Solar-rich building, surplus all day (APJ Complex)
2. `demo_campus` - High-variability campus block, evening peak (Block 5)
3. `demo_admin` - Flat office load, very efficient (Admin)
4. `demo_lab` - High variability laboratory loads (Block 6)
5. `demo_library` - Steady load with evening peak (Library)
6. `demo_block4a` - Mixed residential and office loads (Block 4A)

## Technical Notes

- Backend: Flask + Jinja2 templates
- Data processing structure: `services/data_pipeline.py`
	- Uses `pandas` and `numpy` for CSV processing and metrics extraction.
	- Uses `matplotlib` to save PNG chart placeholders into `static/images/`.
- Static assets: all CSS and generated chart images are under `static/`.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000
