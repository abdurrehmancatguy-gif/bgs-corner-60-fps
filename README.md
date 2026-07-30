# BGS CORNER — Corner 60 FPS

A scroll-driven website for **BGS CORNER**, the House of Oud — a premium
perfume franchise with a vision of one hundred kiosk "corners" in the world's
finest addresses. The hero scrubs a 300-frame product film (crystal flacon →
kiosk reveal) on a full-screen canvas as you scroll.

## The hero film

Frames are **not** committed as individual images. Each quality tier is one
binary pack in [assets/](assets):

| Pack | Resolution | Frames | Codec | Size |
|---|---|---|---|---|
| `film-uhd.avif.bin` | 2560×1440 | 300 | AVIF q68 | 15.0 MB |
| `film-hd.avif.bin` | 1600×900 | 300 | AVIF q66 | 9.3 MB |
| `film-sd.webp.bin` | 1280×720 | 150 | WebP q78 | 4.4 MB |

Pack format:

```
"BGSP" | u32 version | u32 count | u32 width | u32 height
u32 lengths[count]        (little-endian)
concatenated payloads
```

`main.js` picks one tier from viewport size, pixel density, `saveData` and
`effectiveType`, then streams it: per-frame blobs are sliced as bytes arrive,
so the first frame paints long before the download completes. A decode window
sized to a fixed ~110 MB memory budget keeps ImageBitmaps ready around the
playhead, so scrubbing never blocks the main thread. Exactly one pack is
downloaded per visitor.

AVIF was chosen over WebP after measuring both at 2560×1440: it is **half the
size and roughly twice as fast to decode** (14 ms vs 30 ms per frame), and
visually indistinguishable from the 8K source at full crop. The WebP tier
exists only for browsers without AVIF support.

## Rebuilding the packs

The source 8K frames are not in the repo. Extract every 2nd frame to
2560×1440 PNGs first:

```bash
ffmpeg -framerate 60 -i frame_%06d.png -vf "select='not(mod(n\,2))',scale=2560:1440:flags=lanczos" -fps_mode vfr uhd_png/u_%03d.png
```

Then encode the packs (requires Pillow with AVIF support):

```bash
python3 build_packs.py && python3 build_tiers.py
```

## Run locally

```bash
python3 -m http.server 4560
```

Then open <http://localhost:4560>.

## Stack

No frameworks, no build step — hand-written HTML, CSS and vanilla JS.
Respects `prefers-reduced-motion` throughout.
