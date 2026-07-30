#!/usr/bin/env python3
"""Grade the film Deep Oud and rebuild all three film packs in one pass."""
import io
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from oud_deep import grade_frame

HERE = Path(__file__).parent
UHD_PNG = HERE / "uhd_png"          # 2560x1440 source frames (not in the repo)
OUT = HERE / "assets"
COUNT = 300


def one(frame: int):
    """Grade frame `frame` and return its payload for each tier."""
    im = Image.open(UHD_PNG / f"u_{frame:03d}.png").convert("RGB")
    g = grade_frame(im, frame)

    a = io.BytesIO()
    g.save(a, "AVIF", quality=68, speed=6)

    h = io.BytesIO()
    g.resize((1600, 900), Image.LANCZOS).save(h, "AVIF", quality=66, speed=6)

    s = None
    if (frame - 1) % 2 == 0:                      # sd tier is every other frame
        b = io.BytesIO()
        g.resize((1280, 720), Image.LANCZOS).save(b, "WEBP", quality=78, method=6)
        s = b.getvalue()

    return a.getvalue(), h.getvalue(), s


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
    uhd, hd, sd = [], [], []
    with ProcessPoolExecutor() as pool:
        for n, (a, h, s) in enumerate(pool.map(one, range(1, COUNT + 1), chunksize=2), start=1):
            uhd.append(a)
            hd.append(h)
            if s is not None:
                sd.append(s)
            if n % 50 == 0:
                print(f"  graded {n}/{COUNT}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    write_pack(OUT / "film-uhd.avif.bin", uhd, 2560, 1440)
    write_pack(OUT / "film-hd.avif.bin", hd, 1600, 900)
    write_pack(OUT / "film-sd.webp.bin", sd, 1280, 720)


if __name__ == "__main__":
    main()
