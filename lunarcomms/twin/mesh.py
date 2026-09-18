"""
LOLA DEM -> triangle mesh for a Sionna RT lunar scene (the "LunarTwin").

This is the geometry stage of the BostonTwin-style pipeline, with terrain in
place of buildings: a heightfield becomes a single triangulated surface, in
metric polar-stereographic coordinates, with the spherical-Moon bulge baked in
so a >10 km tile is not treated as flat. Pure NumPy -- no Sionna dependency.
"""

from __future__ import annotations

import numpy as np

R_MOON_M = 1_737_400.0


def dem_to_mesh(
    dem: np.ndarray,
    pixel_size_m: float,
    stride: int = 1,
    curvature: bool = True,
    planet_radius_m: float = R_MOON_M,
    center_m: tuple[float, float] | None = None,
):
    """Triangulate a DEM heightfield into (vertices Nx3, faces Mx3).

    ``stride`` decimates the grid (LOD): stride=4 keeps every 4th sample, which
    is the main knob for ray-tracer tractability -- note that decimation blunts
    crater rims and therefore the edge diffraction that dominates lunar
    coverage, so keep it coarse only away from the region of interest.

    ``curvature`` bends the tile onto a sphere cap by subtracting
    ((x-cx)^2+(y-cy)^2)/(2R) from z (the same bulge the LOS test uses), so the
    mesh is a spherical-Moon surface rather than a tangent plane.
    """
    d = np.asarray(dem, dtype=float)[::stride, ::stride]
    h, w = d.shape
    px = pixel_size_m * stride
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    x = xx * px
    y = yy * px
    z = d.copy()
    if curvature:
        cx, cy = center_m if center_m else (x.mean(), y.mean())
        z = z - ((x - cx) ** 2 + (y - cy) ** 2) / (2.0 * planet_radius_m)

    verts = np.column_stack([x.ravel(), y.ravel(), z.ravel()])

    # two triangles per grid cell, vectorized
    i, j = np.mgrid[0:h - 1, 0:w - 1]
    v00 = (i * w + j).ravel()
    v10 = ((i + 1) * w + j).ravel()
    v01 = (i * w + j + 1).ravel()
    v11 = ((i + 1) * w + j + 1).ravel()
    tri1 = np.column_stack([v00, v10, v01])
    tri2 = np.column_stack([v10, v11, v01])
    faces = np.vstack([tri1, tri2])
    return verts, faces


def write_ply(vertices: np.ndarray, faces: np.ndarray, path: str) -> None:
    """Write an ASCII PLY (the mesh format Sionna/Mitsuba scenes reference)."""
    v, f = np.asarray(vertices, float), np.asarray(faces, int)
    with open(path, "w") as fh:
        fh.write("ply\nformat ascii 1.0\n")
        fh.write(f"element vertex {len(v)}\n")
        fh.write("property float x\nproperty float y\nproperty float z\n")
        fh.write(f"element face {len(f)}\n")
        fh.write("property list uchar int vertex_indices\n")
        fh.write("end_header\n")
        for x, y, z in v:
            fh.write(f"{x:.4f} {y:.4f} {z:.4f}\n")
        for a, b, c in f:
            fh.write(f"3 {a} {b} {c}\n")


__all__ = ["dem_to_mesh", "write_ply", "R_MOON_M"]
