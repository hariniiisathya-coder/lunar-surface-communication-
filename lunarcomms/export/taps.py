"""
Tap-delay-line channel export for the lunar surface pipeline.

Purpose
-------
Bridge the S1 coverage physics (two-ray + Deygout over a real DEM) into the
formats 5G link-level simulators and channel emulators consume:

  * MATLAB 5G Toolbox ``nrTDLChannel`` with ``DelayProfile='Custom'``
    (``PathDelays`` in seconds, ``AveragePathGains`` in dB), via
    :func:`to_nrtdl_dict` / :func:`save_nrtdl_mat`.
  * Colosseum/MCHEM-style tap grids (4 taps, 10 ns resolution, 5.11 us max
    delay), via :func:`to_colosseum_taps`.
  * Plain JSON for anything else, via :func:`save_json`.

Physical model (and why the lunar channel is SPARSE)
----------------------------------------------------
Per link the model produces at most a handful of discrete paths:

  LOS pixel:   direct ray (reference, 0 s excess delay, 0 dB) plus the ground
               reflection with complex gain  Gamma * (r1/r2) * exp(-j k dr)
               at excess delay dr/c, dr = r2 - r1. For surface geometries
               (h_tx=30 m, h_rx=2 m, d up to a few km) dr/c is ~0.1-2 ns —
               BELOW any practical emulator tap resolution. The two rays
               therefore collapse into ONE complex tap whose magnitude carries
               the two-ray interference (the spatial nulls a moving rover
               experiences as time fading). Use ``collapse_below_s`` for this.
  NLOS pixel:  no direct ray; a single Deygout-diffracted path with gain
               -J_total dB (ITU-R P.526-15) and a geometric excess delay from
               the dominant edge:  sqrt(d1^2+h^2) + sqrt(d2^2+h^2) - (d1+d2),
               over c. Tens to hundreds of ns for crater-rim edges.

Consequence: 1-3 taps per link. Terrestrial channels fight emulator tap
limits; the lunar surface channel fits MCHEM's 4-tap budget with room to
spare. Gains here are RELATIVE to the free-space direct ray at the same 3-D
distance (E/E_direct); the absolute scale is carried separately as
``fspl_direct_db`` so consumers apply path loss once, globally, the way
nrTDLChannel expects.

Subsurface (Chang'E-4 stratigraphy) taps are deliberately NOT emitted at
S-band and above: the two-way dielectric attenuation through ~12 m of
regolith (~2-3 dB/m at 2.5 GHz) buries those echoes ~75+ dB below the direct
ray. At UHF they become borderline-relevant; add them there if needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from ..geometry.horizon import extract_profile
from ..propagation.diffraction import (
    deygout_loss_db,
    fresnel_kirchhoff_parameter,
    knife_edge_loss_db,
)
from ..propagation.friis import fspl_db
from ..regolith.dielectric import fresnel_coefficients

_C = 299792458.0  # m/s

#: MCHEM (Colosseum) channel-emulator tap grid: 100 MS/s -> 10 ns resolution,
#: 4 complex taps per link, max excess delay 5.11 us.
MCHEM_TAP_RESOLUTION_S = 10e-9
MCHEM_MAX_TAPS = 4
MCHEM_MAX_DELAY_S = 5.11e-6


@dataclass
class LinkTaps:
    """Sparse tap-delay-line description of one Tx->Rx surface link.

    delays_s / gains : excess delay (s, direct ray = 0) and complex amplitude
        RELATIVE to the free-space direct ray at the same 3-D distance.
    los : True if the straight ray clears the terrain profile.
    fspl_direct_db : free-space loss of the direct 3-D distance (absolute
        scale; total PL of tap i = fspl_direct_db - 20*log10|gains[i]|).
    meta : geometry and model bookkeeping.
    """

    delays_s: np.ndarray
    gains: np.ndarray
    los: bool
    fspl_direct_db: float
    meta: dict = field(default_factory=dict)

    @property
    def gains_db(self) -> np.ndarray:
        """Tap magnitudes in dB (relative to the free-space direct ray)."""
        mag = np.maximum(np.abs(self.gains), 1e-12)
        return 20.0 * np.log10(mag)

    def collapsed(self, resolution_s: float = MCHEM_TAP_RESOLUTION_S) -> "LinkTaps":
        """Merge taps closer than ``resolution_s`` by complex summation.

        This is where the two-ray pair (excess delay ~ns) becomes one complex
        tap whose magnitude carries the interference null structure.
        """
        order = np.argsort(self.delays_s)
        d_sorted = np.asarray(self.delays_s, dtype=float)[order]
        g_sorted = np.asarray(self.gains, dtype=complex)[order]
        out_d: list[float] = []
        out_g: list[complex] = []
        for d, g in zip(d_sorted, g_sorted):
            if out_d and (d - out_d[-1]) < resolution_s:
                # merge into the current bin; keep power-weighted delay
                w0, w1 = abs(out_g[-1]) ** 2, abs(g) ** 2
                tot = w0 + w1
                if tot > 0:
                    out_d[-1] = (out_d[-1] * w0 + d * w1) / tot
                out_g[-1] = out_g[-1] + g
            else:
                out_d.append(float(d))
                out_g.append(complex(g))
        return LinkTaps(
            delays_s=np.asarray(out_d),
            gains=np.asarray(out_g),
            los=self.los,
            fspl_direct_db=self.fspl_direct_db,
            meta={**self.meta, "collapsed_resolution_s": resolution_s},
        )


def link_taps(
    dem: np.ndarray,
    pixel_size_m: float,
    tx_row: int,
    tx_col: int,
    rx_row: int,
    rx_col: int,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    rho: float = 1.50,
    max_edges: int = 3,
    tx_pattern=None,
    rx_pattern=None,
    sigma_h_m: float = 0.0,
    roughness_model: str = "ament",
    pol: str = "v",
) -> LinkTaps:
    """Compute the sparse tap set for one Tx->Rx link over the DEM.

    Uses the same profile extraction, LOS test, Fresnel reflection and
    Deygout diffraction as the coverage pipeline, so the taps are exactly the
    channel the coverage maps already assume — just resolved in delay.

    tx_pattern, rx_pattern : optional lunarcomms.antenna.Pattern instances.
        When supplied, the ground-reflected LOS tap is weighted by the antenna
        field gain at its (steeper, downward) elevation relative to the direct
        ray -- the collapsed tap then automatically carries the pattern-shaped
        interference. Default (None) == isotropic == unchanged, so the
        collapsed-tap <-> two_ray.path_loss_db consistency check still holds.
        The NLOS/Deygout tap is also weighted: the diffracted ray launches
        toward the dominant edge (elevation from the edge geometry), so a
        downtilted or directional mast that under- or over-illuminates a
        crater rim changes NLOS coverage too.

    pol : reflection polarization, "v" (vertical, default) or "h" (horizontal),
        forwarded to the Fresnel coefficient. Only affects LOS reflection; near
        grazing both -> -1. Default "v" keeps the consistency check exact.

    sigma_h_m : RMS surface height (m) for the roughness reduction of the
        coherent ground reflection (roughness.specular_factor). Default 0 =
        smooth = unchanged. At high band the reflected tap decoheres and the
        collapsed tap approaches the direct ray (0 dB) -- the specular->diffuse
        transition, per band.
    """
    heights, dist = extract_profile(dem, tx_row, tx_col, rx_row, rx_col,
                                    pixel_size_m)
    d_ground = float(dist[-1])
    tx_e = float(heights[0]) + h_tx_m
    rx_e = float(heights[-1]) + h_rx_m

    # 3-D direct distance and LOS test (same clearance rule as
    # horizon.los_mask_from_tx).
    d3d = float(np.hypot(d_ground, rx_e - tx_e))
    if d_ground <= 0 or len(heights) < 3:
        los = True
    else:
        ray = tx_e + (rx_e - tx_e) * (dist / d_ground)
        los = bool(np.all(ray[1:-1] - heights[1:-1] >= 0))

    lam = _C / float(freq_hz)
    k = 2.0 * np.pi / lam
    fspl_direct = float(fspl_db(max(d3d, 1e-6), freq_hz))
    meta = {
        "freq_hz": float(freq_hz),
        "d_ground_m": d_ground,
        "d3d_m": d3d,
        "h_tx_m": h_tx_m,
        "h_rx_m": h_rx_m,
        "rho": rho,
        "tx_rc": (int(tx_row), int(tx_col)),
        "rx_rc": (int(rx_row), int(rx_col)),
    }

    if los:
        # Two-ray: direct (reference) + ground reflection, flat-ground
        # image geometry on the local mean plane.
        r1 = float(np.hypot(d_ground, h_tx_m - h_rx_m))
        r2 = float(np.hypot(d_ground, h_tx_m + h_rx_m))
        dr = r2 - r1
        theta = float(np.arctan2(h_tx_m + h_rx_m, d_ground))  # grazing angle
        gv, gh = fresnel_coefficients(rho, float(freq_hz) / 1e9, theta)
        gamma = gv if str(pol).lower().startswith("v") else gh
        if sigma_h_m:
            from ..propagation.roughness import specular_factor
            gamma = gamma * specular_factor(sigma_h_m, freq_hz, theta,
                                            model=roughness_model)
        w = 1.0
        if tx_pattern is not None or rx_pattern is not None:
            from ..antenna.geometry import reflected_ray_weight
            w = float(reflected_ray_weight(d_ground, h_tx_m, h_rx_m,
                                           tx_pattern, rx_pattern))
        g_refl = w * complex(gamma) * (r1 / r2) * np.exp(-1j * k * dr)
        return LinkTaps(
            delays_s=np.array([0.0, dr / _C]),
            gains=np.array([1.0 + 0.0j, g_refl]),
            los=True,
            fspl_direct_db=fspl_direct,
            meta={**meta, "model": "two-ray", "grazing_angle_rad": theta},
        )

    # NLOS: Deygout total loss + excess delay of the dominant edge.
    loss_db = float(deygout_loss_db(heights, dist, h_tx_m, h_rx_m,
                                    freq_hz, max_edges=max_edges))
    # Dominant edge geometry (same construction as deygout_loss_db's
    # top-level pass): height above the Tx-Rx line, max-nu point.
    los_line = tx_e + (rx_e - tx_e) * (dist / d_ground)
    hsub = np.asarray(heights, dtype=float) - los_line
    d1_all = np.asarray(dist, dtype=float)
    d2_all = d_ground - d1_all
    interior = slice(1, len(dist) - 1)
    nus = fresnel_kirchhoff_parameter(hsub[interior], d1_all[interior],
                                      d2_all[interior], freq_hz)
    k_dom = int(np.argmax(nus)) + 1
    h_dom = max(float(hsub[k_dom]), 0.0)
    d1, d2 = float(d1_all[k_dom]), float(d_ground - d1_all[k_dom])
    excess_m = (np.hypot(d1, h_dom) + np.hypot(d2, h_dom)) - (d1 + d2)
    g_diff = 10.0 ** (-loss_db / 20.0) * np.exp(-1j * k * excess_m)

    # Antenna weighting of the diffracted ray: it launches UP toward the
    # dominant edge (not along the blocked geometric direct line). Weight by
    # the pattern gain toward the edge relative to the direct direction the
    # global EIRP/Rx-gain already assume -- so a downtilted mast that
    # under-illuminates a crater rim above it loses NLOS coverage.
    w_diff = 1.0
    if tx_pattern is not None or rx_pattern is not None:
        from ..antenna.geometry import ray_pattern_weight
        edge_elev = float(los_line[k_dom] + h_dom)
        el_tx_ray = np.degrees(np.arctan2(edge_elev - tx_e, max(d1, 1e-9)))
        el_rx_ray = np.degrees(np.arctan2(edge_elev - rx_e, max(d2, 1e-9)))
        el_tx_ref = np.degrees(np.arctan2(rx_e - tx_e, d_ground))
        el_rx_ref = np.degrees(np.arctan2(tx_e - rx_e, d_ground))
        w_diff = float(ray_pattern_weight(el_tx_ref, el_rx_ref,
                                          el_tx_ray, el_rx_ray,
                                          tx_pattern, rx_pattern))
    g_diff = w_diff * g_diff
    return LinkTaps(
        delays_s=np.array([excess_m / _C]),
        gains=np.array([complex(g_diff)]),
        los=False,
        fspl_direct_db=fspl_direct,
        meta={**meta, "model": "deygout",
              "deygout_loss_db": loss_db,
              "dominant_edge_height_m": h_dom,
              "dominant_edge_nu": float(nus[k_dom - 1]),
              "dominant_edge_d1_m": d1,
              "antenna_weight": w_diff},
    )


def trajectory_taps(
    dem: np.ndarray,
    pixel_size_m: float,
    tx_row: int,
    tx_col: int,
    path_rc: list[tuple[int, int]],
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    rho: float = 1.50,
    **kwargs,
) -> list[LinkTaps]:
    """Tap sets along a rover trajectory (list of (row, col) waypoints).

    This is the time-varying channel trace: as the rover crosses two-ray
    interference nulls, the collapsed tap magnitude oscillates — the
    'cancellation dynamics' a link-level simulator should replay. Pair each
    entry with a timestamp from the rover speed to obtain g(t).
    """
    return [
        link_taps(dem, pixel_size_m, tx_row, tx_col, r, c,
                  h_tx_m, h_rx_m, freq_hz, rho=rho, **kwargs)
        for (r, c) in path_rc
    ]


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------

def to_nrtdl_dict(link: LinkTaps,
                  collapse_below_s: float | None = None) -> dict:
    """Fields for MATLAB nrTDLChannel with DelayProfile='Custom'.

    Returns PathDelays (s, row vector), AveragePathGains (dB, relative),
    plus the absolute anchor fspl_direct_db and phases (nrTDLChannel draws
    its own fading phases; initial phases are provided for deterministic
    replay tools).
    """
    lk = link.collapsed(collapse_below_s) if collapse_below_s else link
    return {
        "PathDelays": np.asarray(lk.delays_s, dtype=float).reshape(1, -1),
        "AveragePathGains": np.asarray(lk.gains_db, dtype=float).reshape(1, -1),
        "InitialPhasesRad": np.angle(np.asarray(lk.gains)).reshape(1, -1),
        "FSPLDirect_dB": float(lk.fspl_direct_db),
        "LOS": bool(lk.los),
        "CarrierHz": float(lk.meta.get("freq_hz", np.nan)),
    }


def save_nrtdl_mat(links: LinkTaps | list[LinkTaps], path: str,
                   collapse_below_s: float | None = None) -> None:
    """Save one link or a trajectory as a MATLAB .mat for nrTDLChannel.

    A single link saves scalar fields; a list saves cell-array-style stacked
    fields (one row per waypoint) plus GainMagnitude for quick plotting of
    the along-track fading trace.
    """
    from scipy.io import savemat

    if isinstance(links, LinkTaps):
        savemat(path, to_nrtdl_dict(links, collapse_below_s))
        return
    dicts = [to_nrtdl_dict(lk, collapse_below_s) for lk in links]
    n_taps = max(d["PathDelays"].size for d in dicts)

    def _pad(row, fill):
        row = np.asarray(row, dtype=float).ravel()
        return np.pad(row, (0, n_taps - row.size), constant_values=fill)

    savemat(path, {
        "PathDelays": np.vstack([_pad(d["PathDelays"], 0.0) for d in dicts]),
        "AveragePathGains": np.vstack(
            [_pad(d["AveragePathGains"], -300.0) for d in dicts]),
        "InitialPhasesRad": np.vstack(
            [_pad(d["InitialPhasesRad"], 0.0) for d in dicts]),
        "FSPLDirect_dB": np.array([[d["FSPLDirect_dB"]] for d in dicts]),
        "LOS": np.array([[d["LOS"]] for d in dicts], dtype=np.uint8),
        "CarrierHz": float(dicts[0]["CarrierHz"]),
        "GainMagnitude_dB": np.array(
            [[20.0 * np.log10(max(
                np.abs(np.sum(lk.collapsed().gains)), 1e-12))]
             for lk in links]),
    })


def to_colosseum_taps(
    link: LinkTaps,
    n_taps: int = MCHEM_MAX_TAPS,
    tap_resolution_s: float = MCHEM_TAP_RESOLUTION_S,
    max_delay_s: float = MCHEM_MAX_DELAY_S,
) -> tuple[np.ndarray, np.ndarray]:
    """Quantize a link onto an MCHEM-style tap grid.

    Returns (delays_s, complex_gains), both length <= n_taps, delays on the
    tap_resolution_s grid, clipped to max_delay_s. Taps landing on the same
    grid cell are complex-summed; if more than n_taps cells are occupied the
    strongest n_taps are kept. For lunar surface links this never truncates
    (1-3 physical taps).
    """
    lk = link.collapsed(tap_resolution_s)
    cells: dict[int, complex] = {}
    for d, g in zip(lk.delays_s, lk.gains):
        if d > max_delay_s:
            continue
        idx = int(round(d / tap_resolution_s))
        cells[idx] = cells.get(idx, 0.0 + 0.0j) + complex(g)
    idxs = sorted(cells, key=lambda i: -abs(cells[i]))[:n_taps]
    idxs.sort()
    delays = np.array([i * tap_resolution_s for i in idxs])
    gains = np.array([cells[i] for i in idxs])
    return delays, gains


def save_json(links: LinkTaps | list[LinkTaps], path: str) -> None:
    """Plain-JSON dump (delays, complex gains as [re, im], meta)."""
    def one(lk: LinkTaps) -> dict:
        return {
            "delays_s": np.asarray(lk.delays_s, dtype=float).tolist(),
            "gains_re_im": [[float(g.real), float(g.imag)] for g in lk.gains],
            "los": bool(lk.los),
            "fspl_direct_db": float(lk.fspl_direct_db),
            "meta": {mk: (list(mv) if isinstance(mv, tuple) else mv)
                     for mk, mv in lk.meta.items()},
        }

    payload = one(links) if isinstance(links, LinkTaps) else [one(x) for x in links]
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


__all__ = [
    "LinkTaps",
    "link_taps",
    "trajectory_taps",
    "to_nrtdl_dict",
    "save_nrtdl_mat",
    "to_colosseum_taps",
    "save_json",
    "MCHEM_TAP_RESOLUTION_S",
    "MCHEM_MAX_TAPS",
    "MCHEM_MAX_DELAY_S",
    "knife_edge_loss_db",
]
