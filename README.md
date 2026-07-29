# BGS CORNER — Corner 60 FPS

A scroll-driven website for **BGS CORNER**, a premium perfume house. The hero
section scrubs through a 150-frame product film (crystal flacon → boutique
reveal) as you scroll, rendered on a full-screen canvas with inertial smoothing.

## How the frames are stored

The animation frames are **not** committed as individual images. They are
packed into a single binary file, [assets/frames.bin](assets/frames.bin):

```
"BGSP" | u32 version | u32 count | u32 width | u32 height
u32 lengths[count]           (little-endian)
concatenated WebP payloads   (1600×900, quality 80)
```

`main.js` streams the pack, slices per-frame WebP blobs as bytes arrive
(first paint happens before the download finishes), and a windowed decoder
keeps ~30 ImageBitmaps ready around the playhead so scrubbing never blocks
the main thread. Total payload: ~6 MB for the entire film.

## Run locally

Any static server works:

```
python3 -m http.server 4173
```

Then open <http://localhost:4173>.

## Stack

No frameworks, no build step — hand-written HTML, CSS and vanilla JS.
