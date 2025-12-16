from __future__ import annotations

import os
import subprocess
from pathlib import Path


KLAYOUT_EXE = os.environ.get("KLAYOUT_EXE", "").strip().strip('"')


def _require_klayout_exe() -> str:
    if not KLAYOUT_EXE:
        raise RuntimeError(
            "KLAYOUT_EXE is not set.\n"
            'Set it once (then open a new terminal):\n'
            '  setx KLAYOUT_EXE "C:\\Users\\racco\\AppData\\Roaming\\KLayout\\klayout_app.exe"\n'
        )
    p = Path(KLAYOUT_EXE)
    if not p.exists():
        raise RuntimeError(f"KLAYOUT_EXE does not exist: {p}")
    return str(p)


def ensure_macro(macro_path: Path) -> None:
    macro_path.parent.mkdir(parents=True, exist_ok=True)
    macro_path.write_text(
        """\
import pya

app = pya.Application.instance()

in_gds = app.get_config("in_gds") or ""
out_png = app.get_config("out_png") or ""
w_px = int(app.get_config("w_px") or "1600")
h_px = int(app.get_config("h_px") or "1200")

if not in_gds or not out_png:
    raise RuntimeError("Need -rd in_gds=... and -rd out_png=...")

ly = pya.Layout()
ly.read(in_gds)

lv = pya.LayoutView()
lv.load_layout(ly)
lv.max_hier()
lv.zoom_fit()

img = lv.get_image(w_px, h_px)
img.save(out_png)
""",
        encoding="utf-8",
    )


def render_gds_to_png(
    gds_path: str | Path,
    png_path: str | Path,
    *,
    w_px: int = 1600,
    h_px: int = 1200,
) -> None:
    gds_path = Path(gds_path).resolve()
    png_path = Path(png_path).resolve()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    if not gds_path.exists():
        raise FileNotFoundError(gds_path)

    klayout_exe = _require_klayout_exe()
    macro_path = Path(__file__).with_name("klayout_render_png.py")
    ensure_macro(macro_path)

    cmd = [
        klayout_exe,
        "-b",
        "-r",
        str(macro_path),
        "-rd",
        f"in_gds={gds_path}",
        "-rd",
        f"out_png={png_path}",
        "-rd",
        f"w_px={w_px}",
        "-rd",
        f"h_px={h_px}",
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            "KLayout render failed.\n"
            f"CMD: {' '.join(cmd)}\n\n"
            f"STDOUT:\n{r.stdout}\n\n"
            f"STDERR:\n{r.stderr}\n"
        )


if __name__ == "__main__":
    # Example usage:
    # python render_gds_to_png.py input.gds output.png
    import sys

    if len(sys.argv) < 3:
        print("Usage: python render_gds_to_png.py <input.gds> <output.png> [w_px] [h_px]")
        raise SystemExit(2)

    gds_in = sys.argv[1]
    png_out = sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) >= 4 else 1600
    h = int(sys.argv[4]) if len(sys.argv) >= 5 else 1200

    render_gds_to_png(gds_in, png_out, w_px=w, h_px=h)
    print(f"[OK] {png_out}")
