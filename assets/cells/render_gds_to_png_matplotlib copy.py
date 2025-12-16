from __future__ import annotations

from pathlib import Path
import gdstk
import matplotlib.pyplot as plt


def gds_to_png(
    gds_path: str | Path,
    png_path: str | Path,
    *,
    dpi: int = 250,
    pad_frac: float = 0.03,
    flatten: bool = True,
) -> None:
    gds_path = Path(gds_path).resolve()
    png_path = Path(png_path).resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    lib = gdstk.read_gds(str(gds_path))
    tops = lib.top_level()
    if not tops:
        raise RuntimeError(f"No top-level cells found in: {gds_path}")
    top = tops[0]

    cell = top.flatten() if flatten else top

    # Collect polygons + convert paths to polygons
    polygons = list(cell.polygons)
    for p in cell.paths:
        polygons.extend(p.to_polygons())

    if not polygons:
        raise RuntimeError(
            f"No geometry found to render in {gds_path}. If your layout is hierarchical, set flatten=True."
        )

    # Compute bounds
    bbox = cell.bounding_box()
    if bbox is None:
        raise RuntimeError("Could not compute bounding box.")
    (xmin, ymin), (xmax, ymax) = bbox
    dx = max(xmax - xmin, 1.0)
    dy = max(ymax - ymin, 1.0)
    pad = pad_frac * max(dx, dy)

    fig, ax = plt.subplots()
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    for poly in polygons:
        pts = poly.points
        ax.fill(pts[:, 0], pts[:, 1])

    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)

    fig.savefig(str(png_path), dpi=dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python gds_to_png.py <input.gds> <output.png>")
        raise SystemExit(2)

    gds_to_png(sys.argv[1], sys.argv[2])
    print(f"[OK] {sys.argv[2]}")
