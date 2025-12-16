# render_gds_to_png_matplotlib.py
from __future__ import annotations

from pathlib import Path
import math

import yaml
import gdstk
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon


# =========================
# User config (edit these)
# =========================
INPUT_GDS = r"docs_site/assets/cells/straight_cpw.gds"
OUTPUT_PNG = r"docs_site/assets/cells/straight_cpw.png"
INPUT_GDS = r"straight_cpw.gds"
OUTPUT_PNG = r"straight_cpw.png"

LAYER_STACK_YAML = r"arena_v0p2_layer_stack_chip2chip_10um.yaml"  # set "" to disable yaml colors

FIG_W_IN = 10.0
FIG_H_IN = 6.0
DPI = 200

BACKGROUND = "#0b0f14"
DEFAULT_RGB = (0.90, 0.92, 0.96)  # if not found in YAML
DEFAULT_ALPHA_UNKNOWN = 0.5  # your requirement

EDGE_ALPHA_SCALE = 0.90
EDGE_LINEWIDTH = 0.20

PAD_FRAC = 0.08  # 8% padding


# =========================
# Helpers
# =========================
def _rgba255_to_rgba01(rgba255: list[int] | tuple[int, int, int, int]) -> tuple[float, float, float, float]:
    r, g, b, a = [int(x) for x in rgba255]
    r = max(0, min(255, r)) / 255.0
    g = max(0, min(255, g)) / 255.0
    b = max(0, min(255, b)) / 255.0
    a = max(0, min(255, a)) / 255.0
    return (r, g, b, a)


def load_layer_colors_from_yaml(yaml_path: str) -> dict[tuple[int, int], tuple[float, float, float, float]]:
    """
    Parses YOUR YAML format:

    layer_stack:
      QM1F_cpwsig:
        layer: [1, 0]
        info:
          color: [255, 128, 0, 255]

    Returns mapping: (layer, datatype) -> (r,g,b,a) where each is 0..1
    """
    if not yaml_path:
        return {}

    p = Path(yaml_path)
    if not p.exists():
        raise FileNotFoundError(f"Layer stack YAML not found: {p.resolve()}")

    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    stack = data.get("layer_stack", {})
    if not isinstance(stack, dict):
        return {}

    out: dict[tuple[int, int], tuple[float, float, float, float]] = {}

    for _name, spec in stack.items():
        if not isinstance(spec, dict):
            continue

        ld = spec.get("layer")
        if not (isinstance(ld, (list, tuple)) and len(ld) == 2):
            continue
        layer, datatype = int(ld[0]), int(ld[1])

        info = spec.get("info", {})
        if not isinstance(info, dict):
            continue

        rgba255 = info.get("color")
        if not (isinstance(rgba255, (list, tuple)) and len(rgba255) == 4):
            continue

        out[(layer, datatype)] = _rgba255_to_rgba01(rgba255)

    return out


def iter_polygons_from_gds(gds_path: str, *, flatten: bool = True):
    """
    Returns list of tuples: (layer, datatype, points[N,2])

    Handles:
    - BOUNDARY polygons (cell.polygons)
    - PATH elements (cell.paths) converted to polygons
    - referenced subcells (optional flatten)
    """
    lib = gdstk.read_gds(gds_path)

    # Pick top cell(s)
    tops = lib.top_level()
    if not tops:
        raise RuntimeError(f"No top-level cells found in GDS: {gds_path}")

    polys_out: list[tuple[int, int, list[tuple[float, float]]]] = []

    for top in tops:
        cell = top
        if flatten:
            # Flatten to pull geometry from references into this cell
            cell = cell.copy(f"{cell.name}__flat")
            cell.flatten()

        # 1) Normal polygons (BOUNDARY)
        for poly in cell.polygons:
            layer = int(poly.layer)
            datatype = int(poly.datatype)
            pts = [(float(x), float(y)) for (x, y) in poly.points]
            if len(pts) >= 3:
                polys_out.append((layer, datatype, pts))

        # 2) Paths (PATH) -> polygons
        for path in cell.paths:
            layer = int(path.layer)
            datatype = int(path.datatype)
            # Convert path stroke to polygon(s)
            for p in path.to_polygons():
                pts = [(float(x), float(y)) for (x, y) in p.points]
                if len(pts) >= 3:
                    polys_out.append((layer, datatype, pts))

    return polys_out


def compute_bbox(polys: list[tuple[int, int, list[tuple[float, float]]]]):
    if not polys:
        return (0.0, 0.0, 1.0, 1.0)

    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")

    for _, _, pts in polys:
        for x, y in pts:
            xmin = min(xmin, x)
            ymin = min(ymin, y)
            xmax = max(xmax, x)
            ymax = max(ymax, y)

    if not math.isfinite(xmin) or not math.isfinite(ymin):
        return (0.0, 0.0, 1.0, 1.0)

    if xmin == xmax:
        xmax = xmin + 1.0
    if ymin == ymax:
        ymax = ymin + 1.0

    return (xmin, ymin, xmax, ymax)


# =========================
# Main "script-like" flow
# =========================
def render():
    gds_path = Path(INPUT_GDS)
    png_path = Path(OUTPUT_PNG)

    if not gds_path.exists():
        raise FileNotFoundError(f"INPUT_GDS not found: {gds_path.resolve()}")

    layer_colors = load_layer_colors_from_yaml(LAYER_STACK_YAML)

    polys = iter_polygons_from_gds(str(gds_path))
    if not polys:
        raise RuntimeError(f"No polygons found in GDS: {gds_path.resolve()}")

    # Draw order:
    # larger L drawn first; for same L, larger D drawn first.
    # Later draws are on top => smaller D (e.g. 1/0) ends up on top of 1/11.
    polys_sorted = sorted(polys, key=lambda t: (t[0], t[1]), reverse=True)

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI)
    ax = fig.add_subplot(1, 1, 1)
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(BACKGROUND)

    default_rgba_unknown = (DEFAULT_RGB[0], DEFAULT_RGB[1], DEFAULT_RGB[2], DEFAULT_ALPHA_UNKNOWN)

    for layer, datatype, pts in polys_sorted:
        rgba = layer_colors.get((layer, datatype), default_rgba_unknown)

        edge_rgba = (rgba[0], rgba[1], rgba[2], max(0.0, min(1.0, rgba[3] * EDGE_ALPHA_SCALE)))

        patch = MplPolygon(
            pts,
            closed=True,
            facecolor=rgba,
            edgecolor=edge_rgba,
            linewidth=EDGE_LINEWIDTH,
            antialiased=True,
        )
        ax.add_patch(patch)

    xmin, ymin, xmax, ymax = compute_bbox(polys)
    dx = max(xmax - xmin, 1.0)
    dy = max(ymax - ymin, 1.0)
    pad = PAD_FRAC * max(dx, dy)

    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        png_path,
        dpi=DPI,
        bbox_inches="tight",
        pad_inches=0.02,
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    print(f"[OK] PNG: {png_path.resolve()}")


if __name__ == "__main__":
    render()
