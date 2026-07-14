"""
Terrain diffraction loss -- ITU-R P.526-15 (Deygout multi-edge method).
Student 1 (S1) -- Week 4 implementation.

Formulas verified against ITU-R P.526-15:
  Fresnel-Kirchhoff parameter (eq. 13):
      nu = h * sqrt( 2/lambda * (1/d1 + 1/d2) )
  Knife-edge loss (eq. 14, valid nu >= -0.78):
      J(nu) = 6.9 + 20*log10( sqrt((nu-0.1)**2 + 1) + nu - 0.1 )
      J(nu) = 0  for nu < -0.78

NOTE: the original scaffold's worked example ("nu ~ 11.5" for a 200 m rim)
was incorrect -- the correct value from eq. 13 is ~23.1 for a 200 m rim at
S-band midpoint (11.5 corresponds to a ~100 m rim). The formulas here are the
verified ITU-R ones.
"""
import numpy as np

_C = 299792458.0  # m/s


def fresnel_kirchhoff_parameter(h_m, d1_m, d2_m, freq_hz):
    """ITU-R P.526-15 eq. 13 diffraction parameter nu.

        nu = h * sqrt( 2/lambda * (1/d1 + 1/d2) ),  lambda = c/f

    h_m > 0 : obstacle above the Tx-Rx line of sight (diffraction loss).
    h_m < 0 : clearance below LOS (nu < 0, little/no loss).
    """
    h = np.asarray(h_m, dtype=float)
    d1 = np.asarray(d1_m, dtype=float)
    d2 = np.asarray(d2_m, dtype=float)
    lam = _C / float(freq_hz)
    return h * np.sqrt(2.0 / lam * (1.0 / d1 + 1.0 / d2))


def knife_edge_loss_db(nu):
    """ITU-R P.526-15 eq. 14 knife-edge diffraction loss J(nu) in dB.

        J = 0                                                nu < -0.78
        J = 6.9 + 20 log10( sqrt((nu-0.1)^2 + 1) + nu-0.1 )  otherwise
    """
    nu = np.asarray(nu, dtype=float)
    j = 6.9 + 20.0 * np.log10(np.sqrt((nu - 0.1) ** 2 + 1.0) + nu - 0.1)
    out = np.where(nu < -0.78, 0.0, j)
    return float(out) if np.ndim(out) == 0 else out


def _height_above_los(profile_heights_m, profile_distances_m, h_tx_m, h_rx_m):
    """Height of each profile point above the straight Tx-Rx line."""
    d = np.asarray(profile_distances_m, dtype=float)
    h = np.asarray(profile_heights_m, dtype=float)
    tx_elev = h[0] + h_tx_m
    rx_elev = h[-1] + h_rx_m
    total = d[-1] - d[0]
    los = tx_elev + (rx_elev - tx_elev) * (d - d[0]) / total
    return h - los


def deygout_loss_db(profile_heights_m, profile_distances_m,
                    h_tx_m, h_rx_m, freq_hz, max_edges=3):
    """Deygout dominant-edge multi-edge diffraction loss (dB).

    Recursively: find the point of maximum nu between the endpoints; add its
    knife-edge loss; recurse on the Tx->peak and peak->Rx sub-paths, up to
    max_edges dominant edges. Reduces exactly to a single knife edge for a
    lone obstacle.
    """
    d = np.asarray(profile_distances_m, dtype=float)
    h = np.asarray(profile_heights_m, dtype=float)

    def recurse(i0, i1, edges_left):
        if i1 - i0 < 2 or edges_left <= 0:
            return 0.0
        lo, hi = i0 + 1, i1
        d1 = d[lo:hi] - d[i0]
        d2 = d[i1] - d[lo:hi]
        tx_e = h[i0] + (h_tx_m if i0 == 0 else 0.0)
        rx_e = h[i1] + (h_rx_m if i1 == len(d) - 1 else 0.0)
        span = d[i1] - d[i0]
        los = tx_e + (rx_e - tx_e) * (d[lo:hi] - d[i0]) / span
        hsub = h[lo:hi] - los
        nus = fresnel_kirchhoff_parameter(hsub, d1, d2, freq_hz)
        k = int(np.argmax(nus))
        nu_max = nus[k]
        if nu_max <= -0.78:
            return 0.0
        ipk = lo + k
        loss = knife_edge_loss_db(nu_max)
        loss += recurse(i0, ipk, edges_left - 1)
        loss += recurse(ipk, i1, edges_left - 1)
        return loss

    return float(recurse(0, len(d) - 1, max_edges))
