# BGS CORNER — Corner 60 FPS

A scroll-driven website for **BGS CORNER**, the House of Oud — a premium
perfume franchise with a vision of one hundred kiosk "corners" in the world's
finest addresses. The hero scrubs a 300-frame product film (crystal flacon →
kiosk reveal) on a full-screen canvas as you scroll.

Oud is the signature and leads the site. A fourth section, **The Objects**,
holds the wider kiosk range — porcelain, calfskin and writing instruments —
styled deliberately quieter than the oud collection so the perfume stays
dominant, and marked as arriving through 2026.

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

## The Deep Oud grade

The source footage shows a colourless liquid in clear crystal. [oud_deep.py](oud_deep.py)
tints the decanter's contents deep oud amber as an offline pass before encoding.

The tint *multiplies* toward amber rather than painting over, so all the crystal's
facet detail — which lives in the luminance — survives, with speculars and the
saturated gold label plate held back, and a depth gradient so the liquid sits
richer toward the base.

Masking is the hard part: the liquid shares its hue (≈30°) with the amber smoke,
the gold label and the wooden table, so colour alone cannot isolate it. Automatic
segmentation was tried and rejected — it latched onto smoke and set dressing, and
jittered frame to frame, which reads as flicker in motion. Instead the mask is
driven by keyframed search boxes per shot, interpolated with a smoothstep so it
never snaps, and then **snapped to the glass contour**: inside each box the
decanter's extent is measured per row from the luminance, so a loose keyframe
still yields a mask that hugs the crystal.

The film is a multi-shot edit, mapped by frame differencing:

| Frames | Shot | Handling |
|---|---|---|
| 1–43 | full decanter, dark ground | contour-snapped |
| 44–88 | stopper macro | untouched — no liquid body in shot |
| 89–~243 | stopper lift, pulling back to the decanter | contour-snapped |
| 244–263 | cross-dissolve into the kiosk | both shots masked on their own ramps |
| 264–300 | kiosk | shaped mask; the bright set defeats contour snapping |

## Rebuilding the packs

The source 8K frames are not in the repo. Extract every 2nd frame to
2560×1440 PNGs first:

```bash
ffmpeg -framerate 60 -i frame_%06d.png -vf "select='not(mod(n\,2))',scale=2560:1440:flags=lanczos" -fps_mode vfr uhd_png/u_%03d.png
```

Then grade and encode all three packs in one pass (needs Pillow with AVIF
support, plus numpy and scipy):

```bash
python3 build_all.py
```

## Run locally

```bash
python3 -m http.server 4560
```

Then open <http://localhost:4560>.

## Stack

No frameworks, no build step — hand-written HTML, CSS and vanilla JS.
Respects `prefers-reduced-motion` throughout.
