"""Targeted tests for the public tetrahedralize adapter."""

from __future__ import annotations

import numpy as np
import pytest

from dtcc_tetgen_wrapper import adapter
from dtcc_tetgen_wrapper.tetwrapio import TetwrapIO


class _DummyTetwrapResult:
    """Minimal stand-in for the pybind TetGen result."""

    def __init__(self) -> None:
        self.points = np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        self.tets = np.array([[0, 1, 2, 3]], dtype=np.int32)
        self.tri_faces = np.array([[0, 1, 2]], dtype=np.int32)
        self.boundary_tri_faces = np.array([[0, 2, 3]], dtype=np.int32)
        self.boundary_tri_markers = np.array([0, 2], dtype=np.int32)
        self.tri_markers = np.array([1, 0], dtype=np.int32)
        self.edges = np.array([[0, 1]], dtype=np.int32)
        self.neighbors = np.array([[0, 0, 0, 0]], dtype=np.int32)


def _vertices() -> np.ndarray:
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def _faces() -> np.ndarray:
    return np.array(
        [
            [0, 1, 2],
            [0, 1, 3],
            [0, 2, 3],
        ],
        dtype=np.int64,
    )


def _boundary() -> list[list[int]]:
    return [[0, 1, 2]]


def test_boundary_facets_are_required() -> None:
    """tetrahedralize rejects a missing boundary description."""
    with pytest.raises(ValueError):
        adapter.tetrahedralize(_vertices(), _faces(), None)  # type: ignore[arg-type]


def test_face_markers_match_face_count() -> None:
    """face_markers must be the same length as the provided faces."""
    with pytest.raises(ValueError, match="same length as faces"):
        adapter.tetrahedralize(_vertices(), _faces(), _boundary(), face_markers=[1])


def test_returns_tetwrap_io_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """When return_io is True (default) a TetwrapIO wrapper is produced."""
    dummy_result = _DummyTetwrapResult()
    captured = {}

    def _fake_tetrahedralize(
        V, F, F_markers, B, switch_str, ret_boundary, boundary_facet_markers=None
    ):
        captured["vertices"] = V
        captured["faces"] = F
        captured["face_markers"] = F_markers
        captured["boundary"] = B
        captured["boundary_facet_markers"] = boundary_facet_markers
        captured["switch_str"] = switch_str
        captured["return_boundary_faces"] = ret_boundary
        return dummy_result

    monkeypatch.setattr(adapter._tetwrap, "_tetrahedralize", _fake_tetrahedralize)

    io = adapter.tetrahedralize(
        _vertices(),
        _faces(),
        _boundary(),
        face_markers=[3, 3, 3],
        switches_params={"quality": 2},
    )

    assert isinstance(io, TetwrapIO)
    assert io.raw() is dummy_result

    assert np.allclose(captured["vertices"], _vertices())
    assert captured["faces"].dtype == np.int64
    assert captured["face_markers"].dtype == np.int32
    assert captured["boundary"] == [[0, 1, 2]]
    assert captured["boundary_facet_markers"] is None
    # Defaults enable PLC (-p) and our quality request adds q2.
    assert "p" in captured["switch_str"]
    assert "q2" in captured["switch_str"]
    assert captured["return_boundary_faces"] is False


def test_raw_switch_string_is_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """A raw TetGen switch string can be supplied directly."""
    dummy_result = _DummyTetwrapResult()
    captured = {}

    def _fake_tetrahedralize(
        V, F, F_markers, B, switch_str, ret_boundary, boundary_facet_markers=None
    ):
        captured["switch_str"] = switch_str
        return dummy_result

    monkeypatch.setattr(adapter._tetwrap, "_tetrahedralize", _fake_tetrahedralize)

    adapter.tetrahedralize(
        _vertices(),
        _faces(),
        _boundary(),
        tetgen_switches="pQq1.6a0.1",
    )

    assert captured["switch_str"] == "pQq1.6a0.1"


def test_raw_switch_string_conflicts_with_structured_switches() -> None:
    """Raw and structured switch inputs are mutually exclusive."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        adapter.tetrahedralize(
            _vertices(),
            _faces(),
            _boundary(),
            tetgen_switches="pQ",
            switches_params={"quality": 2.0},
        )


def test_requesting_outputs_sets_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requesting faces/edges/neighbors toggles the associated TetGen switches."""
    dummy_result = _DummyTetwrapResult()
    called = {}

    def _fake_tetrahedralize(
        V, F, F_markers, B, switch_str, ret_boundary, boundary_facet_markers=None
    ):
        called["switch_str"] = switch_str
        called["return_boundary_faces"] = ret_boundary
        return dummy_result

    monkeypatch.setattr(adapter._tetwrap, "_tetrahedralize", _fake_tetrahedralize)

    result = adapter.tetrahedralize(
        _vertices(),
        _faces(),
        {"top": [0, 1, 2]},
        return_io=False,
        return_faces=True,
        return_edges=True,
        return_neighbors=True,
        return_boundary_faces=True,
    )

    assert called["return_boundary_faces"] is True
    for flag in ("f", "e", "n"):
        assert flag in called["switch_str"]

    assert isinstance(result, tuple)
    assert len(result) == 7
    points, tets, tri_faces, edges, neighbors, boundary_faces, boundary_markers = result
    assert isinstance(points, np.ndarray)
    assert isinstance(boundary_markers, np.ndarray)
    # Markers are normalized: 0 -> default (-10), positives are shifted down.
    assert set(boundary_markers.tolist()) == {-10, 1}


def test_named_boundary_facets_follow_dtcc_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Named bbox facets normalize to the dtcc face-marker order."""
    dummy_result = _DummyTetwrapResult()
    captured = {}

    def _fake_tetrahedralize(
        V, F, F_markers, B, switch_str, ret_boundary, boundary_facet_markers=None
    ):
        captured["boundary"] = B
        return dummy_result

    monkeypatch.setattr(adapter._tetwrap, "_tetrahedralize", _fake_tetrahedralize)

    adapter.tetrahedralize(
        _vertices(),
        _faces(),
        {
            "south": [0, 1, 2],
            "east": [0, 1, 3],
            "north": [0, 2, 3],
            "west": [1, 2, 3],
            "top": [0, 1, 2, 3],
        },
        tetgen_switches="pQ",
    )

    assert captured["boundary"] == [
        [0, 1, 2, 3],
        [1, 2, 3],
        [0, 1, 3],
        [0, 1, 2],
        [0, 2, 3],
    ]


def test_boundary_facet_markers_follow_normalized_named_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Named boundary facet markers are aligned with the normalized facet order."""
    dummy_result = _DummyTetwrapResult()
    captured = {}

    def _fake_tetrahedralize(
        V, F, F_markers, B, switch_str, ret_boundary, boundary_facet_markers=None
    ):
        captured["boundary_facet_markers"] = boundary_facet_markers
        return dummy_result

    monkeypatch.setattr(adapter._tetwrap, "_tetrahedralize", _fake_tetrahedralize)

    adapter.tetrahedralize(
        _vertices(),
        _faces(),
        {
            "south": [0, 1, 2],
            "east": [0, 1, 3],
            "north": [0, 2, 3],
            "west": [1, 2, 3],
            "top": [0, 1, 2, 3],
        },
        boundary_facet_markers={
            "south": -5,
            "east": -4,
            "north": -6,
            "west": -3,
            "top": -2,
        },
        tetgen_switches="pQ",
    )

    assert captured["boundary_facet_markers"].tolist() == [-2, -3, -4, -5, -6]


def test_native_box_smoke_reports_effective_switches() -> None:
    """A small valid PLC tetrahedralizes through the compiled extension."""
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    boundary = {
        "south": [0, 1, 6, 4],
        "east": [1, 2, 7, 6],
        "north": [2, 3, 5, 7],
        "west": [3, 0, 4, 5],
        "top": [4, 6, 7, 5],
    }

    io = adapter.tetrahedralize(
        vertices,
        faces,
        boundary,
        boundary_facet_markers={
            "south": -5,
            "east": -4,
            "north": -6,
            "west": -3,
            "top": -2,
        },
        tetgen_switches="pQ",
        return_boundary_faces=True,
    )

    assert io.points.shape[1] == 3
    assert io.tets.shape[1] == 4
    assert io.boundary_tri_faces is not None
    assert io.boundary_tri_faces.shape[1] == 3
    assert set(np.unique(io.boundary_tri_markers)).issuperset({-1, -2, -3, -4, -5, -6})
    assert io.switches == "pQnf"
