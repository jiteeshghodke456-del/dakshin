"""IceField plumbing: it must sample sea ice exactly as CurrentField samples
currents, take day 0 of each cycle, and hold (and log) the nearest good day
where a cycle is stale. Synthetic fixtures test the plumbing only; the real
archive is exercised by scripts/berg_sil_hindcast.py."""
import datetime as dt

import numpy as np
import pytest
import xarray as xr

from berg_forecast import IceField, known_stale_dates

LAT = np.arange(-70.0, -64.9, 0.5)
LON = np.arange(10.0, 15.1, 0.5)
DAY0 = dt.date(2026, 9, 1)


def day_center(day):
    return np.datetime64(day).astype("datetime64[s]").astype(float) / 86400.0 + 0.5


def synthetic(n_days=3):
    """A rises 0.1 per degree of longitude and 0.1 per day; the rest constant."""
    shape = (n_days, len(LAT), len(LON))
    conc = np.zeros(shape, np.float32)
    for d in range(n_days):
        conc[d] = 0.1 * (LON - LON[0])[None, :] + 0.1 * d
    t = np.array([day_center(DAY0 + dt.timedelta(days=d)) for d in range(n_days)])
    return IceField(conc, np.full(shape, 1.5, np.float32),
                    np.full(shape, 0.2, np.float32),
                    np.full(shape, -0.1, np.float32), LAT, LON, t)


def test_sample_is_bilinear_in_space_and_linear_in_time():
    ice = synthetic()
    noon = dt.datetime(2026, 9, 1, 12)
    a, h, u, v = ice.sample(12.25, -67.25, noon)        # between grid points
    assert a == pytest.approx(0.225, abs=1e-6)
    assert (h, u, v) == pytest.approx((1.5, 0.2, -0.1), abs=1e-6)
    a_midnight = ice.sample(12.25, -67.25, noon + dt.timedelta(hours=12))[0]
    assert a_midnight == pytest.approx(0.275, abs=1e-6)  # half-way to day 2


def test_sample_refuses_to_invent_ice_next_to_missing_cells():
    ice = synthetic()
    ice._state.u[:, 4, 4] = np.nan                       # one concentration cell
    a, h, u, v = ice.sample(LON[4] + 0.1, LAT[4] + 0.1, dt.datetime(2026, 9, 1, 12))
    assert np.isnan(a)
    assert (h, u, v) == pytest.approx((1.5, 0.2, -0.1), abs=1e-6)
    assert np.isnan(ice.sample(99.0, -67.0, dt.datetime(2026, 9, 1, 12))).all()


def write_cycle(folder, day, conc0, first_time=None):
    """A two-step cycle file: day 0 holds conc0, day 1 holds a decoy value."""
    times = [np.datetime64(first_time or day) + np.timedelta64(i, "D") for i in range(2)]
    def var(value0, value1):
        data = np.stack([np.full((len(LAT), len(LON)), value0, np.float32),
                         np.full((len(LAT), len(LON)), value1, np.float32)])
        return (("time", "latitude", "longitude"), data)
    xr.Dataset(
        {"siconc": var(conc0, 0.99), "sithick": var(1.0, 9.0),
         "usi": var(0.1, 9.0), "vsi": var(0.0, 9.0)},
        coords={"time": np.array(times, "datetime64[ns]"),
                "latitude": LAT, "longitude": LON},
    ).to_netcdf(folder / f"cmems_siconc_{day}.nc")


def test_from_archive_uses_day_0_and_holds_nearest_good_day_for_stale(tmp_path):
    days = [DAY0 + dt.timedelta(days=i) for i in range(4)]
    for day, conc in zip(days, (0.2, 0.4, 0.6, 0.8)):
        write_cycle(tmp_path, day, conc)
    (tmp_path / "KNOWN_STALE.md").write_text(
        f"| `cmems_siconc_{days[1]}.nc` | stale |\n")

    ice = IceField.from_archive(tmp_path)
    assert ice.substituted == {days[1]: days[0]}         # tie -> the earlier day
    at_noon = [ice.sample(12.0, -67.0, dt.datetime(d.year, d.month, d.day, 12))[0]
               for d in days]
    assert at_noon == pytest.approx([0.2, 0.2, 0.6, 0.8], abs=1e-6)
    # thickness 1.0 is day 0; 9.0 would mean a forecast step leaked in
    assert ice.sample(12.0, -67.0, dt.datetime(2026, 9, 3, 12))[1] == pytest.approx(1.0)


def test_from_archive_rejects_a_file_whose_data_is_not_its_named_day(tmp_path):
    write_cycle(tmp_path, DAY0, 0.5, first_time=DAY0 + dt.timedelta(days=1))
    with pytest.raises(ValueError, match="first time step"):
        IceField.from_archive(tmp_path)


def test_known_stale_dates_reads_the_committed_note():
    assert known_stale_dates() == {dt.date(2026, 9, 20), dt.date(2026, 10, 11),
                                   dt.date(2026, 11, 10), dt.date(2026, 11, 17)}
