#!/usr/bin/env python3
"""Tint the decanter's contents Deep Oud across the 300-frame film.

The film is a multi-shot edit (hard cuts at 44 and 89, a dissolve into the
kiosk over 237-264), so the mask is driven by keyframed search boxes that
are interpolated per frame, then *snapped to the actual glass contour*:
inside each box the bottle's left/right extent is measured per row from the
luminance, so a loose keyframe still yields a mask that hugs the crystal.

Frames 44-88 are the stopper macro — no liquid body is in shot, so they are
left untouched.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LUM = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

# Deep Oud (variant C)
TINT = np.array([0.62, 0.26, 0.09], dtype=np.float32)
BASE, DEPTH_GAIN, MUL, ADD = 0.46, 0.54, 0.70, 0.12

BRIGHT = 0.30       # luminance treated as glass
FEATHER = 9
MIN_ROW_PX = 24     # ignore rows with too little glass

# Keyframed search boxes: frame -> (x0, y0, x1, y1)
SHOT_A = {1: (1150, 780, 1450, 1310), 43: (1050, 1100, 1400, 1440)}
# Shot C ends by rising out of frame while the kiosk dissolves in behind it,
# so it needs keyframes through the transition, not a static box.
SHOT_C = {89: (1000, 1200, 1540, 1440),
          140: (960, 1160, 1560, 1440),
          236: (1160, 810, 1450, 1300),
          243: (1150, 560, 1490, 1100),
          250: (1141, 160, 1500, 720)}
SHOT_D = {265: (1148, 828, 1358, 1215), 300: (1145, 828, 1372, 1240)}

# The two shots overlap on screen during the cross-dissolve, in different
# places, so each mask gets its own ramp rather than one shared weight.
C_OUT = (244, 254)      # studio bottle: fully tinted until it starts leaving
D_IN = (246, 263)       # kiosk bottle: fades in as the kiosk resolves

# Shots A and C sit against a dark ground, so the mask can be snapped to the
# glass contour. In the kiosk the background is as bright as the decanter, so
# contour snapping wanders — there we use the measured box as a shaped mask.
SNAP_A_C, SNAP_D = True, False


def _interp(keys, f):
    ks = sorted(keys)
    if f <= ks[0]:
        return keys[ks[0]]
    if f >= ks[-1]:
        return keys[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= f <= b:
            t = (f - a) / (b - a)
            t = t * t * (3 - 2 * t)          # ease, so the mask never snaps
            pa, pb = keys[a], keys[b]
            return tuple(pa[i] + (pb[i] - pa[i]) * t for i in range(4))
    return keys[ks[-1]]


def _ramp(frame, lo, hi, rising):
    if frame <= lo:
        return 1.0 if not rising else 0.0
    if frame >= hi:
        return 0.0 if not rising else 1.0
    t = (frame - lo) / (hi - lo)
    return t if rising else 1.0 - t


def boxes_for(frame):
    """Return [(box, weight, snap), ...] active on this frame."""
    if 44 <= frame <= 88:          # stopper macro: no liquid body in shot
        return []
    if frame <= 43:
        return [(_interp(SHOT_A, frame), 1.0, SNAP_A_C)]

    out = []
    wc = _ramp(frame, *C_OUT, rising=False)
    if wc > 0.001:
        out.append((_interp(SHOT_C, frame), wc, SNAP_A_C))
    wd = _ramp(frame, *D_IN, rising=True)
    if wd > 0.001:
        out.append((_interp(SHOT_D, frame), wd, SNAP_D))
    return out


def shaped_mask(shape, box):
    """A rounded-rectangle body mask, for shots where snapping is unsafe."""
    H, W = shape
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    img = Image.new("L", (W, H), 0)
    ImageDraw.Draw(img).rounded_rectangle(
        [x0, y0, x1, y1], radius=max(6, int((x1 - x0) * 0.16)), fill=255)
    return np.asarray(img).astype(np.float32) / 255.0, y0, y1


def contour_mask(lum, box):
    """Mask hugging the glass inside `box`, from per-row bright extents."""
    H, W = lum.shape
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, x1 = max(0, x0), min(W, x1)
    y0, y1 = max(0, y0), min(H, y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None

    sub = lum[y0:y1, x0:x1] > BRIGHT
    m = np.zeros((H, W), dtype=np.float32)
    any_row = False
    for r in range(sub.shape[0]):
        idx = np.flatnonzero(sub[r])
        if idx.size < MIN_ROW_PX:
            continue
        # percentiles reject stray highlights outside the glass
        lo = int(np.percentile(idx, 3))
        hi = int(np.percentile(idx, 97))
        if hi - lo < 8:
            continue
        m[y0 + r, x0 + lo:x0 + hi + 1] = 1.0
        any_row = True
    if not any_row:
        return None
    return m, y0, y1


def grade_frame(im: Image.Image, frame: int) -> Image.Image:
    a = np.asarray(im).astype(np.float32) / 255.0
    active = boxes_for(frame)
    if not active:
        return im

    H, W = a.shape[:2]
    lum2 = (a * LUM).sum(2)
    lum = lum2[:, :, None]

    # gold label plate: saturated + bright -> keep it as artwork
    mx, mn = a.max(2), a.min(2)
    sat = np.where(mx > 1e-5, (mx - mn) / np.maximum(mx, 1e-5), 0.0)
    label = np.clip((sat - 0.34) / 0.22, 0, 1) * np.clip((lum2 - 0.30) / 0.25, 0, 1)
    label = np.asarray(
        Image.fromarray((label * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    ).astype(np.float32) / 255.0

    spec = np.clip((lum - 0.78) / 0.22, 0, 1)
    tinted = a * TINT[None, None, :] * MUL + (lum * TINT[None, None, :]) * ADD

    total = np.zeros((H, W, 1), dtype=np.float32)
    for box, weight, snap in active:
        if weight <= 0.001:
            continue
        got = contour_mask(lum2, box) if snap else shaped_mask((H, W), box)
        if got is None:
            continue
        m, y0, y1 = got
        m = np.asarray(
            Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(FEATHER))
        ).astype(np.float32) / 255.0

        yy = np.arange(H, dtype=np.float32)[:, None, None]
        depth = np.clip((yy - y0) / max(y1 - y0, 1), 0, 1)
        s = (BASE + DEPTH_GAIN * depth) * (m * (1.0 - 0.9 * label))[:, :, None]
        total = np.maximum(total, s * weight)

    k = np.clip(total, 0, 1) * (1.0 - 0.85 * spec)
    out = np.clip(a * (1 - k) + tinted * k, 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8))
