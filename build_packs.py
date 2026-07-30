#!/usr/bin/env python3
"""Build the BGS CORNER hero film packs from the 8K source frames.

Produces two packs in the repo's assets/ directory:
  film-uhd.avif.bin  2560x1440 AVIF q68  — large viewports
  film-hd.webp.bin   1600x900  WebP q82  — small viewports / no AVIF support

Pack format (v1):
  b"BGSP" | u32 version | u32 count | u32 width | u32 height
  u32 lengths[count] (little-endian) | concatenated payloads
"""
import io
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

SCRATCH = Path(__file__).parent
UHD_PNG = SCRATCH / "uhd_png"
OUT = Path("/Users/ajoomama/github/corner-60-fps/assets")


def encode_pair(path: Path):
    """Return (avif_uhd_bytes, webp_hd_bytes) for one frame."""
    im = Image.open(path).convert("RGB")

    a = io.BytesIO()
    im.save(a, "AVIF", quality=68, speed=6)

    hd = im.resize((1600, 900), Image.LANCZOS)
    w = io.BytesIO()
    hd.save(w, "WEBP", quality=82, method=6)

    return a.getvalue(), w.getvalue()


def write_pack(path: Path, payloads, w: int, h: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"BGSP")
        f.write(struct.pack("<IIII", 1, len(payloads), w, h))
        for p in payloads:
            f.write(struct.pack("<I", len(p)))
        for p in payloads:
            f.write(p)
    sizes = sorted(len(p) for p in payloads)
    print(f"{path.name}: {len(payloads)} frames {w}x{h}  "
          f"pack={path.stat().st_size/1e6:.1f} MB  "
          f"median={sizes[len(sizes)//2]/1024:.0f}K max={sizes[-1]/1024:.0f}K",
          flush=True)


def main() -> None:
    files = sorted(UHD_PNG.glob("u_*.png"))
    assert files, f"no frames in {UHD_PNG}"
    print(f"encoding {len(files)} frames...", flush=True)

    avifs, webps = [], []
    with ProcessPoolExecutor() as pool:
        for i, (a, w) in enumerate(pool.map(encode_pair, files, chunksize=2)):
            avifs.append(a)
            webps.append(w)
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(files)}", flush=True)

    write_pack(OUT / "film-uhd.avif.bin", avifs, 2560, 1440)
    write_pack(OUT / "film-hd.webp.bin", webps, 1600, 900)


if __name__ == "__main__":
    main()
