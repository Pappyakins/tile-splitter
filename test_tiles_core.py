"""Headless tests for tiles_core. Run: python test_tiles_core.py
Covers the grid workflow (regression), the mixed sizes workflow, and
the Roll to Film planner including the 1 mm safety margin rule."""
from PIL import Image, ImageDraw

import tiles_core as tc

PANELS = [(12.0, 16.0), (8.0, 10.0), (12.0, 16.0)]
GAP = 0.75


def approx(a, b, tol=0.05):
    assert abs(a - b) <= tol, f"{a} != {b} (tol {tol})"


def test_plan_mixed_geometry():
    plan = tc.plan_mixed(6700, 3200, PANELS, GAP, 300)
    tw, th = plan["total_in"]
    approx(tw, 33.5, 1e-9)
    approx(th, 16.0, 1e-9)
    t1, t2, t3 = plan["tiles"]
    approx(t1["x_in"], 0.0, 1e-9)
    approx(t2["x_in"], 12.75, 1e-9)
    approx(t3["x_in"], 21.5, 1e-9)
    approx(t1["y_in"], 0.0, 1e-9)
    approx(t2["y_in"], 3.0, 1e-9)
    approx(t3["y_in"], 0.0, 1e-9)
    # Source is exactly the arrangement aspect, so sx = sy = 200 px/in
    assert t1["box"] == (0, 0, 2400, 3200), t1["box"]
    assert t2["box"] == (2550, 600, 4150, 2600), t2["box"]
    assert t3["box"] == (4300, 0, 6700, 3200), t3["box"]
    assert t1["name"] == "tile_P1_12x16"
    assert t2["name"] == "tile_P2_8x10"
    assert t3["name"] == "tile_P3_12x16"


def test_split_mixed_exact_pixels():
    img = Image.new("RGB", (6700, 3200), (0, 0, 0))
    plan = tc.plan_mixed(6700, 3200, PANELS, GAP, 300)
    d = ImageDraw.Draw(img)
    colors = [(200, 30, 30), (30, 200, 30), (30, 30, 200)]
    for t, col in zip(plan["tiles"], colors):
        d.rectangle(t["box"], fill=col)
    tiles = tc.split_image(img, plan)
    assert tiles["tile_P1_12x16"].size == (3600, 4800)
    assert tiles["tile_P2_8x10"].size == (2400, 3000)
    assert tiles["tile_P3_12x16"].size == (3600, 4800)
    for name, col in zip(sorted(tiles), colors):
        piece = tiles[name]
        px = piece.getpixel((piece.size[0] // 2, piece.size[1] // 2))
        assert px == col, (name, px, col)


def test_assembly_map_and_job_summary_mixed():
    img = Image.new("RGB", (6700, 3200), (120, 120, 120))
    plan = tc.plan_mixed(6700, 3200, PANELS, GAP, 300)
    amap = tc.assembly_map_mixed(img, plan)
    assert amap.size == (1400, 669), amap.size
    text = tc.job_summary_mixed(plan, PANELS, GAP, 300, "photo.jpg")
    assert "Total wall size: 33.50 x 16.00 in" in text
    assert "tile_P1_12x16.png" in text
    assert "tile_P2_8x10.png" in text
    assert "tile_P3_12x16.png" in text
    assert "8 x 10 in" in text


def test_film_mixed_layout():
    pieces = [{"label": "P1", "w_in": 8.0, "h_in": 10.0},
              {"label": "P2", "w_in": 11.0, "h_in": 14.0},
              {"label": "P3", "w_in": 8.0, "h_in": 10.0}]
    fp = tc.plan_film_pieces(pieces, 305.0)
    assert fp["fits_all"] and not fp["flatbed"]
    approx(fp["usable_mm"], 304.0, 1e-9)
    p1, p2, p3 = fp["placements"]
    approx(p1["x"], 0.0)
    approx(p1["y"], 200.0)
    approx(p1["w"], 203.2)
    approx(p1["h"], 254.0)
    approx(p2["x"], 0.0)          # 11 in piece needs its own row
    approx(p2["y"], 464.0)
    approx(p3["y"], 829.6)
    approx(fp["total_mm"], 1093.6)
    text = tc.film_summary_pieces(fp)
    assert "304 mm printable width" in text


def test_film_mixed_lane_fit_and_layout_image():
    # P1 is 12 x 16 in: a lane fit on the roll, not flatbed. P2 is a
    # normal piece. Both place, and the layout image still renders.
    img = Image.new("RGB", (6700, 3200), (90, 90, 90))
    plan = tc.plan_mixed(6700, 3200, [(12.0, 16.0), (8.0, 10.0)], GAP, 300)
    pieces = [{"label": f"P{t['pos']}", "w_in": t["w_in"],
               "h_in": t["h_in"], "box": t["box"]} for t in plan["tiles"]]
    fp = tc.plan_film_pieces(pieces, 305.0)
    assert fp["fits_all"] and fp["flatbed"] == []
    assert len(fp["placements"]) == 2
    p1, p2 = fp["placements"]
    assert p1["lane"] is True and p2["lane"] is False
    approx(p1["w"], 304.0)        # placed at the printable width
    approx(p1["h"], 406.4)
    approx(p2["y"], 616.4)        # lane piece fills its row, P2 drops down
    fimg = tc.film_layout_image(img, plan, fp)
    assert fimg is not None  # long roll, schematic scales to max height


def test_film_mixed_partial_flatbed():
    img = Image.new("RGB", (6700, 3200), (90, 90, 90))
    plan = tc.plan_mixed(6700, 3200, [(16.0, 20.0), (8.0, 10.0)], GAP, 300)
    pieces = [{"label": f"P{t['pos']}", "w_in": t["w_in"],
               "h_in": t["h_in"], "box": t["box"]} for t in plan["tiles"]]
    fp = tc.plan_film_pieces(pieces, 305.0)
    assert len(fp["placements"]) == 1
    assert [f["name"] for f in fp["flatbed"]] == ["P1"]
    assert tc.film_layout_image(img, plan, fp) is not None


def test_film_12in_piece_is_lane_fit():
    # 12 x 16 in is 304.8 x 406.4 mm: over the 304 mm printable width
    # but no wider than the 305 mm film itself, so it is a lane fit,
    # NOT flatbed only. This is the standard 12 in lane case.
    fp = tc.plan_film_pieces([{"label": "P1", "w_in": 12.0, "h_in": 16.0}],
                             305.0)
    assert fp["fits_all"] and fp["flatbed"] == []
    assert len(fp["placements"]) == 1
    p = fp["placements"][0]
    assert p["lane"] is True and p["rotated"] is False
    approx(p["w"], 304.0)         # print sized to the printable width
    approx(p["h"], 406.4)
    approx(p["w_mm"], 304.8)      # the piece's true size is kept
    text = tc.film_summary_pieces(fp)
    assert "Lane fit" in text
    assert "prints centred at 304 mm on the 305 mm film" in text
    assert "trim the clear film edges flush" in text
    assert "Flatbed only" not in text


def test_film_lane_fit_layout_image_band():
    # The layout image draws the film width as a band with the lane
    # print centred in it: the strip beside the print stays band fill.
    img = Image.new("RGB", (2000, 2000), (50, 50, 50))
    plan = tc.plan_tiles(2000, 2000, 12, 16, 1, 1, 0.75, 300)
    fp = tc.plan_film(12, 16, 1, 305.0)
    assert fp["fits"] and fp["lane_count"] == 1
    fimg = tc.film_layout_image(img, plan, fp)
    assert fimg is not None and fimg.size[0] == int(round(305 * 3.0))
    # Band outline runs down both film edges beside the piece, and
    # the centred print covers the middle.
    assert fimg.getpixel((0, 700)) == (150, 140, 118)
    assert fimg.getpixel((914, 700)) == (150, 140, 118)
    assert fimg.getpixel((457, 700)) == (50, 50, 50)


def test_film_rotation():
    # 13 x 10 in is 330.2 x 254 mm: too wide upright, fits rotated.
    fp = tc.plan_film_pieces([{"label": "P1", "w_in": 13.0, "h_in": 10.0}],
                             305.0)
    assert fp["fits_all"] and len(fp["placements"]) == 1
    p = fp["placements"][0]
    assert p["rotated"] is True
    approx(p["w"], 254.0)
    approx(p["h"], 330.2)


def test_film_lane_fit_rotated():
    # 13 x 12 in: too wide upright (330.2 mm over the film), and the
    # 12 in side (304.8 mm) is over the printable width but within the
    # film, so it lane fits rotated.
    fp = tc.plan_film_pieces([{"label": "P1", "w_in": 13.0, "h_in": 12.0}],
                             305.0)
    assert fp["fits_all"] and len(fp["placements"]) == 1
    p = fp["placements"][0]
    assert p["lane"] is True and p["rotated"] is True
    approx(p["w"], 304.0)
    approx(p["h"], 330.2)


def test_film_16in_piece_flatbed():
    # 16 x 20 in is 406.4 x 508 mm: wider than the 305 mm film itself
    # either way up, still flatbed only.
    fp = tc.plan_film_pieces([{"label": "P1", "w_in": 16.0, "h_in": 20.0}],
                             305.0)
    assert fp["placements"] == [] and len(fp["flatbed"]) == 1
    text = tc.film_summary_pieces(fp)
    assert "Flatbed only" in text
    assert "wider than the 305 mm film itself even rotated" in text


def test_legacy_grid_plan_unchanged():
    plan = tc.plan_tiles(6000, 4000, 12, 16, 3, 1, 0.75, 300)
    assert plan["total_in"] == (37.5, 16.0)
    assert plan["out_px"] == (3600, 4800)
    assert [t["name"] for t in plan["tiles"]] == \
        ["tile_R1C1", "tile_R1C2", "tile_R1C3"]
    img = Image.new("RGB", (6000, 4000), (10, 20, 30))
    tiles = tc.split_image(img, plan)
    assert all(t.size == (3600, 4800) for t in tiles.values())
    amap = tc.assembly_map(img, plan, 0.75, 12, 16)
    assert amap.size[0] == 1400
    text = tc.job_summary(plan, 12, 16, 3, 1, 0.75, 300, "x.jpg")
    assert "Grid: 3 across x 1 down" in text


def test_legacy_film():
    fp = tc.plan_film(8, 10, 1, 305.0)
    assert fp["fits"] and fp["rotated"] is False and fp["per_row"] == 1
    assert fp["lane_count"] == 0
    approx(fp["total_mm"], 464.0)
    # A 12 in wide piece (304.8 mm) is the standard lane case: it runs
    # on the roll as a lane fit at the 304 mm printable width, so the
    # grid planner reports fits, one per row, all lane fit.
    fp2 = tc.plan_film(12, 16, 3, 305.0)
    assert fp2["fits"] is True and fp2["per_row"] == 1
    assert fp2["lane_count"] == 3
    text = tc.film_summary(fp2, 3)
    assert "Lane fit" in text
    assert "print centred at 304 mm on the 305 mm film" in text
    assert "trim the clear film edges flush" in text
    img = Image.new("RGB", (2000, 2000), (50, 50, 50))
    plan = tc.plan_tiles(2000, 2000, 8, 10, 1, 1, 0.75, 300)
    assert tc.film_layout_image(img, plan, fp) is not None


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"PASS {name}")
    print(f"ALL {len(tests)} TESTS PASSED")
