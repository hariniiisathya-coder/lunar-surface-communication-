"""Lunar coordinate frames and Earth-Moon geometry via SPICE (ASCII build)."""

from __future__ import annotations

import glob

import numpy as np
import spiceypy as spice

R_MOON_KM = 1737.4


def load_kernels(kernel_dir="data/kernels"):
    """Furnish the SPICE kernels needed for lunar geometry."""
    tls = glob.glob(f"{kernel_dir}/*.tls")
    if not tls:
        raise FileNotFoundError(f"No leapseconds (.tls) kernel in {kernel_dir}")
    spice.furnsh(tls[0])
    spice.furnsh(f"{kernel_dir}/de440.bsp")
    for pat in ("*.tpc", "*.bpc", "*.tf"):
        for k in glob.glob(f"{kernel_dir}/{pat}"):
            spice.furnsh(k)
    if spice.ktotal("ALL") < 4:
        raise RuntimeError("Expected at least 4 kernels furnished.")


def earth_moon_distance_km(et):
    """Earth-Moon distance (km) at ephemeris time et (scalar or array)."""
    et = np.asarray(et, dtype=float)
    if et.ndim == 0:
        pos, _ = spice.spkpos("MOON", float(et), "ECLIPJ2000", "NONE", "EARTH")
        return float(np.linalg.norm(pos))
    out = []
    for e in et:
        pos, _ = spice.spkpos("MOON", float(e), "ECLIPJ2000", "NONE", "EARTH")
        out.append(np.linalg.norm(pos))
    return np.array(out)


def surface_to_inertial(lon_deg, lat_deg, alt_m, frame="MOON_ME"):
    """Lunar surface (lon, lat, alt) -> Cartesian km in the requested frame."""
    rec = spice.pgrrec("MOON", np.radians(lon_deg), np.radians(lat_deg),
                       alt_m / 1000.0, R_MOON_KM, 0.0)
    if frame == "MOON_ME":
        return np.array(rec)
    rot = spice.pxform("MOON_ME", frame, 0.0)
    return np.array(spice.mxv(rot, rec))


def earth_elevation_angle_deg(surface_lon_deg, surface_lat_deg, et):
    """Elevation of Earth (deg) from a lunar surface point; <0 = below horizon."""
    earth_me, _ = spice.spkpos("EARTH", et, "MOON_ME", "NONE", "MOON")
    surf = np.array(spice.pgrrec("MOON", np.radians(surface_lon_deg),
                                 np.radians(surface_lat_deg), 0.0, R_MOON_KM, 0.0))
    to_earth = np.array(earth_me) - surf
    up = surf / np.linalg.norm(surf)
    sin_el = np.dot(to_earth, up) / np.linalg.norm(to_earth)
    return float(np.degrees(np.arcsin(np.clip(sin_el, -1, 1))))
