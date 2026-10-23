"""Core image tiling logic for Tile Splitter (no GUI dependencies).

Takes a picture and splits it into print-ready tiles for multi-panel
wall art (triptychs, grids). The hanging gap between panels is part of
the math: each tile samples its window with a stride of tile + gap, so
when the panels hang with that gap, the picture lines up across them.
"""
from PIL import Image, ImageDraw, ImageFont


def plan_tiles(img_w, img_h, tile_w_in, tile_h_in, cols, rows, gap_in, dpi):
    """Return a plan dict: crop box on the source, per-tile source windows
    and output pixel sizes, total wall size, effective source dpi."""
    total_w_in = cols * tile_w_in + (cols - 1) * gap_in
    total_h_in = rows * tile_h_in + (rows - 1) * gap_in
    target = total_w_in / total_h_in
    src = img_w / img_h
    if src > target:
        crop_h = img_h
        crop_w = int(round(img_h * target))
    else:
        crop_w = img_w
        crop_h = int(round(img_w / target))
    x0 = (img_w - crop_w) // 2
    y0 = (img_h - crop_h) // 2
    sx = crop_w / total_w_in   # source px per wall inch (x)
    sy = crop_h / total_h_in   # source px per wall inch (y)
    out_w = int(round(tile_w_in * dpi))
    out_h = int(round(tile_h_in * dpi))
    tiles = []
    for r in range(rows):
        for c in range(cols):
            ix = x0 + int(round(c * (tile_w_in + gap_in) * sx))
            iy = y0 + int(round(r * (tile_h_in + gap_in) * sy))
            iw = int(round(tile_w_in * sx))
            ih = int(round(tile_h_in * sy))
            tiles.append({
                "row": r + 1, "col": c + 1,
                "box": (ix, iy, ix + iw, iy + ih),
                "out": (out_w, out_h),
                "name": f"tile_R{r + 1}C{c + 1}",
            })
    return {
        "crop": (x0, y0, x0 + crop_w, y0 + crop_h),
        "total_in": (total_w_in, total_h_in),
        "tiles": tiles,
        "eff_dpi": min(sx, sy),
        "out_px": (out_w, out_h),
    }


def split_image(img, plan, out_fmt="PNG"):
    """Cut the tiles per plan. Returns {name: PIL.Image} at print size."""
    result = {}
    for t in plan["tiles"]:
        piece = img.crop(t["box"]).resize(t["out"], Image.LANCZOS)
        result[t["name"]] = piece
    return result


def assembly_map(img, plan, gap_in, tile_w_in, tile_h_in, max_w=1400):
    """A labelled preview showing how the tiles reassemble on the wall.
    Tiles are drawn at their wall positions with the real gap, each
    labelled R{row}C{col}, over a neutral backdrop."""
    tw, th = plan["total_in"]
    scale = max_w / tw
    W = int(round(tw * scale))
    H = int(round(th * scale))
    canvas = Image.new("RGB", (W, H), (38, 38, 42))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            max(16, int(tile_h_in * scale * 0.16)))
    except Exception:
        font = ImageFont.load_default()
    sx_img = img.size[0]
    for t in plan["tiles"]:
        c, r = t["col"] - 1, t["row"] - 1
        dx = int(round((c * (tile_w_in + gap_in)) * scale))
        dy = int(round((r * (tile_h_in + gap_in)) * scale))
        dw = int(round(tile_w_in * scale))
        dh = int(round(tile_h_in * scale))
        piece = img.crop(t["box"]).resize((dw, dh), Image.LANCZOS)
        canvas.paste(piece, (dx, dy))
        label = f"R{t['row']}C{t['col']}"
        pad = 6
        bbox = d.textbbox((0, 0), label, font=font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.rectangle([dx + pad, dy + pad, dx + pad + lw + 12, dy + pad + lh + 10],
                    fill=(0, 0, 0))
        d.text((dx + pad + 6, dy + pad + 4), label, fill=(255, 210, 90), font=font)
    return canvas


def job_summary(plan, tile_w_in, tile_h_in, cols, rows, gap_in, dpi, src_name,
                film_text=""):
    tw, th = plan["total_in"]
    ow, oh = plan["out_px"]
    lines = [
        f"Tile Splitter job",
        f"Source picture: {src_name}",
        f"Grid: {cols} across x {rows} down",
        f"Each tile: {tile_w_in} x {tile_h_in} in  ->  {ow} x {oh} px at {dpi} DPI",
        f"Hanging gap: {gap_in} in (already in the math, hang panels with this gap)",
        f"Total wall size: {tw:.2f} x {th:.2f} in "
        f"({tw * 2.54:.1f} x {th * 2.54:.1f} cm)",
        f"Tiles: {len(plan['tiles'])} files, named tile_R<row>C<col>",
        f"Source resolution over the artwork: about {plan['eff_dpi']:.0f} px per inch",
    ]
    if film_text:
        lines += ["", film_text]
    return "\n".join(lines) + "\n"


# ================= Roll to Film (eufyMake E1 attachment) =================
# Official figures: film 100-305 mm wide, up to 10 m continuous per job,
# about 15-20 cm of blank leader before the first print.
FILM_WIDTH_MM = 305.0
FILM_LEADER_MM = 200.0
FILM_MAX_JOB_MM = 10000.0
FILM_CUT_GAP_MM = 10.0


def plan_film(tile_w_in, tile_h_in, count, film_width_mm=FILM_WIDTH_MM):
    """Lay identical pieces down a film roll, shelf style.
    Each piece is used upright when it fits the film width, rotated 90
    degrees when only the long side fits across, and flagged when it
    cannot fit either way. Returns placements in mm from the roll top
    (leader included) plus the total film length."""
    w = tile_w_in * 25.4
    h = tile_h_in * 25.4
    fits_up = w <= film_width_mm
    fits_rot = h <= film_width_mm
    if fits_up:
        pw, ph, rotated = w, h, False
    elif fits_rot:
        pw, ph, rotated = h, w, True
    else:
        return {"fits": False, "placements": [], "rotated": False,
                "piece_mm": (w, h), "total_mm": 0.0,
                "film_width_mm": film_width_mm}
    per_row = max(1, int((film_width_mm + FILM_CUT_GAP_MM) //
                         (pw + FILM_CUT_GAP_MM)))
    placements = []
    y = FILM_LEADER_MM
    x = 0.0
    in_row = 0
    for i in range(count):
        if in_row == per_row:
            y += ph + FILM_CUT_GAP_MM
            x = 0.0
            in_row = 0
        placements.append({"name": f"piece {i + 1}", "x": x, "y": y,
                           "w": pw, "h": ph})
        x += pw + FILM_CUT_GAP_MM
        in_row += 1
    total = y + ph + FILM_CUT_GAP_MM
    return {"fits": True, "placements": placements, "rotated": rotated,
            "piece_mm": (w, h), "total_mm": total,
            "film_width_mm": film_width_mm, "per_row": per_row}


def film_summary(fp, count):
    if not fp["fits"]:
        w, h = fp["piece_mm"]
        return (f"Roll to Film: a {w:.0f} x {h:.0f} mm piece does not fit "
                f"the {fp['film_width_mm']:.0f} mm film either way up. "
                f"Split it smaller or print it on the flatbed "
                f"(330 x 420 mm).")
    lines = [
        f"Roll to Film ({fp['film_width_mm']:.0f} mm film): {count} piece(s), "
        f"{fp['per_row']} across"
        + (" (pieces rotated 90 degrees on the film)" if fp["rotated"] else ""),
        f"Film used: {fp['total_mm'] / 1000:.2f} m including a "
        f"{FILM_LEADER_MM:.0f} mm blank leader and cutting gaps",
    ]
    if fp["total_mm"] > FILM_MAX_JOB_MM:
        lines.append("Warning: over the 10 m continuous job limit, "
                     "split the job into two runs.")
    lines.append("Use Flexible White Ink for roll modes with white, "
                 "standard white can shrink and curl film.")
    return "\n".join(lines)


def film_layout_image(img, plan, fp, max_h=2600):
    """Schematic of the roll: leader band, then every tile placed at its
    film position with its name, true proportions."""
    if not fp["fits"]:
        return None
    scale = 3.0  # px per mm
    W = int(round(fp["film_width_mm"] * scale))
    H = int(round(fp["total_mm"] * scale))
    if H > max_h:
        scale *= max_h / H
        W = int(round(fp["film_width_mm"] * scale))
        H = int(round(fp["total_mm"] * scale))
    canvas = Image.new("RGB", (W, H), (245, 242, 235))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 30)
        small = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
        small = font
    leader_h = int(round(FILM_LEADER_MM * scale))
    d.rectangle([0, 0, W, leader_h], fill=(214, 208, 196))
    d.text((12, leader_h // 2 - 14),
           f"BLANK LEADER {FILM_LEADER_MM:.0f} mm", fill=(90, 84, 70),
           font=small)
    tiles = plan["tiles"]
    for t, p in zip(tiles, fp["placements"]):
        dx = int(round(p["x"] * scale))
        dy = int(round(p["y"] * scale))
        dw = int(round(p["w"] * scale))
        dh = int(round(p["h"] * scale))
        piece = img.crop(t["box"])
        if fp["rotated"]:
            piece = piece.rotate(-90, expand=True)
        canvas.paste(piece.resize((dw, dh), Image.LANCZOS), (dx, dy))
        d.rectangle([dx, dy, dx + dw - 1, dy + dh - 1],
                    outline=(200, 40, 40), width=3)
        d.rectangle([dx + 8, dy + 8, dx + 150, dy + 46], fill=(0, 0, 0))
        d.text((dx + 16, dy + 13), t["name"], fill=(255, 210, 90),
               font=font)
    d.text((12, H - 40),
           f"Total film: {fp['total_mm'] / 1000:.2f} m", fill=(60, 56, 48),
           font=small)
    return canvas

