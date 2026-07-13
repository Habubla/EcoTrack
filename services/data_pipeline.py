from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

DEFAULT_BUILDING_LOADS: dict[str, float] = {
    "APJ Complex": 128.4,
    "Block 5": 86.1,
    "Block 6": 78.3,
    "Admin": 49.7,
    "Library": 57.4,
    "Block 4A": 73.9,
    "SAC": 64.2,
    "SC": 52.8,
}

_PIE_PALETTE = [
    "#4FC3F7", "#29B6F6", "#03A9F4", "#039BE5",
    "#0288D1", "#0277BD", "#01579B", "#81D4FA",
]


def create_placeholder_charts(image_dir: Path) -> None:
    image_dir.mkdir(parents=True, exist_ok=True)
    hours = np.arange(24)
    production = 55 + 25 * np.sin((hours - 6) * np.pi / 12)
    consumption = 52 + 14 * np.sin((hours + 1) * np.pi / 12) + np.where(
        (hours >= 18) & (hours <= 22), 10, 0
    )
    _save_line_chart(
        image_dir / "placeholder_production_vs_consumption.png",
        hours, production, consumption,
        title="Production vs. Consumption (placeholder)",
    )
    _save_pie_chart(
        image_dir / "placeholder_load_distribution.png",
        list(DEFAULT_BUILDING_LOADS.keys()),
        list(DEFAULT_BUILDING_LOADS.values()),
        title="Load Distribution by Building (placeholder)",
    )


def generate_user_charts(
    file_path: Path,
    building_name: str,
    username: str,
    image_dir: Path,
    current_building_loads: dict[str, float] | None = None,
) -> int:
    """Regenerate both charts from the uploaded CSV for *username*.
    Returns a Unix timestamp for cache-busting."""
    image_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(file_path)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if numeric_cols:
        raw_vals = df[numeric_cols[0]].dropna().values.astype(float)
    else:
        raw_vals = np.ones(24) * 50.0

    if len(raw_vals) >= 24:
        consumption = raw_vals[:24]
    else:
        x_old = np.linspace(0, 1, len(raw_vals))
        x_new = np.linspace(0, 1, 24)
        consumption = np.interp(x_new, x_old, raw_vals)

    if consumption.max() > 2000:
        consumption = consumption / 1000.0
    elif consumption.max() < 0.5:
        consumption = consumption * 1000.0

    rng = np.random.default_rng(seed=int(abs(consumption.mean()) * 100) % (2 ** 31))
    production = consumption * (1.04 + rng.uniform(0.0, 0.08, 24))
    hours = np.arange(24)

    slug = _slug(username)
    _save_line_chart(
        image_dir / f"{slug}_production_vs_consumption.png",
        hours, production, consumption,
        title=f"Production vs. Consumption — {building_name}",
    )

    loads = dict(current_building_loads or DEFAULT_BUILDING_LOADS)
    loads[building_name] = round(float(consumption.mean()), 2)
    _save_pie_chart(
        image_dir / f"{slug}_load_distribution.png",
        list(loads.keys()),
        list(loads.values()),
        title=f"Load Distribution — Updated ({building_name})",
    )

    return int(datetime.now().timestamp())


def process_smart_meter_file(
    file_path: Path,
    appliance_name: str,
    appliance_wattage: float,
) -> dict:
    df = pd.read_csv(file_path)
    if df.empty:
        raise ValueError("CSV file has no rows.")

    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_columns:
        raise ValueError("CSV must include at least one numeric column.")

    numeric_values = df[numeric_columns].to_numpy(dtype=float)
    mean_load = float(np.mean(numeric_values))
    peak_load = float(np.max(numeric_values))
    variability = float(np.std(numeric_values))
    estimated_daily_kwh = (appliance_wattage * 8) / 1000
    efficiency_band = "Efficient" if estimated_daily_kwh < 3.5 else "Needs Optimization"

    return {
        "file_name": file_path.name,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "numeric_columns": numeric_columns,
        "mean_load": round(mean_load, 3),
        "peak_load": round(peak_load, 3),
        "variability": round(variability, 3),
        "appliance_name": appliance_name,
        "appliance_wattage": appliance_wattage,
        "estimated_daily_kwh": round(estimated_daily_kwh, 3),
        "efficiency_band": efficiency_band,
    }


def generate_price_cycle() -> list[dict]:
    hours = np.arange(24)
    rng = np.random.default_rng(seed=42)
    base_curve = 6.4 + 2.2 * np.sin((hours - 7) * np.pi / 12)
    evening_penalty = np.where((hours >= 18) & (hours <= 22), 2.7, 0)
    noise = rng.normal(0, 0.18, size=24)
    prices = np.round(base_curve + evening_penalty + noise, 2)
    return [
        {"hour": int(h), "hour_label": f"{h:02d}:00 - {(h+1)%24:02d}:00", "price_per_kwh": float(p)}
        for h, p in zip(hours, prices, strict=True)
    ]


def _save_line_chart(path, hours, production, consumption, title):
    fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=140)
    ax.plot(hours, production, label="Production", color="#42A5F5", linewidth=2.2)
    ax.plot(hours, consumption, label="Consumption", color="#FFCA28", linewidth=2.2)
    ax.fill_between(hours, production, consumption,
                    where=(production >= consumption),
                    alpha=0.08, color="#42A5F5")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Power (kW)")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _save_pie_chart(path, labels, values, title):
    fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=140)
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%", startangle=135,
        colors=_PIE_PALETTE[:len(values)],
        wedgeprops={"edgecolor": "#0C152B", "linewidth": 1},
        textprops={"fontsize": 8}, pctdistance=0.8,
    )
    for auto in autotexts:
        auto.set_color("#F8FBFF")
        auto.set_fontsize(7)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.axis("equal")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower())
