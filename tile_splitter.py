"""JakinsCraft Tile Splitter, desktop app.

Open a picture, choose a layout, and it splits the picture into print
ready tiles. Two layouts: a uniform grid of same sized panels, or
different sized panels side by side. The hanging gap is part of the
math either way, so a big piece split across panels lines up again
on the wall.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from tiles_core import (plan_tiles, split_image, assembly_map, job_summary,
                        plan_film, film_summary, film_layout_image,
                        plan_mixed, assembly_map_mixed, job_summary_mixed,
                        plan_film_pieces, film_summary_pieces)

VERSION = "1.2.0"

# Standard sizes are multiples of 12 in, matching the 12 inch print
# width of the roll to film attachment. Anything else stays available
# through Custom and the free entry fields.
PRESETS = {
    "12 x 12 in": (12.0, 12.0),
    "12 x 24 in": (12.0, 24.0),
    "24 x 24 in": (24.0, 24.0),
    "12 x 36 in": (12.0, 36.0),
    "24 x 36 in": (24.0, 36.0),
    "Custom": None,
}

MIXED_PRESETS = [(12.0, 12.0), (12.0, 24.0), (24.0, 24.0),
                 (12.0, 36.0), (24.0, 36.0)]
MAX_MIXED_PANELS = 8


def _fmt_num(v):
    return f"{v:g}"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"JakinsCraft Tile Splitter v{VERSION}")
        self.geometry("1060x720")
        self.minsize(900, 600)
        self.img = None
        self.img_name = ""
        self._photo = None
        self._job = None

        self.mode = tk.StringVar(value="grid")
        self.tile_w = tk.StringVar(value="12")
        self.tile_h = tk.StringVar(value="24")
        self.cols = tk.StringVar(value="3")
        self.rows = tk.StringVar(value="1")
        self.gap = tk.StringVar(value="0.75")
        self.dpi = tk.StringVar(value="300")
        self.film_w = tk.StringVar(value="305")
        self.preset = tk.StringVar(value="12 x 24 in")
        self.status = tk.StringVar(value="Open a picture to begin.")
        self.summary = tk.StringVar(value="")
        self.mixed_readout = tk.StringVar(value="")
        self.mixed_rows = []

        self._build_ui()
        for var in (self.tile_w, self.tile_h, self.cols, self.rows,
                    self.gap, self.dpi, self.film_w):
            var.trace_add("write", lambda *_: self._schedule_preview())
        for w, h in ((12.0, 24.0), (12.0, 12.0), (12.0, 24.0)):
            self._add_mixed_panel(w, h)

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

        ttk.Label(left, text="Layout").pack(anchor="w")
        modes = ttk.Frame(left)
        modes.pack(fill="x", pady=(0, 8))
        ttk.Radiobutton(modes, text="Uniform grid", value="grid",
                        variable=self.mode, command=self._mode_changed)\
            .pack(side="left")
        ttk.Radiobutton(modes, text="Mixed sizes side by side",
                        value="mixed", variable=self.mode,
                        command=self._mode_changed).pack(side="left")

        container = ttk.Frame(left)
        container.pack(fill="x")
        self.grid_frame = ttk.Frame(container)
        self.grid_frame.grid(row=0, column=0, sticky="nsew")
        self.mixed_frame = ttk.Frame(container)
        self.mixed_frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(self.grid_frame, text="Panel size preset")\
            .pack(anchor="w")
        cb = ttk.Combobox(self.grid_frame, textvariable=self.preset,
                          state="readonly", values=list(PRESETS.keys()),
                          width=24)
        cb.pack(fill="x", pady=(0, 8))
        cb.bind("<<ComboboxSelected>>", self._preset_changed)
        self._field(self.grid_frame, "Panel width (in)", self.tile_w)
        self._field(self.grid_frame, "Panel height (in)", self.tile_h)
        self._field(self.grid_frame, "Panels across", self.cols)
        self._field(self.grid_frame, "Panels down", self.rows)

        ttk.Label(self.mixed_frame,
                  text="Panels, left to right, centred vertically")\
            .pack(anchor="w", pady=(0, 4))
        self.mixed_rows_frame = ttk.Frame(self.mixed_frame)
        self.mixed_rows_frame.pack(fill="x")
        ttk.Button(self.mixed_frame, text="Add panel",
                   command=lambda: self._add_mixed_panel(12.0, 24.0))\
            .pack(fill="x", pady=(5, 4))
        ttk.Label(self.mixed_frame, text="Quick add").pack(anchor="w")
        quick = ttk.Frame(self.mixed_frame)
        quick.pack(fill="x", pady=(0, 4))
        for w, h in MIXED_PRESETS:
            ttk.Button(quick, text=f"{_fmt_num(w)}x{_fmt_num(h)}",
                       width=6,
                       command=lambda w=w, h=h: self._add_mixed_panel(w, h))\
                .pack(side="left", padx=(0, 3))
        ttk.Label(self.mixed_frame, textvariable=self.mixed_readout,
                  wraplength=250, foreground="#234").pack(fill="x",
                                                          pady=(2, 2))

        self._field(left, "Hanging gap (in)", self.gap)
        self._field(left, "Print DPI", self.dpi)
        self._field(left, "Film width (mm, Roll to Film)", self.film_w)
        ttk.Label(left, wraplength=250, foreground="#666",
                  text="Printable width is the film width minus a 1 mm "
                       "safety margin, so a 305 mm roll prints 304 mm "
                       "wide.").pack(fill="x", pady=(0, 4))

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
        ttk.Label(left, foreground="#666",
                  text=f"JakinsCraft Tile Splitter v{VERSION}")\
            .pack(fill="x", pady=(6, 0))

        self.preview = ttk.Label(right, anchor="center",
                                 text="Preview will appear here")
        self.preview.pack(fill="both", expand=True)
        self.grid_frame.tkraise()

    def _field(self, parent, label, var):
        ttk.Label(parent, text=label).pack(anchor="w")
        ttk.Entry(parent, textvariable=var, width=24).pack(fill="x",
                                                           pady=(0, 7))

    # ---------------- mixed panel editor ----------------
    def _add_mixed_panel(self, w, h):
        if len(self.mixed_rows) >= MAX_MIXED_PANELS:
            self.status.set(f"Mixed mode holds up to "
                            f"{MAX_MIXED_PANELS} panels.")
            return
        frame = ttk.Frame(self.mixed_rows_frame)
        frame.pack(fill="x", pady=1)
        lbl = ttk.Label(frame, text="P?", width=3)
        lbl.pack(side="left")
        wv = tk.StringVar(value=_fmt_num(w))
        hv = tk.StringVar(value=_fmt_num(h))
        ttk.Entry(frame, textvariable=wv, width=6).pack(side="left")
        ttk.Label(frame, text=" x ").pack(side="left")
        ttk.Entry(frame, textvariable=hv, width=6).pack(side="left")
        ttk.Label(frame, text=" in").pack(side="left")
        row = {"frame": frame, "w": wv, "h": hv, "label": lbl}
        ttk.Button(frame, text="Remove", width=7,
                   command=lambda: self._remove_mixed_panel(row))\
            .pack(side="left", padx=(5, 0))
        for var in (wv, hv):
            var.trace_add("write",
                          lambda *_: (self._update_mixed_readout(),
                                      self._schedule_preview()))
        self.mixed_rows.append(row)
        self._renumber_mixed()
        self._update_mixed_readout()
        self._schedule_preview()

    def _remove_mixed_panel(self, row):
        if len(self.mixed_rows) <= 1:
            self.status.set("Mixed mode needs at least one panel.")
            return
        row["frame"].destroy()
        self.mixed_rows.remove(row)
        self._renumber_mixed()
        self._update_mixed_readout()
        self._schedule_preview()

    def _renumber_mixed(self):
        for i, row in enumerate(self.mixed_rows):
            row["label"].config(text=f"P{i + 1}")

    def _mixed_panels(self):
        panels = []
        for row in self.mixed_rows:
            w = float(row["w"].get())
            h = float(row["h"].get())
            if w <= 0 or h <= 0 or w > 120 or h > 120:
                raise ValueError
            panels.append((w, h))
        if not panels:
            raise ValueError
        return panels

    def _update_mixed_readout(self):
        try:
            panels = self._mixed_panels()
            gap = float(self.gap.get())
            if gap < 0:
                raise ValueError
        except ValueError:
            self.mixed_readout.set("Check the panel sizes and gap.")
            return
        tw = sum(w for w, _ in panels) + gap * (len(panels) - 1)
        th = max(h for _, h in panels)
        self.mixed_readout.set(
            f"{len(panels)} panel(s), total wall {tw:.1f} x {th:.1f} in "
            f"({tw * 2.54:.0f} x {th * 2.54:.0f} cm)")

    # ---------------- logic ----------------
    def _mode_changed(self):
        if self.mode.get() == "mixed":
            self.mixed_frame.tkraise()
            self._update_mixed_readout()
        else:
            self.grid_frame.tkraise()
        self._refresh_preview()

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

    def _common_numbers(self):
        gap = float(self.gap.get())
        dpi = int(self.dpi.get())
        film_w = float(self.film_w.get())
        if gap < 0 or dpi < 36 or film_w < 50 or film_w > 1000:
            raise ValueError
        return gap, dpi, film_w

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

    def _quality(self, eff):
        return ("Sharp print" if eff >= 250 else
                "Good print" if eff >= 150 else
                "May look soft, use a bigger photo or smaller panels")

    def _refresh_preview(self):
        self._job = None
        if self.img is None:
            return
        if self.mode.get() == "mixed":
            self._refresh_mixed_preview()
        else:
            self._refresh_grid_preview()

    def _refresh_grid_preview(self):
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
        fp = plan_film(tw, th, cols * rows, film_w)
        film_line = (f"Film: {fp['total_mm'] / 1000:.2f} m of "
                     f"{film_w:.0f} mm roll incl. leader"
                     if fp["fits"] else
                     "Film: pieces too wide for the roll, flatbed only")
        self.summary.set(
            f"Wall size: {total_w:.1f} x {total_h:.1f} in "
            f"({total_w * 2.54:.0f} x {total_h * 2.54:.0f} cm)\n"
            f"Each tile prints at {ow} x {oh} px\n"
            f"Photo gives about {eff:.0f} px per inch: "
            f"{self._quality(eff)}\n"
            f"{film_line}")
        avail_w = max(420, self.preview.winfo_width() - 8)
        amap = assembly_map(self.img, plan, gap, tw, th,
                            max_w=min(1100, avail_w))
        self._photo = ImageTk.PhotoImage(amap)
        self.preview.config(image=self._photo, text="")

    def _refresh_mixed_preview(self):
        try:
            panels = self._mixed_panels()
            gap, dpi, film_w = self._common_numbers()
        except ValueError:
            self.summary.set("Check the numbers: panel sizes above "
                             "zero, DPI 36 or more.")
            return
        plan = plan_mixed(self.img.size[0], self.img.size[1],
                          panels, gap, dpi)
        total_w, total_h = plan["total_in"]
        eff = plan["eff_dpi"]
        fp = plan_film_pieces(self._mixed_pieces(plan), film_w)
        if fp["fits_all"]:
            film_line = (f"Film: all {len(panels)} pieces fit, "
                         f"{fp['total_mm'] / 1000:.2f} m of "
                         f"{film_w:.0f} mm roll incl. leader")
        elif fp["placements"]:
            film_line = (f"Film: {len(fp['placements'])} of "
                         f"{len(panels)} pieces on the roll "
                         f"({fp['total_mm'] / 1000:.2f} m), "
                         f"{len(fp['flatbed'])} flatbed only")
        else:
            film_line = "Film: pieces too wide for the roll, flatbed only"
        outs = ", ".join(f"P{t['pos']} {t['out'][0]}x{t['out'][1]}"
                         for t in plan["tiles"])
        self.summary.set(
            f"Wall size: {total_w:.1f} x {total_h:.1f} in "
            f"({total_w * 2.54:.0f} x {total_h * 2.54:.0f} cm)\n"
            f"{len(panels)} panels side by side, prints at {outs} px\n"
            f"Photo gives about {eff:.0f} px per inch: "
            f"{self._quality(eff)}\n"
            f"{film_line}")
        avail_w = max(420, self.preview.winfo_width() - 8)
        amap = assembly_map_mixed(self.img, plan,
                                  max_w=min(1100, avail_w))
        self._photo = ImageTk.PhotoImage(amap)
        self.preview.config(image=self._photo, text="")

    @staticmethod
    def _mixed_pieces(plan):
        return [{"label": f"P{t['pos']}", "w_in": t["w_in"],
                 "h_in": t["h_in"], "box": t["box"]}
                for t in plan["tiles"]]

    def save_tiles(self):
        if self.img is None:
            messagebox.showinfo("No picture", "Open a picture first.")
            return
        if self.mode.get() == "mixed":
            self._save_mixed()
        else:
            self._save_grid()

    def _save_grid(self):
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

    def _save_mixed(self):
        try:
            panels = self._mixed_panels()
            gap, dpi, film_w = self._common_numbers()
        except ValueError:
            messagebox.showerror("Check the numbers",
                                 "Panel sizes must be above zero, "
                                 "DPI 36 or more.")
            return
        folder = filedialog.askdirectory(title="Where should tiles go?")
        if not folder:
            return
        plan = plan_mixed(self.img.size[0], self.img.size[1],
                          panels, gap, dpi)
        tiles = split_image(self.img, plan)
        for name, piece in tiles.items():
            piece.save(os.path.join(folder, name + ".png"))
        assembly_map_mixed(self.img, plan, max_w=1600).save(
            os.path.join(folder, "assembly-map.png"))
        fp = plan_film_pieces(self._mixed_pieces(plan), film_w)
        fimg = film_layout_image(self.img, plan, fp)
        if fimg is not None:
            fimg.save(os.path.join(folder, "film-layout.png"))
        with open(os.path.join(folder, "job.txt"), "w") as f:
            f.write(job_summary_mixed(plan, panels, gap, dpi,
                                      self.img_name,
                                      film_text=film_summary_pieces(fp)))
        self.status.set(f"Saved {len(tiles)} tiles plus the assembly map "
                        f"to {folder}")
        messagebox.showinfo(
            "Done",
            f"{len(tiles)} print ready tiles saved.\n\n"
            "Open assembly-map.png to see which panel goes where, "
            "film-layout.png for the roll plan, and job.txt for the sizes.")


if __name__ == "__main__":
    App().mainloop()
