# JakinsCraft Tile Splitter

A small Windows desktop app that splits one picture into print-ready
tiles for multi-panel wall art: triptychs, grids, and big pieces split
across several panels.

## What it does

- Open any picture (JPG, PNG, WebP, BMP)
- Two layouts, picked in the app:
  - **Uniform grid**: pick a panel size, how many panels across and
    down, and the hanging gap between panels. Tiles are saved as
    `tile_R<row>C<col>.png`
- Standard sizes are multiples of 12 in, matching the 12 inch print
  width of the roll to film attachment: 12 x 12, 12 x 24, 24 x 24,
  12 x 36 and 24 x 36, in the grid presets and the mixed mode quick
  add buttons. Any other size (12 x 16, 11 x 14, ...) still works,
  just type it in or pick Custom
  - **Mixed sizes side by side**: stack different sized panels next
    to each other in one row, like a 12 x 16, an 8 x 10 and another
    12 x 16. Panels are centre-aligned vertically against the tallest
    one, and saved as `tile_P<position>_<W>x<H>.png`
- The gap is part of the math: each tile samples its slice with a
  stride of panel + gap, so when the panels hang with that gap, the
  picture lines up across them
- Live preview shows the assembled piece with every tile labelled
  and a print quality readout based on your photo's resolution
- Saving writes:
  - one PNG per panel, at exact print size and DPI (300 by default)
  - `assembly-map.png`, the labelled layout picture
  - `film-layout.png`, the Roll to Film plan (below)
  - `job.txt`, sizes and settings for the job

## Roll to Film mode (eufyMake E1)

Built around the E1 Roll-to-Film attachment's real limits: film
100 to 305 mm wide, up to 10 m continuous per job, about 200 mm of
blank leader at the start of every job. One point from the official
spec: 305 mm is the maximum print width itself, and it carries a
1 mm total safety margin, so the usable printable width is the film
width minus 1 mm (304 mm on a 305 mm roll). Set the film width in
the app (305 mm by default) and every job also gets:

- a film layout picture: leader band first, then every piece at its
  true position and size down the roll, ready to cut apart
- the total film the job uses, leader and cutting gaps included,
  in `job.txt` and in the app summary
- pieces up to the printable width are placed as they are, pieces
  that only fit turned sideways are placed rotated 90 degrees, and
  a piece between the printable width and the film width itself is
  a **lane fit**: a true 12 in panel is 304.8 mm, just over the
  304 mm printable width, and the standard 12 in lane case must work
  on film, so it prints centred at 304 mm on the 305 mm film with
  the full picture kept (a 0.26 percent difference no eye can see),
  and the clear film edges are trimmed flush after printing. Only a
  piece wider than the film itself either way up is flagged as
  flatbed only. Lane fit pieces are called out in `job.txt` and
  drawn in the film layout inside a film width band, print centred,
  labelled LANE FIT

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
