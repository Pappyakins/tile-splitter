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
  - `film-layout.png`, the Roll to Film plan (below)
  - `job.txt`, sizes and settings for the job

## Roll to Film mode (eufyMake E1)

Built around the E1 Roll-to-Film attachment's real limits: film
100 to 305 mm wide, up to 10 m continuous per job, about 200 mm of
blank leader at the start of every job. Set the film width in the app
(305 mm by default) and every job also gets:

- a film layout picture: leader band first, then every piece at its
  true position and size down the roll, ready to cut apart
- the total film the job uses, leader and cutting gaps included,
  in `job.txt` and in the app summary
- pieces wider than the film are placed rotated 90 degrees when they
  fit that way, and flagged with flatbed advice when they do not

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
it to the release. Or run `BUILD-WINDOWS.bat` on any Windows PC with
Python 3 installed, it builds the same exe into `dist\`.
