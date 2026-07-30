#!/usr/bin/env python3
"""Build the smaller BGS CORNER film tiers from the 2560x1440 intermediates.

  film-hd.avif.bin   1600x900  AVIF q66, 300 frames — small/mid viewports
  film-sd.webp.bin   1280x720  WebP q78, 150 frames — no-AVIF compatibility
"""
import io
import struct
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

SCRATCH = Path(__file__).parent
UHD_PNG = SCRATCH / "uhd_png"
OUT = Path("/Users/ajoomama/github/corner-60-fps/assets")


def hd(path: Path) -> bytes:
    im = Image.open(path).convert("RGB").resize((1600, 900), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "AVIF", quality=66, speed=6)
    return b.getvalue()


def sd(path: Path) -> bytes:
    im = Image.open(path).convert("RGB").resize((1280, 720), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "WEBP", quality=78, method=6)
    return b.getvalue()


def write_pack(path: Path, payloads, w: int, h: int) -> None:
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
          f"median={sizes[len(sizes)//2]/1024:.0f}K max={sizes[-1]/1024:.0f}K", flush=True)


def main() -> None:
    files = sorted(UHD_PNG.glob("u_*.png"))
    assert files, f"no frames in {UHD_PNG}"

    with ProcessPoolExecutor() as pool:
        write_pack(OUT / "film-hd.avif.bin", list(pool.map(hd, files, chunksize=2)), 1600, 900)
        # compatibility tier: every other frame of the 300 = 150
        write_pack(OUT / "film-sd.webp.bin",
                   list(pool.map(sd, files[::2], chunksize=2)), 1280, 720)


if __name__ == "__main__":
    main()
