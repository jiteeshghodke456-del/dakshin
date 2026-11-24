"""Iceberg trajectory forecast (HANDOFF_TONIGHT slice 5).

Steps a berg forward on real ocean currents with midpoint (RK2) integration,
dt = 1 h, velocities from the WDE17 drift model (models/iceberg/drift.py).
Currents are interpolated bilinearly in space and linearly between daily means
(each daily mean is taken as valid at 12:00 UTC of its day; the half-days
outside the first and last centre use the nearest day).

Honesty rules, from the handoff:
- a step that lands on NaN current (land, or outside the data) marks the berg
  "grounded or unknown" and STOPS it — motion is never invented;
- wind defaults to zero, and each track records WDE17's R (relative wind
  forcing) computed with an assumed 10 m/s wind so the neglected term is
  visible. Measured on the 2026 corridor hindcast the median R is 0.25 with
  a maximum of 1.73 — the corridor's currents are slow enough that wind is
  NOT negligible for every berg, so zero-wind is a stated limitation here,
  not a safe approximation (see dakshin/figures/berg_hindcast.json).
"""
from __future__ import annotations

import datetime as dt
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.iceberg.drift import iceberg_velocity, relative_wind_forcing  # noqa: E402
from models.iceberg.sil import locking_force_per_width, sil_velocity  # noqa: E402

M_PER_DEG = 111_195.0  # mean metres per degree of latitude
STATUS_OK = "ok"
STATUS_GROUNDED = "grounded or unknown"

# Keel draught for grounding detection: USNIC publishes no thickness, so the
# assumed 250 m tabular thickness (models/iceberg/melt.py) at the ice/water
# density ratio gives ~207 m. An ASSUMPTION, carried into every output.
ASSUMED_DRAUGHT_M = 0.83 * 250.0


class BathymetryGrid:
    """Shallowest depth per 0.05° cell, from the committed IBCSO/GEBCO subset."""

    def __init__(self, path: Path | None = None):
        path = path or (Path(__file__).resolve().parent.parent
                        / "data" / "bathymetry" / "ibcso_v2_corridor_0p05.nc")
        with xr.open_dataset(path) as ds:
            self.lat = ds["lat"].values
            self.lon = ds["lon"].values
            # elevation: negative below sea level; shallowest point per cell
            self.elev = ds["elevation"].values

    def depth_m(self, lon: float, lat: float) -> float:
        """Water depth (positive down); NaN outside coverage, <=0 on land."""
        if not (self.lat[0] <= lat <= self.lat[-1]
                and self.lon[0] <= lon <= self.lon[-1]):
            return float("nan")
        i = int(np.clip(np.searchsorted(self.lat, lat), 0, len(self.lat) - 1))
        j = int(np.clip(np.searchsorted(self.lon, lon), 0, len(self.lon) - 1))
        return float(-self.elev[i, j])


class CurrentField:
    """Daily-mean surface currents on a regular lat/lon grid."""

    def __init__(self, u: np.ndarray, v: np.ndarray, lat: np.ndarray,
                 lon: np.ndarray, day_centers: np.ndarray):
        """u, v: (n_days, n_lat, n_lon) m/s; day_centers: float days since epoch."""
        self.u, self.v = u, v
        self.lat, self.lon = lat, lon
        self.t = day_centers

    @classmethod
    def from_files(cls, paths: list[Path]) -> "CurrentField":
        """Build from daily CMEMS files (uo/vo, one or more time steps each)."""
        us, vs, times = [], [], []
        lat = lon = None
        for p in sorted(paths):
            with xr.open_dataset(p) as ds:
                lat_v = ds["latitude"].values
                lon_v = ds["longitude"].values
                if lat is None:
                    lat, lon = lat_v, lon_v
                elif not (np.array_equal(lat, lat_v) and np.array_equal(lon, lon_v)):
                    raise ValueError(f"{p} is on a different grid")
                u = ds["uo"].values
                v = ds["vo"].values
                if u.ndim == 4:  # (time, depth, lat, lon) -> surface level
                    u, v = u[:, 0], v[:, 0]
                us.append(u.astype(np.float32))
                vs.append(v.astype(np.float32))
                days = ds["time"].values.astype("datetime64[D]")
                times.append(days.astype("datetime64[s]").astype(float) / 86400.0 + 0.5)
        t = np.concatenate(times)
        order = np.argsort(t)
        return cls(np.concatenate(us)[order], np.concatenate(vs)[order],
                   lat, lon, t[order])

    def sample(self, lon: float, lat: float, when: dt.datetime) -> tuple[float, float]:
        """(u, v) in m/s at a point and instant; (nan, nan) if unknowable."""
        t = when.replace(tzinfo=dt.timezone.utc).timestamp() / 86400.0
        t = float(np.clip(t, self.t[0], self.t[-1]))
        k = int(np.searchsorted(self.t, t, side="right") - 1)
        k = min(max(k, 0), len(self.t) - 2) if len(self.t) > 1 else 0
        if len(self.t) == 1:
            w = 0.0
        else:
            w = (t - self.t[k]) / (self.t[k + 1] - self.t[k])
        u = self._bilinear(self.u[k], lon, lat)
        v = self._bilinear(self.v[k], lon, lat)
        if len(self.t) > 1 and w > 0:
            u2 = self._bilinear(self.u[k + 1], lon, lat)
            v2 = self._bilinear(self.v[k + 1], lon, lat)
            u, v = u * (1 - w) + u2 * w, v * (1 - w) + v2 * w
        return float(u), float(v)

    def _bilinear(self, grid: np.ndarray, lon: float, lat: float) -> float:
        """NaN if outside the grid or any of the 4 surrounding cells is NaN —
        near a coast we refuse to invent a water velocity."""
        if not (self.lon[0] <= lon <= self.lon[-1] and self.lat[0] <= lat <= self.lat[-1]):
            return float("nan")
        i = int(np.searchsorted(self.lat, lat)) - 1
        j = int(np.searchsorted(self.lon, lon)) - 1
        i = min(max(i, 0), len(self.lat) - 2)
        j = min(max(j, 0), len(self.lon) - 2)
        fy = (lat - self.lat[i]) / (self.lat[i + 1] - self.lat[i])
        fx = (lon - self.lon[j]) / (self.lon[j + 1] - self.lon[j])
        q = grid[i:i + 2, j:j + 2]
        if not np.isfinite(q).all():
            return float("nan")
        return float(q[0, 0] * (1 - fy) * (1 - fx) + q[0, 1] * (1 - fy) * fx
                     + q[1, 0] * fy * (1 - fx) + q[1, 1] * fy * fx)


ICE_ARCHIVE = (Path(__file__).resolve().parent.parent
               / "data" / "cmems_forecast_archive")


def known_stale_dates(archive_dir: Path = ICE_ARCHIVE) -> set[dt.date]:
    """Cycle dates listed in KNOWN_STALE.md: files that hold the previous
    day's forecast under this day's name, so their day 0 is not an analysis."""
    note = Path(archive_dir) / "KNOWN_STALE.md"
    if not note.exists():
        return set()
    return {dt.date.fromisoformat(d) for d in
            re.findall(r"cmems_siconc_(\d{4}-\d{2}-\d{2})\.nc", note.read_text())}


class IceField:
    """Daily sea-ice state: concentration A (0-1), thickness h (m) and ice
    velocity (m/s), sampled by the same code as the currents.

    Built from day 0 (the analysis day) of each archived CMEMS forecast cycle.
    A day with no usable cycle is filled with the nearest good day's field and
    recorded in `substituted` -- held, never interpolated into existence.
    """

    def __init__(self, conc: np.ndarray, thick: np.ndarray, u: np.ndarray,
                 v: np.ndarray, lat: np.ndarray, lon: np.ndarray,
                 day_centers: np.ndarray,
                 substituted: dict[dt.date, dt.date] | None = None):
        """All fields (n_days, n_lat, n_lon); day_centers: float days since epoch."""
        # two CurrentField samplers, so the bilinear-in-space, linear-in-time
        # rule and its refuse-to-invent NaN behaviour are literally shared
        self._state = CurrentField(conc, thick, lat, lon, day_centers)
        self._drift = CurrentField(u, v, lat, lon, day_centers)
        self.lat, self.lon, self.t = lat, lon, day_centers
        self.substituted = substituted or {}

    @classmethod
    def from_archive(cls, archive_dir: Path = ICE_ARCHIVE,
                     skip: set[dt.date] | None = None) -> "IceField":
        """Load day 0 of every cmems_siconc_<date>.nc cycle except `skip`
        (default: the dates in KNOWN_STALE.md)."""
        archive_dir = Path(archive_dir)
        skip = known_stale_dates(archive_dir) if skip is None else skip
        good: dict[dt.date, tuple] = {}
        lat = lon = None
        for p in sorted(archive_dir.glob("cmems_siconc_*.nc")):
            day = dt.date.fromisoformat(p.stem[-10:])
            if day in skip:
                continue
            with xr.open_dataset(p) as ds:
                first = ds["time"].values[0].astype("datetime64[D]").astype(dt.date)
                if first != day:
                    raise ValueError(f"{p.name}: first time step is {first}, not {day}")
                lat_v, lon_v = ds["latitude"].values, ds["longitude"].values
                if lat is None:
                    lat, lon = lat_v, lon_v
                elif not (np.array_equal(lat, lat_v) and np.array_equal(lon, lon_v)):
                    raise ValueError(f"{p} is on a different grid")
                good[day] = tuple(ds[k].isel(time=0).values.astype(np.float32)
                                  for k in ("siconc", "sithick", "usi", "vsi"))
        if not good:
            raise FileNotFoundError(f"no usable sea-ice cycles in {archive_dir}")

        days = [min(good) + dt.timedelta(days=i)
                for i in range((max(good) - min(good)).days + 1)]
        substituted = {}
        stacks = ([], [], [], [])
        for day in days:
            src = day
            if day not in good:
                # nearest good day; on a tie the earlier one
                src = min(good, key=lambda g: (abs((g - day).days), g))
                substituted[day] = src
            for stack, grid in zip(stacks, good[src]):
                stack.append(grid)
        t = np.array([np.datetime64(d).astype("datetime64[s]").astype(float) / 86400.0 + 0.5
                      for d in days])
        return cls(*(np.stack(st) for st in stacks), lat, lon, t, substituted)

    def sample(self, lon: float, lat: float,
               when: dt.datetime) -> tuple[float, float, float, float]:
        """(A, h, u_si, v_si) at a point and instant; NaN where unknowable."""
        return (*self._state.sample(lon, lat, when),
                *self._drift.sample(lon, lat, when))


@dataclass
class Track:
    name: str
    times: list[dt.datetime] = field(default_factory=list)
    lats: list[float] = field(default_factory=list)
    lons: list[float] = field(default_factory=list)
    status: str = STATUS_OK
    wind_forcing_R: float | None = None  # assumed 10 m/s wind, see module doc
    # Sea-ice locking, filled only when forecast_track is given an ice field:
    # one lambda per integrated step (the midpoint stage, whose velocity moves
    # the berg), and how many of those steps had no sea-ice data at the berg.
    sil_lambda: list[float] = field(default_factory=list)
    ice_missing_steps: int = 0

    def positions(self):
        return list(zip(self.times, self.lats, self.lons))


def _step_velocity(field_: CurrentField, lon, lat, when, length_m, width_m):
    uc, vc = field_.sample(lon, lat, when)
    if not (math.isfinite(uc) and math.isfinite(vc)):
        return None
    u, v = iceberg_velocity(uc, vc, 0.0, 0.0, lat, length_m, width_m)
    return float(u), float(v), float(np.hypot(uc, vc)), float(uc), float(vc)


def forecast_track(name: str, lat0: float, lon0: float,
                   length_m: float, width_m: float,
                   field_: CurrentField,
                   start: dt.datetime, days: float,
                   dt_hours: float = 1.0,
                   bathymetry: "BathymetryGrid | None" = None,
                   draught_m: float = ASSUMED_DRAUGHT_M,
                   ice_field: "IceField | None" = None,
                   sil_params: dict | None = None) -> Track:
    """Midpoint (RK2) integration of one berg. Record hourly positions.

    With `bathymetry`, a berg whose assumed keel reaches the seabed
    (depth < draught_m) is marked grounded at its start or wherever the track
    first touches such a cell, and is not advected further — the v2 behaviour
    motivated by the v1 hindcast finding that most corridor giants are
    anchored. Without it, behaviour is exactly the original v1.

    With `ice_field`, both RK2 stages pass the WDE17 velocity through the
    sea-ice locking rule of Marson et al. (2024) (models/iceberg/sil.py);
    `sil_params` overrides its defaults. `sil_params={"strength_rule":
    "forces"}` uses the paper's strength threshold, the force needed to hold
    this berg at the ice velocity; the default "drag" is the weaker form the
    first hindcast run used. Where the ice field has no data the
    step uses the WDE17 velocity unchanged and is counted on the track.
    Without `ice_field` nothing about the integration changes.
    """
    track = Track(name=name)
    lat, lon = float(lat0), float(lon0)
    t = start
    h = dt_hours * 3600.0
    end = start + dt.timedelta(days=days)
    track.times.append(t); track.lats.append(lat); track.lons.append(lon)

    first = _step_velocity(field_, lon, lat, t, length_m, width_m)
    if first is not None:
        track.wind_forcing_R = float(relative_wind_forcing(
            10.0, max(first[2], 1e-6), lat, length_m, width_m))

    def aground(lo, la):
        if bathymetry is None:
            return False
        d = bathymetry.depth_m(lo, la)
        return math.isfinite(d) and d < draught_m

    if aground(lon, lat):
        track.status = STATUS_GROUNDED
        return track

    sil_kwargs = dict(sil_params or {})
    strength_rule = sil_kwargs.pop("strength_rule", "drag")
    if strength_rule not in ("drag", "forces"):
        raise ValueError(f"unknown strength_rule {strength_rule!r}")

    def with_ice(k, lo, la, when):
        """(u, v, lambda, ice_known) after sea-ice locking at this stage."""
        conc, thick, u_si, v_si = ice_field.sample(lo, la, when)
        known = all(math.isfinite(x) for x in (conc, thick, u_si, v_si))
        p_s = None
        if strength_rule == "forces" and known:
            p_s = locking_force_per_width(u_si, v_si, k[3], k[4], la,
                                          length_m, width_m)
        return (*sil_velocity(k[0], k[1], conc, thick, u_si, v_si, p_s=p_s,
                              **sil_kwargs), known)

    while t < end:
        k1 = _step_velocity(field_, lon, lat, t, length_m, width_m)
        if k1 is None:
            track.status = STATUS_GROUNDED
            break
        if ice_field is not None:
            k1 = with_ice(k1, lon, lat, t)
        mid_lat = lat + k1[1] * h / 2 / M_PER_DEG
        mid_lon = lon + k1[0] * h / 2 / (M_PER_DEG * math.cos(math.radians(lat)))
        t_mid = t + dt.timedelta(seconds=h / 2)
        k2 = _step_velocity(field_, mid_lon, mid_lat, t_mid, length_m, width_m)
        if k2 is None:
            track.status = STATUS_GROUNDED
            break
        if ice_field is not None:
            k2 = with_ice(k2, mid_lon, mid_lat, t_mid)
        new_lat = lat + k2[1] * h / M_PER_DEG
        new_lon = lon + k2[0] * h / (M_PER_DEG * math.cos(math.radians(lat)))
        if aground(new_lon, new_lat):
            track.status = STATUS_GROUNDED
            break
        lat, lon = new_lat, new_lon
        t = t + dt.timedelta(seconds=h)
        if ice_field is not None:
            track.sil_lambda.append(k2[2])
            track.ice_missing_steps += not k2[3]
        track.times.append(t); track.lats.append(lat); track.lons.append(lon)
    return track


def great_circle_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
