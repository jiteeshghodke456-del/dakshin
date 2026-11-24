#!/usr/bin/env python3
"""One figure for docs/SIL_EXPERIMENT.md, drawn only from the committed JSON.

    python scripts/plot_sil_experiment.py   # writes dakshin/figures/sil_experiment.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "dakshin" / "figures"
OUT = FIG / "sil_experiment.png"

INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
NEUTRAL = "#8a8983"          # reference bars: not one of the model variants
WDE17, CONC, PAPER = "#2a78d6", "#eb6834", "#1baf7a"   # fixed per variant, all panels


def bars(ax, labels, values, colors, fmt, title, note):
    y = range(len(labels))[::-1]
    ax.barh(list(y), values, height=0.52, color=colors, zorder=3)
    for yi, v in zip(y, values):
        ax.text(v + max(values) * 0.02, yi, fmt.format(v), va="center",
                fontsize=11, color=INK)
    ax.set_yticks(list(y), labels, fontsize=10.5, color=INK)
    ax.set_xlim(0, max(values) * 1.22)
    ax.set_title(title, fontsize=12, color=INK, loc="left", pad=10, weight="bold")
    ax.text(0, -0.2, note, transform=ax.transAxes, fontsize=9, color=MUTED, va="top")
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="#e4e3df", lw=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c9c8c2")
    ax.set_facecolor(SURFACE)


def main() -> int:
    hind = json.loads((FIG / "berg_sil_hindcast.json").read_text())
    drift = json.loads((FIG / "ice_drift_check.json").read_text())
    v = hind["variants_error_km_per_day"]
    near = drift["nominal_within_200km_of_a_hindcast_berg"]

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.3), facecolor=SURFACE)
    bars(axes[0],
         ["Locking on\nconcentration alone", "The paper's rule\n(strength scales\nwith berg mass)"],
         [round(100 * v["v3_sil"]["sil"]["fraction_hours_lambda_eq_1"], 1),
          round(100 * v["v5_sil_force_balance"]["sil"]["fraction_hours_lambda_eq_1"], 1)],
         [CONC, PAPER], "{:.1f} %", "1. How often the bergs are fully locked",
         "Share of about 14,400 berg-hours with lambda = 1.")
    bars(axes[1],
         ["Persistence\n(berg did not move)", "WDE17, no sea ice",
          "+ locking on\nconcentration alone", "+ the paper's rule"],
         [hind["persistence_km_per_day"]["moving"]["mean"], v["v1_wde17"]["moving"]["mean"],
          v["v3_sil"]["moving"]["mean"], v["v5_sil_force_balance"]["moving"]["mean"]],
         [NEUTRAL, WDE17, CONC, PAPER], "{:.2f}", "2. Landing error on the 13 moving segments",
         "Mean, km/day. Lower is better. 9 of the 13 are one berg (C39).")
    bars(axes[2],
         ["Bergs that moved\n(weekly USNIC fixes)", "Observed sea ice within\n200 km (OSI SAF)",
          "CMEMS sea ice,\nsame points"],
         [hind["persistence_km_per_day"]["moving"]["mean"],
          near["observed_speed_km_per_day"]["mean"], near["model_speed_km_per_day"]["mean"]],
         [NEUTRAL, "#52514e", "#b3b2ab"], "{:.2f}", "3. The ice moves faster than the bergs",
         "Mean speed, km/day. The model ice is close to the observed ice.")
    fig.suptitle("Sea-ice locking (Marson et al. 2024) on 88 weekly segments of eight giant "
                 "Antarctic bergs, Sep to Nov 2026", fontsize=13, color=INK, x=0.012,
                 ha="left", y=1.02)
    fig.tight_layout(w_pad=3.0)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
