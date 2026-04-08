# DTCC TetGen Wrapper

DTCC TetGen Wrapper provides Python bindings for TetGen and volume meshing
support for DTCC Platform.

This project is part of the
[Digital Twin Platform (DTCC Platform)](https://github.com/dtcc-platform/)
developed at the
[Digital Twin Cities Centre](https://dtcc.chalmers.se/)
supported by Sweden's Innovation Agency Vinnova under Grant No. 2019-421 00041.

## Documentation

Usage notes and examples are provided in this README, in
[`demos/demo.py`](demos/demo.py), and in the test suite under [`tests/`](tests/).

## Installation

Install from PyPI:

```bash
pip install dtcc-tetgen-wrapper
```

To build from source, first vendor TetGen into the package:

```bash
git clone https://github.com/dtcc-platform/dtcc-tetgen-wrapper.git
cd dtcc-tetgen-wrapper
./vendor_tetgen.sh
pip install .
```

If you want a different TetGen version, set `TETGEN_VERSION` before running
`vendor_tetgen.sh`.

## Usage

The wrapper targets manifold triangle surfaces described as a piecewise linear
complex (PLC). The main entry point is `tetrahedralize()`, which accepts NumPy
arrays and returns either a `TetwrapIO` object or raw output arrays.

```python
import numpy as np
from dtcc_tetgen_wrapper import tetrahedralize

vertices = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 1.0],
    ],
    dtype=float,
)

faces = np.array(
    [
        [0, 1, 2],
        [0, 2, 3],
        [4, 5, 6],
        [4, 6, 7],
        [0, 1, 5],
        [0, 5, 4],
        [1, 2, 6],
        [1, 6, 5],
        [2, 3, 7],
        [2, 7, 6],
        [3, 0, 4],
        [3, 4, 7],
    ],
    dtype=np.int64,
)

boundary_facets = {
    "bottom": [0, 1, 2, 3],
    "top": [4, 5, 6, 7],
    "south": [0, 1, 5, 4],
    "east": [1, 2, 6, 5],
    "north": [2, 3, 7, 6],
    "west": [3, 0, 4, 7],
}

mesh = tetrahedralize(
    vertices,
    faces,
    boundary_facets,
    switches_params={"quality": (1.6, 25.0), "max_volume": 0.02},
    switches_overrides={"quiet": True},
)

points = mesh.points
tets = mesh.tets
```

`faces` and `boundary_facets` jointly define the PLC. Do not describe the same
surface patch twice, for example by triangulating a wall in `faces` and also
listing that wall again in `boundary_facets`.

If you want to pass a raw TetGen switch string instead of structured switch
parameters, use `tetgen_switches=...`.

## Development Notes

Run the wrapper test suite with:

```bash
pytest tests
```

The wrapper writes native TetGen repro files on failure, including a `.poly`
file, so failing inputs can be reproduced directly with the TetGen CLI.

## Authors (in order of appearance)

* [George Spaias](mailto:gspaiasa@ece.auth.gr)
* [Anders Logg](http://anders.logg.org)

## License

This project is licensed under the
[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html).

TetGen itself is also AGPL-licensed. Any software using this wrapper must
comply with the AGPL terms.

## Community guidelines

Comments, contributions, and questions are welcome. Please engage with
us through Issues, Pull Requests, and Discussions on our GitHub page.
