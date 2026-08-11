# BGS CORNER — Corner 60 FPS

A scroll-driven website for **BGS CORNER**, the House of Oud — a perfumer
selling rare ouds and perfumes from Rigga Al Buteen, Dubai. The hero scrubs a
301-frame product film (house seal → boxed flacons → shop) on a full-screen canvas
as you scroll.

Oud is the signature and the site carries nothing else: four sections —
The House, The Oud, The Collection and The Corner. An earlier draft pitched a
hundred-kiosk expansion and a range of house objects; both were cut, and are
in the history if they are ever wanted back.

## The hero film

Frames are **not** committed as individual images. Each quality tier is one
binary pack in [assets/](assets):

| Pack | Resolution | Frames | Codec | Size |
|---|---|---|---|---|
| `film-uhd.avif.bin` | 2560×1440 | 301 | AVIF q68 | 22.9 MB |
| `film-hd.avif.bin` | 1600×900 | 301 | AVIF q66 | 14.3 MB |
| `film-sd.webp.bin` | 1280×720 | 151 | WebP q78 | 6.3 MB |

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

The source frames are not in the repo. Downscale them to 2560×1440 first —
`uhd_png/` is gitignored, so it can live in the repo directory:

```bash
ffmpeg -i frames/frame_%04d.png -vf "scale=2560:1440:flags=lanczos" uhd_png/u_%03d.png
```

Then encode all three tiers in one pass (needs Pillow with AVIF support):

```bash
python3 build_film.py
```

Frame count is read from the directory, so a film of any length works. Two
things must follow a rebuild:

- bump `FILM_VERSION` in [main.js](main.js), or returning visitors keep the
  cached film;
- re-time `PHASES` in [main.js](main.js). The three hero copy panels are placed
  against specific beats in the current film, so new footage needs new numbers.


## Run locally

```bash
python3 -m http.server 4560
```

Then open <http://localhost:4560>.

## Stack

No frameworks, no build step — hand-written HTML, CSS and vanilla JS.
Respects `prefers-reduced-motion` throughout.
