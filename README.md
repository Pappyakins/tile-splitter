# JakinsCraft Tile Splitter

A small Windows desktop app that splits one picture into print-ready
tiles for multi-panel wall art: triptychs, grids, and big pieces split
across several panels.

## What it does

- Open any picture (JPG, PNG, WebP, BMP)
- Pick a panel size (presets like 12 x 16 in, or custom), how many
  panels across and down, and the hanging gap between panels
- The gap is part of the math: each tile samples its slice with a
  stride of panel + gap, so when the panels hang with that gap, the
  picture lines up across them
- Live preview shows the assembled piece with every tile labelled
  (R1C1, R1C2, ...) and a print quality readout based on your photo's
  resolution
- Saving writes:
  - `tile_R<row>C<col>.png`, one file per panel, at exact print size
    and DPI (300 by default)
  - `assembly-map.png`, the labelled layout picture
  - `job.txt`, sizes and settings for the job

## Get the app

Download `TileSplitter.exe` from the
[Releases](https://github.com/Pappyakins/tile-splitter/releases) page.
No install, no Python needed, just run it. Windows may show a
SmartScreen prompt for an unsigned app, choose "More info" then
"Run anyway".

## Run from source

```
pip install pillow
python tile_splitter.py
```

## Build the exe

Pushing a `v*` tag runs the GitHub Actions workflow on a Windows
runner, which builds `TileSplitter.exe` with PyInstaller and attaches
it to the release.
