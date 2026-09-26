"""Default link budget of the IEEE Aerospace 2027 coverage study.

Sources (see the paper, Sec. "Study Sites and Default Parameters"):
  SENS_DBM  -93.8 dBm: 3GPP TS 38.101-1 v15.2.0 Table 7.3.2-1, NR reference
            sensitivity for a 20 MHz carrier in band n38, 15 kHz SCS. (An
            earlier default of -106 dBm corresponded to a ~1.25 MHz narrowband
            allocation and was 12 dB more optimistic.)
  EIRP_DBM  53 dBm: between the 50 dBm / 0 dBi lunar scenario of Edwards et al.
            (IEEE Aerospace 2023) and a 3GPP macro cell (46 dBm, 12-15 dBi).
  GRX_DBI   2 dBi user antenna (TR 36.942 uses 0 dBi).
  H_TX_M    30 m mast (Edwards et al. lander tower; TR 36.942 Table 4.3).
  H_RX_M    2 m user antenna.
"""
SENS_DBM = -93.8
EIRP_DBM = 53.0
GRX_DBI = 2.0
H_TX_M = 30.0
H_RX_M = 2.0
