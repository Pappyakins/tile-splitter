"""JakinsCraft Tile Splitter, desktop app.

Open a picture, choose a panel size and grid, and it splits the picture
into print ready tiles. The hanging gap is part of the math, so a big
piece split across panels lines up again on the wall.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from tiles_core import (plan_tiles, split_image, assembly_map, job_summary,
                        plan_film, film_summary, film_layout_image)

PRESETS = {
    "12 x 16 in": (12.0, 16.0),
    "11 x 14 in": (11.0, 14.0),
    "8 x 10 in": (8.0, 10.0),
    "12 x 12 in": (12.0, 12.0),
    "16 x 20 in": (16.0, 20.0),
    "Custom": None,
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JakinsCraft Tile Splitter")
        self.geometry("1060x680")
        self.minsize(900, 560)
        self.img = None
        self.img_name = ""
        self._photo = None
        self._job = None

        self.tile_w = tk.StringVar(value="12")
        self.tile_h = tk.StringVar(value="16")
        self.cols = tk.StringVar(value="3")
        self.rows = tk.StringVar(value="1")
        self.gap = tk.StringVar(value="0.75")
        self.dpi = tk.StringVar(value="300")
        self.film_w = tk.StringVar(value="305")
        self.preset = tk.StringVar(value="12 x 16 in")
        self.status = tk.StringVar(value="Open a picture to begin.")
        self.summary = tk.StringVar(value="")

        self._build_ui()
        for var in (self.tile_w, self.tile_h, self.cols, self.rows,
                    self.gap, self.dpi, self.film_w):
            var.trace_add("write", lambda *_: self._schedule_preview())

    # ---------------- UI ----------------
    def _build_ui(self):
        left = ttk.Frame(self, padding=12)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=(0, 12, 12, 12))
        right.pack(side="right", fill="both", expand=True)

        ttk.Button(left, text="Open picture...", command=self.open_image)\
            .pack(fill="x", pady=(0, 4))
        self.file_label = ttk.Label(left, text="No picture loaded",
                                    wraplength=250, foreground="#666")
        self.file_label.pack(fill="x", pady=(0, 10))

        ttk.Label(left, text="Panel size preset").pack(anchor="w")
        cb = ttk.Combobox(left, textvariable=self.preset, state="readonly",
                          values=list(PRESETS.keys()), width=24)
        cb.pack(fill="x", pady=(0, 8))
        cb.bind("<<ComboboxSelected>>", self._preset_changed)

        self._field(left, "Panel width (in)", self.tile_w)
        self._field(left, "Panel height (in)", self.tile_h)
        self._field(left, "Panels across", self.cols)
        self._field(left, "Panels down", self.rows)
        self._field(left, "Hanging gap (in)", self.gap)
        self._field(left, "Print DPI", self.dpi)
        self._field(left, "Film width (mm, Roll to Film)", self.film_w)

        ttk.Label(left, textvariable=self.summary, wraplength=250,
                  foreground="#234").pack(fill="x", pady=(8, 4))
        ttk.Button(left, text="Split and save tiles...",
                   command=self.save_tiles).pack(fill="x", pady=(6, 4))
        ttk.Label(left, textvariable=self.status, wraplength=250)\
            .pack(fill="x", pady=(2, 0))
        ttk.Label(left, wraplength=250, foreground="#666",
                  text="Tip: the gap is built into the split. Hang the "
                       "panels with exactly this gap and the picture "
                       "lines up across them.").pack(fill="x", pady=(10, 0))

        self.preview = ttk.Label(right, anchor="center",
                                 text="Preview will appear here")
        self.preview.pack(fill="both", expand=True)

    def _field(self, parent, label, var):
        ttk.Label(parent, text=label).pack(anchor="w")
        ttk.Entry(parent, textvariable=var, width=24).pack(fill="x",
                                                           pady=(0, 7))

    # ---------------- logic ----------------
    def _preset_changed(self, _event=None):
        size = PRESETS.get(self.preset.get())
        if size:
            self.tile_w.set(str(size[0]).rstrip("0").rstrip("."))
            self.tile_h.set(str(size[1]).rstrip("0").rstrip("."))

    def _numbers(self):
        tw = float(self.tile_w.get())
        th = float(self.tile_h.get())
        cols = int(self.cols.get())
        rows = int(self.rows.get())
        gap = float(self.gap.get())
        dpi = int(self.dpi.get())
        film_w = float(self.film_w.get())
        if min(tw, th) <= 0 or cols < 1 or rows < 1 or gap < 0 or dpi < 36:
            raise ValueError
        if cols > 12 or rows > 12 or film_w < 50 or film_w > 1000:
            raise ValueError
        return tw, th, cols, rows, gap, dpi, film_w

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose a picture",
            filetypes=[("Pictures", "*.jpg *.jpeg *.png *.webp *.bmp"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            self.img = Image.open(path).convert("RGB")
            self.img.load()
        except Exception as e:
            messagebox.showerror("Could not open picture", str(e))
            return
        self.img_name = os.path.basename(path)
        self.file_label.config(
            text=f"{self.img_name}\n{self.img.size[0]} x {self.img.size[1]} px")
        self.status.set("Picture loaded. Check the preview, then split.")
        self._refresh_preview()

    def _schedule_preview(self):
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(450, self._refresh_preview)

    def _refresh_preview(self):
        self._job = None
        if self.img is None:
            return
        try:
            tw, th, cols, rows, gap, dpi, film_w = self._numbers()
        except ValueError:
            self.summary.set("Check the numbers: sizes above zero, "
                             "panels 1 to 12, DPI 36 or more.")
            return
        plan = plan_tiles(self.img.size[0], self.img.size[1],
                          tw, th, cols, rows, gap, dpi)
        total_w, total_h = plan["total_in"]
        ow, oh = plan["out_px"]
        eff = plan["eff_dpi"]
        quality = ("Sharp print" if eff >= 250 else
                   "Good print" if eff >= 150 else
                   "May look soft, use a bigger photo or smaller panels")
        fp = plan_film(tw, th, cols * rows, film_w)
        film_line = (f"Film: {fp['total_mm'] / 1000:.2f} m of "
                     f"{film_w:.0f} mm roll incl. leader"
                     if fp["fits"] else
                     "Film: pieces too wide for the roll, flatbed only")
        self.summary.set(
            f"Wall size: {total_w:.1f} x {total_h:.1f} in "
            f"({total_w * 2.54:.0f} x {total_h * 2.54:.0f} cm)\n"
            f"Each tile prints at {ow} x {oh} px\n"
            f"Photo gives about {eff:.0f} px per inch: {quality}\n"
            f"{film_line}")
        avail_w = max(420, self.preview.winfo_width() - 8)
        amap = assembly_map(self.img, plan, gap, tw, th,
                            max_w=min(1100, avail_w))
        self._photo = ImageTk.PhotoImage(amap)
        self.preview.config(image=self._photo, text="")

    def save_tiles(self):
        if self.img is None:
            messagebox.showinfo("No picture", "Open a picture first.")
            return
        try:
            tw, th, cols, rows, gap, dpi, film_w = self._numbers()
        except ValueError:
            messagebox.showerror("Check the numbers",
                                 "Sizes must be above zero, panels 1 to 12.")
            return
        folder = filedialog.askdirectory(title="Where should tiles go?")
        if not folder:
            return
        plan = plan_tiles(self.img.size[0], self.img.size[1],
                          tw, th, cols, rows, gap, dpi)
        tiles = split_image(self.img, plan)
        for name, piece in tiles.items():
            piece.save(os.path.join(folder, name + ".png"))
        assembly_map(self.img, plan, gap, tw, th, max_w=1600).save(
            os.path.join(folder, "assembly-map.png"))
        fp = plan_film(tw, th, cols * rows, film_w)
        fimg = film_layout_image(self.img, plan, fp)
        if fimg is not None:
            fimg.save(os.path.join(folder, "film-layout.png"))
        with open(os.path.join(folder, "job.txt"), "w") as f:
            f.write(job_summary(plan, tw, th, cols, rows, gap, dpi,
                                self.img_name,
                                film_text=film_summary(fp, cols * rows)))
        self.status.set(f"Saved {len(tiles)} tiles plus the assembly map "
                        f"to {folder}")
        messagebox.showinfo(
            "Done",
            f"{len(tiles)} print ready tiles saved.\n\n"
            "Open assembly-map.png to see which tile goes where, "
            "film-layout.png for the roll plan, and job.txt for the sizes.")


if __name__ == "__main__":
    App().mainloop()
