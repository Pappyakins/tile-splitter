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
    """Cut the tiles per plan. Returns {name: PIL.Image} at print size.
    Works for grid plans and mixed plans alike: every tile entry carries
    its own source box and output pixel size."""
    result = {}
    for t in plan["tiles"]:
        piece = img.crop(t["box"]).resize(t["out"], Image.LANCZOS)
        result[t["name"]] = piece
    return result


def _fmt_dim(v):
    """12.0 -> '12', 12.5 -> '12.5', for filenames and labels."""
    return f"{v:g}"


def plan_mixed(img_w, img_h, panels, gap_in, dpi):
    """Plan a row of different sized panels hung side by side.

    panels: ordered list of (w_in, h_in), left to right, centre-aligned
    vertically against the tallest panel. The source is cover-cropped
    to the whole arrangement's aspect, then each panel samples its own
    window (offsets include the hanging gaps, same rule as the grid).
    Returns a plan in the same shape as plan_tiles; each tile entry also
    carries its wall offsets (x_in, y_in, measured from the arrangement's
    top-left) and its own size and output pixels."""
    n = len(panels)
    total_w_in = sum(w for w, _ in panels) + gap_in * max(0, n - 1)
    total_h_in = max(h for _, h in panels)
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
    tiles = []
    x_in = 0.0
    for i, (w_in, h_in) in enumerate(panels):
        y_in = (total_h_in - h_in) / 2.0
        ix = x0 + int(round(x_in * sx))
        iy = y0 + int(round(y_in * sy))
        iw = int(round(w_in * sx))
        ih = int(round(h_in * sy))
        tiles.append({
            "row": 1, "col": i + 1, "pos": i + 1,
            "box": (ix, iy, ix + iw, iy + ih),
            "out": (int(round(w_in * dpi)), int(round(h_in * dpi))),
            "x_in": x_in, "y_in": y_in, "w_in": w_in, "h_in": h_in,
            "name": f"tile_P{i + 1}_{_fmt_dim(w_in)}x{_fmt_dim(h_in)}",
        })
        x_in += w_in + gap_in
    return {
        "crop": (x0, y0, x0 + crop_w, y0 + crop_h),
        "total_in": (total_w_in, total_h_in),
        "tiles": tiles,
        "eff_dpi": min(sx, sy),
        "out_px": tiles[0]["out"] if tiles else (0, 0),
        "mixed": True,
    }


def assembly_map_mixed(img, plan, max_w=1400):
    """Labelled preview of a mixed-size arrangement: every panel drawn
    at its true wall position (centre-aligned, real gaps), labelled
    P<n> with its size."""
    tw, th = plan["total_in"]
    scale = max_w / tw
    W = int(round(tw * scale))
    H = int(round(th * scale))
    canvas = Image.new("RGB", (W, H), (38, 38, 42))
    d = ImageDraw.Draw(canvas)
    min_h = min(t["h_in"] for t in plan["tiles"])
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            max(15, int(min_h * scale * 0.13)))
    except Exception:
        font = ImageFont.load_default()
    for t in plan["tiles"]:
        dx = int(round(t["x_in"] * scale))
        dy = int(round(t["y_in"] * scale))
        dw = int(round(t["w_in"] * scale))
        dh = int(round(t["h_in"] * scale))
        piece = img.crop(t["box"]).resize((dw, dh), Image.LANCZOS)
        canvas.paste(piece, (dx, dy))
        label = f"P{t['pos']}  {_fmt_dim(t['w_in'])}x{_fmt_dim(t['h_in'])} in"
        pad = 6
        bbox = d.textbbox((0, 0), label, font=font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.rectangle([dx + pad, dy + pad, dx + pad + lw + 12, dy + pad + lh + 10],
                    fill=(0, 0, 0))
        d.text((dx + pad + 6, dy + pad + 4), label, fill=(255, 210, 90),
               font=font)
    return canvas


def job_summary_mixed(plan, panels, gap_in, dpi, src_name, film_text=""):
    tw, th = plan["total_in"]
    lines = [
        "Tile Splitter job",
        f"Source picture: {src_name}",
        f"Layout: {len(panels)} different sized panels side by side, "
        f"centred vertically",
        f"Hanging gap: {gap_in} in (already in the math, hang panels "
        f"with this gap)",
        f"Total wall size: {tw:.2f} x {th:.2f} in "
        f"({tw * 2.54:.1f} x {th * 2.54:.1f} cm)",
        "Panels, left to right:",
    ]
    for t in plan["tiles"]:
        ow, oh = t["out"]
        lines.append(
            f"  P{t['pos']}: {_fmt_dim(t['w_in'])} x {_fmt_dim(t['h_in'])} in, "
            f"starts {t['x_in']:.2f} in from the left, its top sits "
            f"{t['y_in']:.2f} in below the tallest panel's top, "
            f"file {t['name']}.png -> {ow} x {oh} px at {dpi} DPI")
    lines.append(f"Source resolution over the artwork: about "
                 f"{plan['eff_dpi']:.0f} px per inch")
    if film_text:
        lines += ["", film_text]
    return "\n".join(lines) + "\n"


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
# about 15-20 cm of blank leader before the first print. The 305 mm max
# print width carries a 1 mm total safety margin, so the usable
# printable width of a roll is its width minus 1 mm (304 mm on a
# 305 mm roll). A piece between the usable width and the film width
# (a true 12 in piece is 304.8 mm) is a LANE FIT, and it runs as a
# full bleed: the piece prints at its full design width and the
# printer clips 0.4 mm per side as bleed, so the image reaches the
# board edge with no unprinted border, then the film is trimmed
# flush after printing. Only a piece wider than the film itself,
# either way up, is flatbed only.
FILM_WIDTH_MM = 305.0
FILM_LEADER_MM = 200.0
FILM_MAX_JOB_MM = 10000.0
FILM_CUT_GAP_MM = 10.0
FILM_SAFETY_MM = 1.0


def plan_film_pieces(pieces, film_width_mm=FILM_WIDTH_MM):
    """Lay a list of pieces down a film roll, shelf style, in order.

    pieces: [{"label": str, "w_in": float, "h_in": float, ...}]; extra
    keys (a source "box", say) are carried into the placement.
    Classification, in order: a piece sits upright when its width fits
    the printable width (film width minus the 1 mm safety margin),
    rotated 90 degrees when only its height fits across, then a LANE
    FIT when the oriented width is over the printable width but no
    wider than the film itself (the standard 12 in lane case): it
    prints at its full design width as a full bleed, the printer
    clips 0.4 mm per side as bleed so the image reaches the board
    edge with no unprinted border, and the film is trimmed flush
    after printing. Its layout placement is still drawn at the
    printable width in the film schematic. Only a
    piece wider than the film either way up lands in the "flatbed"
    list. Placements carry "lane" (True for a lane fit), the placed
    print size as "w"/"h", and the piece's true size as "w_mm"/"h_mm".
    Returns the placements in mm from the roll top (leader included),
    the flatbed list, and the total film length."""
    usable = film_width_mm - FILM_SAFETY_MM
    placements = []
    flatbed = []
    y = FILM_LEADER_MM
    x = 0.0
    row_h = 0.0
    for i, p in enumerate(pieces):
        w = p["w_in"] * 25.4
        h = p["h_in"] * 25.4
        label = p.get("label", f"piece {i + 1}")
        lane = False
        if w <= usable:
            pw, ph, rotated = w, h, False
        elif h <= usable:
            pw, ph, rotated = h, w, True
        elif w <= film_width_mm:
            pw, ph, rotated, lane = usable, h, False, True
        elif h <= film_width_mm:
            pw, ph, rotated, lane = usable, w, True, True
        else:
            flatbed.append({"name": label, "w_mm": w, "h_mm": h})
            continue
        if x > 0 and x + pw > usable:
            y += row_h + FILM_CUT_GAP_MM
            x = 0.0
            row_h = 0.0
        pl = {"name": label, "x": x, "y": y, "w": pw, "h": ph,
              "rotated": rotated, "lane": lane,
              "w_mm": w, "h_mm": h, "src_index": i}
        if "box" in p:
            pl["box"] = p["box"]
        placements.append(pl)
        x += pw + FILM_CUT_GAP_MM
        row_h = max(row_h, ph)
    total = (y + row_h + FILM_CUT_GAP_MM) if placements else 0.0
    return {"placements": placements, "flatbed": flatbed,
            "fits_all": not flatbed, "total_mm": total,
            "film_width_mm": film_width_mm, "usable_mm": usable}


def plan_film(tile_w_in, tile_h_in, count, film_width_mm=FILM_WIDTH_MM):
    """Lay identical pieces down a film roll (see plan_film_pieces),
    in the original return shape for the grid workflow."""
    pieces = [{"w_in": tile_w_in, "h_in": tile_h_in}
              for _ in range(count)]
    fp = plan_film_pieces(pieces, film_width_mm)
    lane_count = sum(1 for p in fp["placements"] if p.get("lane"))
    base = {"piece_mm": (tile_w_in * 25.4, tile_h_in * 25.4),
            "film_width_mm": film_width_mm, "usable_mm": fp["usable_mm"],
            "lane_count": lane_count}
    if not fp["placements"]:
        return dict(base, fits=False, placements=[], rotated=False,
                    total_mm=0.0, per_row=0)
    first_y = fp["placements"][0]["y"]
    per_row = sum(1 for p in fp["placements"] if p["y"] == first_y)
    return dict(base, fits=True, placements=fp["placements"],
                rotated=fp["placements"][0]["rotated"],
                total_mm=fp["total_mm"], per_row=per_row)


def film_summary(fp, count):
    usable = fp.get("usable_mm", fp["film_width_mm"] - FILM_SAFETY_MM)
    if not fp["fits"]:
        w, h = fp["piece_mm"]
        return (f"Roll to Film: a {w:.0f} x {h:.0f} mm piece is wider than "
                f"the {fp['film_width_mm']:.0f} mm film itself either way "
                f"up, flatbed only. Split it smaller or print it on the "
                f"flatbed (330 x 420 mm).")
    lines = [
        f"Roll to Film ({fp['film_width_mm']:.0f} mm film, "
        f"{usable:.0f} mm printable width): {count} piece(s), "
        f"{fp['per_row']} across"
        + (" (pieces rotated 90 degrees on the film)" if fp["rotated"] else ""),
        f"Film used: {fp['total_mm'] / 1000:.2f} m including a "
        f"{FILM_LEADER_MM:.0f} mm blank leader and cutting gaps",
    ]
    if fp.get("lane_count"):
        lines.append(
            f"Lane fit: {fp['lane_count']} piece(s) are the full 12 in "
            f"lane width, they print at full design width with "
            f"0.4 mm clipped per side as bleed, so the image reaches "
            f"the board edge with no unprinted border, trim the film "
            f"flush after printing.")
    if fp["total_mm"] > FILM_MAX_JOB_MM:
        lines.append("Warning: over the 10 m continuous job limit, "
                     "split the job into two runs.")
    lines.append("Use Flexible White Ink for roll modes with white, "
                 "standard white can shrink and curl film.")
    return "\n".join(lines)


def film_summary_pieces(fp):
    """Film summary for a mixed piece list (see plan_film_pieces)."""
    usable = fp["usable_mm"]
    fw = fp["film_width_mm"]
    head = (f"Roll to Film ({fw:.0f} mm film, {usable:.0f} mm printable "
            f"width after the 1 mm safety margin)")
    lines = []
    if fp["placements"]:
        n_rot = sum(1 for p in fp["placements"] if p["rotated"])
        n_lane = sum(1 for p in fp["placements"] if p.get("lane"))
        lines.append(f"{head}: {len(fp['placements'])} piece(s) on the roll"
                     + (f", {n_rot} rotated 90 degrees" if n_rot else "")
                     + (f", {n_lane} lane fit" if n_lane else ""))
        lines.append(f"Film used: {fp['total_mm'] / 1000:.2f} m including a "
                     f"{FILM_LEADER_MM:.0f} mm blank leader and cutting gaps")
        if fp["total_mm"] > FILM_MAX_JOB_MM:
            lines.append("Warning: over the 10 m continuous job limit, "
                         "split the job into two runs.")
        for p in fp["placements"]:
            if p.get("lane"):
                lines.append(
                    f"Lane fit: {p['name']} ({p['w_mm']:.0f} x "
                    f"{p['h_mm']:.0f} mm) prints at full design width, "
                    f"0.4 mm clipped per side as bleed, so the image "
                    f"reaches the board edge with no unprinted border, "
                    f"trim the film flush after printing.")
    else:
        lines.append(f"{head}: nothing fits the roll, every piece is "
                     f"flatbed only.")
    for f in fp["flatbed"]:
        lines.append(
            f"Flatbed only: {f['name']} ({f['w_mm']:.0f} x {f['h_mm']:.0f} mm) "
            f"is wider than the {fw:.0f} mm film itself even rotated. "
            f"Print it on the flatbed (330 x 420 mm) instead.")
    lines.append("Use Flexible White Ink for roll modes with white, "
                 "standard white can shrink and curl film.")
    return "\n".join(lines)


def film_layout_image(img, plan, fp, max_h=2600):
    """Schematic of the roll: leader band, then every piece placed at
    its film position with its name, true proportions. Works with the
    grid plan_film result and with plan_film_pieces: a placement that
    carries its own source "box" (the mixed workflow) is labelled with
    its piece name, otherwise the plan tile at the same index supplies
    the picture and the tile name."""
    if not fp["placements"]:
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
    tiles = plan["tiles"] if plan else []
    for p in fp["placements"]:
        t = None
        if p.get("src_index") is not None and p["src_index"] < len(tiles):
            t = tiles[p["src_index"]]
        box = p.get("box") or (t["box"] if t else None)
        if box is None:
            continue
        label = t["name"] if (t is not None and "box" not in p) \
            else p["name"]
        dy = int(round(p["y"] * scale))
        dw = int(round(p["w"] * scale))
        dh = int(round(p["h"] * scale))
        if p.get("lane"):
            # Lane fit (full bleed): draw the full film width as a
            # visible band, the print area in it, film trimmed flush
            # after printing.
            d.rectangle([0, dy, W - 1, dy + dh - 1], fill=(226, 219, 204),
                        outline=(150, 140, 118), width=2)
            dx = int(round((fp["film_width_mm"] - p["w"]) / 2 * scale))
            label += " LANE FIT"
        else:
            dx = int(round(p["x"] * scale))
        piece = img.crop(box)
        if p.get("rotated", fp.get("rotated", False)):
            piece = piece.rotate(-90, expand=True)
        canvas.paste(piece.resize((dw, dh), Image.LANCZOS), (dx, dy))
        d.rectangle([dx, dy, dx + dw - 1, dy + dh - 1],
                    outline=(200, 40, 40), width=3)
        bbox = d.textbbox((0, 0), label, font=font)
        lw = bbox[2] - bbox[0]
        d.rectangle([dx + 8, dy + 8, dx + 24 + lw, dy + 46], fill=(0, 0, 0))
        d.text((dx + 16, dy + 13), label, fill=(255, 210, 90),
               font=font)
        if p.get("lane"):
            note = "full bleed, 0.4 mm clips per side, trim flush"
            bbox = d.textbbox((0, 0), note, font=small)
            nw = bbox[2] - bbox[0]
            d.rectangle([dx + 8, dy + 50, dx + 20 + nw, dy + 82],
                        fill=(0, 0, 0))
            d.text((dx + 14, dy + 54), note, fill=(255, 255, 255),
                   font=small)
    d.text((12, H - 40),
           f"Total film: {fp['total_mm'] / 1000:.2f} m", fill=(60, 56, 48),
           font=small)
    return canvas

