#!/usr/bin/env python3
"""
Pure adapter for TetGen via the local pybind11 module `_tetwrap`.

Inputs are plain NumPy arrays and Python lists — no dtcc dependency.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from . import _tetwrap, switches
from .tetwrapio import TetwrapIO

BoundaryFacets = Union[
    Sequence[Sequence[int]],
    Mapping[str, Sequence[int]],
]
BoundaryFacetMarkers = Union[
    Sequence[int],
    Mapping[str, int],
]
RawTetgenSwitches = Union[str, bytes, np.ndarray]
# Default named-facet order matching the dtcc CFD face-marker convention:
# -2 top, -3 west/xmin, -4 east/xmax, -5 south/ymin, -6 north/ymax.
BOUNDARY_FACET_ORDER = ("top", "west", "east", "south", "north")


def _ensure_ndarray(vertices: np.ndarray, faces: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    V = np.asarray(vertices, dtype=float)
    F = np.asarray(faces, dtype=np.int64)

    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError("vertices must be (N, 3) float array")
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("faces must be (M, 3) int array of triangles")
    return V, F


def _normalized_boundary_facet_keys(
    boundary_facets: Mapping[str, Sequence[int]],
) -> List[str]:
    keys: List[str] = []
    for key in BOUNDARY_FACET_ORDER:
        if key in boundary_facets:
            keys.append(key)
    for key in sorted(boundary_facets.keys()):
        if key not in BOUNDARY_FACET_ORDER:
            keys.append(key)
    return keys


def _normalize_boundary_facets(boundary_facets: BoundaryFacets) -> List[List[int]]:
    if boundary_facets is None:
        raise ValueError("boundary_facets is required (list of polygons or dict of named polygons)")

    if isinstance(boundary_facets, Mapping):
        out: List[List[int]] = []
        for key in _normalized_boundary_facet_keys(boundary_facets):
            poly = list(map(int, boundary_facets[key]))
            if len(poly) < 3:
                raise ValueError(f"boundary facet '{key}' must have at least 3 vertices")
            out.append(poly)
        if len(out) < 1:
            raise ValueError("boundary_facets dict must contain at least one polygon")
        return out

    out = []
    for i, poly in enumerate(boundary_facets):
        p = list(map(int, poly))
        if len(p) < 3:
            raise ValueError(f"boundary facet {i} must have at least 3 vertices")
        out.append(p)
    if len(out) < 1:
        raise ValueError("boundary_facets must contain at least one polygon")
    return out


def _normalize_boundary_facet_markers(
    boundary_facets: BoundaryFacets,
    boundary_facet_markers: BoundaryFacetMarkers,
) -> List[int]:
    if isinstance(boundary_facet_markers, Mapping):
        if not isinstance(boundary_facets, Mapping):
            raise ValueError(
                "boundary_facet_markers mapping requires boundary_facets to be a mapping too"
            )
        facet_keys = _normalized_boundary_facet_keys(boundary_facets)
        extra_keys = sorted(set(boundary_facet_markers.keys()) - set(facet_keys))
        if extra_keys:
            raise ValueError(
                "boundary_facet_markers contains keys not present in boundary_facets: "
                + ", ".join(extra_keys)
            )
        out: List[int] = []
        for key in facet_keys:
            if key not in boundary_facet_markers:
                raise ValueError(f"boundary_facet_markers is missing marker for facet '{key}'")
            out.append(int(boundary_facet_markers[key]))
        return out

    out = [int(marker) for marker in boundary_facet_markers]
    expected_count = (
        len(_normalized_boundary_facet_keys(boundary_facets))
        if isinstance(boundary_facets, Mapping)
        else len(boundary_facets)
    )
    if len(out) != expected_count:
        raise ValueError("boundary_facet_markers must have the same length as boundary_facets")
    return out


def tetrahedralize(
    vertices: np.ndarray,
    faces: np.ndarray,
    boundary_facets: BoundaryFacets,
    *,
    face_markers: Optional[Sequence[int]] = None,
    boundary_facet_markers: Optional[BoundaryFacetMarkers] = None,
    switches_params: Optional[Mapping[str, Any]] = None,
    switches_overrides: Optional[Mapping[str, Any]] = None,
    tetgen_switches: Optional[RawTetgenSwitches] = None,
    interior_default: Optional[int] = -10,
    return_io: bool = True,
    return_faces: bool = False,
    return_boundary_faces: bool = False,
    return_edges: bool = False,
    return_neighbors: bool = False,
) -> Union[
    TetwrapIO,
    Tuple[
        np.ndarray,
        np.ndarray,
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
    ],
]:
    """
    Run TetGen on a PLC defined by `faces` (triangles) + `boundary_facets` (polygons).

    The two inputs are complementary: together they should describe the PLC
    boundary, without repeating the same geometric facet in both forms.
    """
    V, F = _ensure_ndarray(vertices, faces)
    B = _normalize_boundary_facets(boundary_facets)
    B_markers = None
    if boundary_facet_markers is not None:
        B_markers = np.asarray(
            _normalize_boundary_facet_markers(boundary_facets, boundary_facet_markers),
            dtype=np.int32,
        )

    if tetgen_switches is not None and (
        switches_params is not None or switches_overrides is not None
    ):
        raise ValueError(
            "tetgen_switches is mutually exclusive with switches_params and switches_overrides"
        )

    F_markers = None
    if face_markers is not None:
        F_markers = np.asarray(face_markers, dtype=np.int32)
        if F_markers.ndim != 1:
            raise ValueError("face_markers must be a 1D sequence of integers")
        if F_markers.shape[0] != F.shape[0]:
            raise ValueError("face_markers must have the same length as faces")

    tetgen_switch_input: RawTetgenSwitches
    if tetgen_switches is not None:
        tetgen_switch_input = tetgen_switches
    else:
        s_params = dict(switches_params or {})
        if return_faces or return_boundary_faces:
            s_params["output_faces"] = True
        if return_edges:
            s_params["output_edges"] = True
        if return_neighbors or return_boundary_faces:
            s_params["output_neighbors"] = True

        s_over = dict(switches_overrides or {})
        tetgen_switch_input = switches.build_tetgen_switches(params=s_params, **s_over)

    raw_io = _tetwrap._tetrahedralize(
        V,
        F,
        F_markers,
        B,
        tetgen_switch_input,
        return_boundary_faces,
        B_markers,
    )
    io = TetwrapIO(raw_io, interior_default=interior_default)

    if return_io:
        return io

    points = np.asarray(io.points)
    tets = np.asarray(io.tets)
    tri_faces = None if io.tri_faces is None else np.asarray(io.tri_faces)
    boundary_tri_faces = None if io.boundary_tri_faces is None else np.asarray(io.boundary_tri_faces)
    boundary_tri_markers = None if io.boundary_tri_markers is None else np.asarray(io.boundary_tri_markers)
    edges = None if io.edges is None else np.asarray(io.edges)
    neighbors = None if io.neighbors is None else np.asarray(io.neighbors)

    return (
        points,
        tets,
        tri_faces,
        edges,
        neighbors,
        boundary_tri_faces,
        boundary_tri_markers,
    )


__all__ = ["tetrahedralize", "TetwrapIO"]
