/* ═══════════════════════════════════════════════════════════════
   BGS CORNER — scroll-driven hero film
   Frames are packed in a single binary file (assets/frames.bin):
     magic "BGSP" | u32 version | u32 count | u32 w | u32 h |
     u32 lengths[count] | concatenated WebP payloads
   The loader streams the file, slices per-frame blobs as bytes
   arrive, and a windowed decoder keeps ImageBitmaps ready around
   the current scroll position so scrubbing never blocks.
   ═══════════════════════════════════════════════════════════════ */

(() => {
  "use strict";

  const PACK_URL = "assets/frames.bin";
  const DPR_CAP = 2;
  const AHEAD = 22;          // frames decoded ahead of playhead
  const BEHIND = 8;          // frames kept behind playhead
  const MAX_DECODES = 3;     // concurrent decodes

  const canvas = document.getElementById("film");
  const ctx = canvas.getContext("2d");
  const hero = document.querySelector(".hero");
  const loaderEl = document.getElementById("loader");
  const loaderFill = document.getElementById("loader-fill");
  const loaderPct = document.getElementById("loader-pct");
  const cue = document.getElementById("cue");
  const nav = document.getElementById("nav");
  const frame = document.getElementById("hero-frame");
  const copies = [
    document.getElementById("copy-1"),
    document.getElementById("copy-2"),
    document.getElementById("copy-3"),
  ];

  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── state ── */
  let frameW = 0, frameH = 0, count = 0;
  let blobs = [];            // per-frame compressed blobs
  let bitmaps = [];          // per-frame decoded ImageBitmap | null
  let decoding = new Set();
  let ready = false;         // first frame drawn
  let pos = 0;               // smoothed playhead (float frame index)
  let target = 0;            // scroll-derived target frame
  let drawnIdx = -1;
  let lastT = 0;

  /* ── canvas sizing ── */
  function resize() {
    const dpr = Math.min(devicePixelRatio || 1, DPR_CAP);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      drawnIdx = -1; // force redraw
    }
  }
  addEventListener("resize", resize);

  /* ── draw one frame, cover-fit ── */
  function draw(idx) {
    const bmp = bitmaps[idx];
    if (!bmp) return false;
    const cw = canvas.width, ch = canvas.height;
    const s = Math.max(cw / frameW, ch / frameH);
    const dw = frameW * s, dh = frameH * s;
    ctx.drawImage(bmp, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
    drawnIdx = idx;
    return true;
  }

  /* nearest decoded frame at or below idx, else above */
  function nearestReady(idx) {
    for (let d = 0; d < count; d++) {
      if (idx - d >= 0 && bitmaps[idx - d]) return idx - d;
      if (idx + d < count && bitmaps[idx + d]) return idx + d;
    }
    return -1;
  }

  /* ── windowed decoder ── */
  function pump() {
    if (!count) return;
    const c = Math.round(pos);
    // evict far-away bitmaps
    for (let i = 0; i < count; i++) {
      if (bitmaps[i] && (i < c - BEHIND * 2 || i > c + AHEAD * 2)) {
        bitmaps[i].close();
        bitmaps[i] = null;
      }
    }
    // decode the window, nearest-first
    for (let d = 0; d <= AHEAD && decoding.size < MAX_DECODES; d++) {
      for (const i of [c + d, c - d]) {
        if (i < 0 || i >= count || d > (i < c ? BEHIND : AHEAD)) continue;
        if (!blobs[i] || bitmaps[i] || decoding.has(i)) continue;
        decoding.add(i);
        createImageBitmap(blobs[i])
          .then((bmp) => {
            if (bitmaps[i]) bmp.close();
            else bitmaps[i] = bmp;
          })
          .catch(() => {})
          .finally(() => { decoding.delete(i); pump(); });
        if (decoding.size >= MAX_DECODES) break;
      }
    }
  }

  /* ── scroll mapping ── */
  function measure() {
    const rect = hero.getBoundingClientRect();
    const total = hero.offsetHeight - innerHeight;
    const scrolled = Math.min(Math.max(-rect.top, 0), total);
    return total > 0 ? scrolled / total : 0;
  }

  /* hero copy phases: [fadeIn, fullIn, fullOut, fadeOut] in progress space */
  const PHASES = [
    [-0.01, 0.00, 0.16, 0.26],
    [0.30, 0.40, 0.52, 0.62],
    [0.72, 0.82, 1.01, 1.02],
  ];

  function phaseAlpha(p, [a, b, c, d]) {
    if (p <= a || p >= d) return 0;
    if (p < b) return (p - a) / (b - a);
    if (p > c) return 1 - (p - c) / (d - c);
    return 1;
  }

  function updateCopy(p) {
    for (let i = 0; i < copies.length; i++) {
      const a = phaseAlpha(p, PHASES[i]);
      copies[i].style.opacity = a.toFixed(3);
      copies[i].style.transform = `translateY(${((1 - a) * 26).toFixed(1)}px)`;
      copies[i].style.visibility = a > 0.001 ? "visible" : "hidden";
    }
    cue.style.opacity = p < 0.04 && ready ? 1 : 0;
    frame.style.opacity = phaseAlpha(p, PHASES[0]).toFixed(3);
  }

  /* ── main loop ── */
  function tick(t) {
    requestAnimationFrame(tick);
    step(t);
  }

  function step(t) {
    const dt = Math.min(Math.max((t - lastT) / 1000, 0) || 0.016, 0.05);
    lastT = t;

    const p = measure();
    target = p * (count - 1 || 0);
    updateCopy(p);

    if (!ready) return;

    // critically-damped-ish approach to target
    const k = reducedMotion ? 1 : 1 - Math.exp(-9 * dt);
    pos += (target - pos) * k;
    if (Math.abs(target - pos) < 0.02) pos = target;

    pump();

    const want = Math.round(pos);
    if (want !== drawnIdx) {
      if (!draw(want)) {
        const alt = nearestReady(want);
        if (alt >= 0 && alt !== drawnIdx) draw(alt);
      }
    }
  }

  /* ── pack streaming loader ── */
  async function load() {
    const res = await fetch(PACK_URL);
    if (!res.ok) throw new Error(`frames.bin: HTTP ${res.status}`);
    const totalBytes = +res.headers.get("Content-Length") || 0;

    let received = 0;
    let header = null;   // {n, offsets[]}
    let buf = new Uint8Array(totalBytes || 1 << 20);
    let nextFrame = 0;

    const reader = res.body.getReader();

    const append = (chunk) => {
      if (received + chunk.length > buf.length) {
        const grown = new Uint8Array(Math.max(buf.length * 2, received + chunk.length));
        grown.set(buf.subarray(0, received));
        buf = grown;
      }
      buf.set(chunk, received);
      received += chunk.length;
    };

    const tryParseHeader = () => {
      if (received < 20) return;
      const dv = new DataView(buf.buffer);
      if (dv.getUint32(0) !== 0x42475350) throw new Error("bad magic"); // "BGSP"
      const n = dv.getUint32(8, true);
      if (received < 20 + n * 4) return;
      frameW = dv.getUint32(12, true);
      frameH = dv.getUint32(16, true);
      const offsets = [20 + n * 4];
      for (let i = 0; i < n; i++) offsets.push(offsets[i] + dv.getUint32(20 + i * 4, true));
      header = { n, offsets };
      count = n;
      blobs = new Array(n).fill(null);
      bitmaps = new Array(n).fill(null);
    };

    const sliceReadyFrames = () => {
      if (!header) return;
      while (nextFrame < header.n && received >= header.offsets[nextFrame + 1]) {
        blobs[nextFrame] = new Blob(
          [buf.subarray(header.offsets[nextFrame], header.offsets[nextFrame + 1])],
          { type: "image/webp" }
        );
        nextFrame++;
      }
    };

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      append(value);
      if (!header) tryParseHeader();
      sliceReadyFrames();

      if (totalBytes) {
        const pct = Math.round((received / totalBytes) * 100);
        loaderFill.style.width = pct + "%";
        loaderPct.textContent = pct + "%";
      }

      // first paint as soon as frame 0 exists
      if (!ready && blobs[0]) {
        ready = true;
        resize();
        createImageBitmap(blobs[0]).then((bmp) => {
          bitmaps[0] = bmp;
          if (drawnIdx < 0) draw(0);
          loaderEl.classList.add("done");
        });
      }
    }

    sliceReadyFrames();
    loaderFill.style.width = "100%";
    loaderEl.classList.add("done");
    pump();

    // hand the corner section a still of the final frame — no extra
    // image files needed in the repo
    const img = document.getElementById("corner-img");
    if (img && blobs[count - 1]) img.src = URL.createObjectURL(blobs[count - 1]);
  }

  /* ── nav + reveals ── */
  addEventListener("scroll", () => {
    nav.classList.toggle("solid", scrollY > innerHeight * 0.6);
  }, { passive: true });

  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }
  }, { threshold: 0.18, rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  /* ── go ── */
  resize();
  updateCopy(0);
  requestAnimationFrame(tick);

  // dev/test hook: lets tooling drive the loop when rAF is throttled
  window.__bgs = {
    info: () => ({
      count, ready,
      pos: +pos.toFixed(2), target: +target.toFixed(2), drawnIdx,
      buffered: blobs.filter(Boolean).length,
      decoded: bitmaps.filter(Boolean).length,
    }),
    step: (t) => step(t),
  };
  load().catch((err) => {
    console.error(err);
    loaderPct.textContent = "The film could not be loaded.";
  });
})();
