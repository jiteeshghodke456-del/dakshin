"""CorrectedIceWorld: the delta really reaches the router's SIC samples.

Synthetic grids test the plumbing only, per the no-dummy-data rule's
unit-test exception.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

pyproj = pytest.importorskip("pyproj")
from real_route_run import CorrectedIceWorld  # noqa: E402


class FlatWorld:
    def sample(self, lat, lon, t):
        return {"sic": np.zeros(np.shape(lat)), "other": 7}

    n_days = 10


def make_npz(tmp_path):
    # Small south-polar patch; one lead whose delta is +0.5 everywhere.
    lat, lon = np.meshgrid(np.linspace(-70, -60, 8), np.linspace(60, 80, 9),
                           indexing="ij")
    raw = np.zeros_like(lat, dtype=np.float32)
    f = tmp_path / "c.npz"
    np.savez(f, lat=lat, lon=lon, raw_lead1=raw, corrected_lead1=raw + 0.5)
    return f


def test_delta_applied_and_passthrough(tmp_path):
    w = CorrectedIceWorld(FlatWorld(), make_npz(tmp_path))
    out = w.sample(np.array([[-65.0]]), np.array([[70.0]]), 1.0)
    assert out["sic"][0, 0] == pytest.approx(0.5)
    assert out["other"] == 7            # non-ice fields untouched
    assert w.n_days == 10               # attribute passthrough


def test_delta_clipped_to_valid_sic(tmp_path):
    class IcyWorld(FlatWorld):
        def sample(self, lat, lon, t):
            return {"sic": np.full(np.shape(lat), 0.9)}

    w = CorrectedIceWorld(IcyWorld(), make_npz(tmp_path))
    out = w.sample(np.array([-65.0]), np.array([70.0]), 1.0)
    assert out["sic"][0] == pytest.approx(1.0)   # 0.9 + 0.5 clips at 1
