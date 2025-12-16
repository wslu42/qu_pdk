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
