"""Slice 3: the reachability statistic behind the AI-vs-raw decision check.

Synthetic grids here test the plumbing only (connectivity logic), per the
no-dummy-data rule's unit-test exception.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from corrected_forecast import ICE_LIMIT, reachable  # noqa: E402


def grid(n=20):
    d2 = np.full((n, n), 200.0)  # neither near (<=50) nor far (>=400)
    d2[0, 0] = 10.0              # "station" corner
    d2[-1, -1] = 500.0           # the only "open water" cell
    return d2


def test_open_path_is_reachable():
    d2 = grid()
    sic = np.zeros_like(d2)
    assert reachable(sic, d2)


def test_ice_belt_blocks():
    d2 = grid()
    sic = np.zeros_like(d2)
    sic[5, :] = ICE_LIMIT + 0.1      # solid over-limit band between corners
    assert not reachable(sic, d2)


def test_nan_band_blocks_too():
    d2 = grid()
    sic = np.zeros_like(d2)
    sic[5, :] = np.nan               # no-data is not passable
    assert not reachable(sic, d2)


def test_vessel_limit_pin():
    # corrected_forecast.py hardcodes the router's default; keep them equal
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sim.router import VesselModel
    assert VesselModel().ice_limit == ICE_LIMIT
