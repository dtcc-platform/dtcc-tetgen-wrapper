"""Build TetGen command-line switches from descriptive kwargs.
This file intentionally has no dtcc dependency.
"""

from copy import deepcopy
from typing import Any, Dict, Optional, Union

DEFAULT_TETGEN_PARAMS = {
    # Core
    "plc": True,                    # -p : input is a PLC
    "preserve_surface": False,      # -Y : keep input surface unchanged
    "reconstruct": False,           # -r : reconstruct a previous mesh
    "coarsen": False,               # -R : coarsen mesh
    "assign_region_attributes": False,  # -A

    # Sizing / quality
    "quality": None,                # -q{val} or -q if True
    "max_volume": None,             # -a{val} or -a if True (per-region)
    "sizing_function": None,        # -m{token} or -m if True
    "insert_points": None,          # -i{token} or -i if True
    "optimize_level": None,         # -O{int}
    "optimize_max_dihedral": None,  # -o/#{deg}
    "optimize_max_aspect_ratio": None,  # -o//#{ratio}
    "max_added_points": None,       # -S{int}
    "coplanar_tolerance": None,     # -T{float}

    # Numerical / topology
    "no_exact_arithmetic": False,   # -X
    "no_merge_coplanar": False,     # -M
    "weighted_delaunay": False,     # -w
    "keep_convex_hull": False,      # -c
    "detect_self_intersections": False,  # -d

    # Numbering / output control
    "zero_numbering": False,        # -z (output files start from 0)
    "output_faces": False,          # -f
    "output_edges": False,          # -e
    "output_neighbors": False,      # -n
    "output_voronoi": False,        # -v
    "output_medit_mesh": False,     # -g
    "output_vtk": False,            # -k
    "no_jettison_unused_vertices": False,  # -J
    "suppress_boundary_output": False,     # -B
    "suppress_node_file": False,    # -N
    "suppress_ele_file": False,     # -E
    "suppress_face_edge_files": False,     # -F
    "suppress_iteration_numbers": False,   # -I
    "check_mesh": False,            # -C

    # Verbosity
    "quiet": False,                 # -Q
    "verbose": False,               # -V

    # Misc
    "help": False,                  # -h
    "extra": "",                    # anything to append verbatim
    # Alias: if you prefer `refine=True` to mean bare `-q`
    "refine": False,                # -> -q (only if quality is None)
}


def tetgen_defaults() -> Dict[str, Any]:
    """Get a deep copy of the default TetGen parameters.

    Returns:
        A dictionary with default TetGen parameter values.
    """
    return deepcopy(DEFAULT_TETGEN_PARAMS)


def _fmt_num(x: Union[bool, int, float]) -> str:
    """Format a number for inclusion in TetGen switches.

    Args:
        x: Value to format (bool, int, or float).

    Returns:
        Formatted string representation.
    """
    if x is True:
        return ""
    if isinstance(x, float):
        return f"{x:g}"
    return str(x)


def _emit_q(cfg: Dict[str, Any]) -> str:
    """Build the quality switch string for TetGen.

    Args:
        cfg: Configuration dictionary with quality parameters.

    Returns:
        Quality switch string (e.g., "q", "q1.5", "q2/15").
    """
    ratio = cfg.get("radius_edge_ratio")
    angle = cfg.get("min_dihedral_angle")
    q = cfg.get("quality")

    if ratio is None and angle is None and q is None and not cfg.get("refine"):
        return ""

    # Parse compound forms
    if (ratio is None and angle is None) and q is not None:
        if q is True:
            return "q"
        if isinstance(q, (int, float)):
            ratio = q
        elif isinstance(q, (tuple, list)) and len(q) == 2:
            ratio, angle = q
        elif isinstance(q, dict):
            ratio = q.get("ratio", ratio)
            angle = q.get("min_dihedral", angle)
        else:
            raise ValueError("quality must be True | number | (ratio, angle) | {'ratio':..,'min_dihedral':..}")

    if q is None and cfg.get("refine"):
        return "q"

    s = "q"
    if ratio is not None:
        s += _fmt_num(ratio)
        if angle is not None:
            s += f"/{_fmt_num(angle)}"
    elif angle is not None:
        s += f"/{_fmt_num(angle)}"
    return s


def build_tetgen_switches(params: Optional[Dict[str, Any]] = None, **overrides: Any) -> str:
    """Build TetGen command-line switches from parameters.

    Args:
        params: Optional dictionary of TetGen parameters.
        **overrides: Keyword arguments to override params.

    Returns:
        String of concatenated TetGen switches.

    Raises:
        ValueError: If mutually exclusive options are specified.
    """
    cfg = tetgen_defaults()
    if params:
        cfg.update(params)
    if overrides:
        cfg.update(overrides)

    if cfg["quiet"] and cfg["verbose"]:
        raise ValueError("`quiet` (-Q) and `verbose` (-V) are mutually exclusive.")

    parts = []

    toggles = [
        ("plc", "p"),
        ("preserve_surface", "Y"),
        ("reconstruct", "r"),
        ("coarsen", "R"),
        ("assign_region_attributes", "A"),
        ("no_exact_arithmetic", "X"),
        ("no_merge_coplanar", "M"),
        ("weighted_delaunay", "w"),
        ("keep_convex_hull", "c"),
        ("detect_self_intersections", "d"),
        ("zero_numbering", "z"),
        ("output_faces", "f"),
        ("output_edges", "e"),
        ("output_neighbors", "n"),
        ("output_voronoi", "v"),
        ("output_medit_mesh", "g"),
        ("output_vtk", "k"),
        ("no_jettison_unused_vertices", "J"),
        ("suppress_boundary_output", "B"),
        ("suppress_node_file", "N"),
        ("suppress_ele_file", "E"),
        ("suppress_face_edge_files", "F"),
        ("suppress_iteration_numbers", "I"),
        ("check_mesh", "C"),
        ("quiet", "Q"),
        ("verbose", "V"),
        ("help", "h"),
    ]

    for key, flag in toggles:
        if cfg.get(key):
            parts.append(flag)

    # Quality
    q_str = _emit_q(cfg)
    if q_str:
        parts.append(q_str)

    # Max volume: -a or -a{val}
    a = cfg.get("max_volume")
    if a is not None:
        parts.append("a" + _fmt_num(a))

    # -m{token}
    m = cfg.get("sizing_function")
    if m is not None:
        parts.append("m" + ("" if m is True else str(m)))

    # -i{token}
    i = cfg.get("insert_points")
    if i is not None:
        parts.append("i" + ("" if i is True else str(i)))

    # -O{int}
    O = cfg.get("optimize_level")
    if O is not None:
        parts.append("O" + _fmt_num(O))

    # -o/#{deg} and -o//#{ratio}
    opt_max_dihedral = cfg.get("optimize_max_dihedral")
    opt_max_aspect_ratio = cfg.get("optimize_max_aspect_ratio")
    if opt_max_dihedral is not None or opt_max_aspect_ratio is not None:
        o = "o"
        if opt_max_dihedral is not None:
            o += "/" + _fmt_num(opt_max_dihedral)
        if opt_max_aspect_ratio is not None:
            o += "//" if opt_max_dihedral is not None else "//"
            o += _fmt_num(opt_max_aspect_ratio)
        parts.append(o)

    # -S{int}
    S = cfg.get("max_added_points")
    if S is not None:
        parts.append("S" + _fmt_num(S))

    # -T{float}
    T = cfg.get("coplanar_tolerance")
    if T is not None:
        parts.append("T" + _fmt_num(T))

    if cfg.get("extra"):
        parts.append(cfg["extra"])

    return "".join(parts)
