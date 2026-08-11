#!/usr/bin/env python3
"""Encode the hero film into the three packs the site actually loads.

Reads 2560x1440 frames from uhd_png/ (u_001.png, u_002.png, ...) and writes:

  assets/film-uhd.avif.bin   2560x1440  AVIF q68  every frame
  assets/film-hd.avif.bin    1600x900   AVIF q66  every frame
  assets/film-sd.webp.bin    1280x720   WebP q78  every other frame

Pack format:
  b"BGSP" | u32 version | u32 count | u32 width | u32 height
  u32 lengths[count] (little-endian) | concatenated payloads

Frame count is taken from the directory, so a film of any length works. After
running, bump FILM_VERSION in main.js so returning visitors are not served the
previous film from cache.
"""
import io
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
UHD_PNG = HERE / "uhd_png"          # not in the repo; see README
OUT = HERE / "assets"

TIERS = [
    ("film-uhd.avif.bin", (2560, 1440), "AVIF", dict(quality=68, speed=6), 1),
    ("film-hd.avif.bin",  (1600, 900),  "AVIF", dict(quality=66, speed=6), 1),
    ("film-sd.webp.bin",  (1280, 720),  "WEBP", dict(quality=78, method=6), 2),
]


def encode(path: Path):
    """Return one payload per tier for a single frame."""
    im = Image.open(path).convert("RGB")
    out = []
    for _, size, fmt, opts, _ in TIERS:
        buf = io.BytesIO()
        (im if im.size == size else im.resize(size, Image.LANCZOS)).save(buf, fmt, **opts)
        out.append(buf.getvalue())
    return out


def write_pack(path: Path, payloads, size) -> None:
    w, h = size
    with open(path, "wb") as f:
        f.write(b"BGSP")
        f.write(struct.pack("<IIII", 1, len(payloads), w, h))
        for p in payloads:
            f.write(struct.pack("<I", len(p)))
        for p in payloads:
            f.write(p)
    sizes = sorted(len(p) for p in payloads)
    print(f"  {path.name:22} {len(payloads):>4} frames  {w}x{h:<5} "
          f"{path.stat().st_size/1e6:5.1f} MB   median {sizes[len(sizes)//2]/1024:.0f}K",
          flush=True)


def main() -> None:
    files = sorted(UHD_PNG.glob("u_*.png"))
    if not files:
        sys.exit(f"no frames in {UHD_PNG} — see the README for the ffmpeg step")
    print(f"encoding {len(files)} frames into {len(TIERS)} tiers...", flush=True)

    buckets = [[] for _ in TIERS]
    with ProcessPoolExecutor() as pool:
        for n, payloads in enumerate(pool.map(encode, files, chunksize=2), start=1):
            for t, (bucket, tier) in enumerate(zip(buckets, TIERS)):
                if (n - 1) % tier[4] == 0:
                    bucket.append(payloads[t])
            if n % 50 == 0:
                print(f"    {n}/{len(files)}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    for bucket, (name, size, *_ ) in zip(buckets, TIERS):
        write_pack(OUT / name, bucket, size)

    print(f"\nframe count is {len(files)} — bump FILM_VERSION in main.js")


if __name__ == "__main__":
    main()
