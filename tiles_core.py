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


def job_summary(plan, tile_w_in, tile_h_in, cols, rows, gap_in, dpi, src_name):
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
    return "\n".join(lines) + "\n"
