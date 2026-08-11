/* ═══════════════════════════════════════════════════════════════
   BGS CORNER — scroll-driven hero film + reveal choreography

   The film ships as a single binary pack per quality tier:
     "BGSP" | u32 version | u32 count | u32 w | u32 h |
     u32 lengths[count] | concatenated image payloads

   The loader picks a tier from screen size, pixel density and the
   network, streams the pack, and slices per-frame blobs as bytes
   arrive so the first frame paints long before the download ends.
   A decode window sized to a fixed memory budget keeps ImageBitmaps
   ready around the playhead, so scrubbing never blocks the main
   thread.
   ═══════════════════════════════════════════════════════════════ */

(() => {
  "use strict";

  /* Bump ONLY when assets/film-*.bin are rebuilt. The packs are large and are
     served without cache headers by most static hosts, so browsers will happily
     reuse a stale copy for a long time; versioning the URL makes a rebuild
     reach visitors who already have the old film cached. Changing this forces a
     multi-megabyte re-download, so it is independent of the ?v= on the script
     and stylesheet in index.html — bump that one for code changes. */
  const FILM_VERSION = "4";

  /* Quality tiers, best first. `min` is the required viewport width in
     device pixels; AVIF tiers are skipped when the browser can't decode it. */
  const TIERS = [
    { url: "assets/film-uhd.avif.bin", mime: "image/avif", min: 1700, avif: true },
    { url: "assets/film-hd.avif.bin",  mime: "image/avif", min: 0,    avif: true },
    { url: "assets/film-sd.webp.bin",  mime: "image/webp", min: 0,    avif: false },
  ];

  const DPR_CAP = 2;
  const MAX_DECODES = 6;     // concurrent createImageBitmap calls
  const AHEAD_RATIO = 0.72;  // share of the window that sits ahead of the playhead

  /* Decoded bitmaps are the memory cost of smooth scrubbing: one 2560×1440
     frame is ~14.7 MB as RGBA. Scale what we hold to the device. */
  const MEM_BUDGET = (() => {
    const gb = navigator.deviceMemory || 4;
    return Math.min(200e6, Math.max(90e6, gb * 22e6));
  })();

  const canvas = document.getElementById("film");
  const ctx = canvas.getContext("2d", { alpha: false });
  const hero = document.querySelector(".hero");
  const curtain = document.getElementById("curtain");
  const curtainFill = document.getElementById("curtain-fill");
  const progressBar = document.getElementById("progress-bar");
  const cue = document.getElementById("cue");
  const nav = document.getElementById("nav");
  const frameRule = document.getElementById("hero-frame");
  const brand = document.querySelector(".brand");
  const copies = [
    document.getElementById("copy-1"),
    document.getElementById("copy-2"),
    document.getElementById("copy-3"),
  ];

  /* Hero parallax. The headline rides further than the small type, so the
     block reads as layered depth rather than one flat plane sliding. */
  const POINTER_BLOCK = 17;   // px the whole copy block travels with the pointer
  const POINTER_LEAD = 12;    // extra px for the headline itself
  const RISE = 54;            // px the copy rises as it fades in

  const heroLayers = copies.map((el) => ({
    el,
    lead: el.querySelector(".brand, .line"),
  }));

  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── state ── */
  let frameW = 0, frameH = 0, count = 0;
  let blobs = [];      // compressed per-frame blobs
  let bitmaps = [];    // decoded ImageBitmap | null
  const decoding = new Set();
  let ahead = 12, behind = 5;
  let ready = false;
  let pos = 0, target = 0, drawnIdx = -1, lastT = 0;
  let pointerX = 0, pointerY = 0, pointerLerpX = 0, pointerLerpY = 0;

  /* ── canvas sizing ── */
  function resize() {
    const dpr = Math.min(devicePixelRatio || 1, DPR_CAP);
    const w = Math.round(canvas.clientWidth * dpr);
    const h = Math.round(canvas.clientHeight * dpr);
    if (w && h && (canvas.width !== w || canvas.height !== h)) {
      canvas.width = w;
      canvas.height = h;
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      drawnIdx = -1;
    }
  }
  addEventListener("resize", resize);

  /* ── draw one frame, cover-fit ── */
  function draw(idx) {
    const bmp = bitmaps[idx];
    if (!bmp || !canvas.width) return false;
    const cw = canvas.width, ch = canvas.height;
    const s = Math.max(cw / frameW, ch / frameH);
    const dw = frameW * s, dh = frameH * s;
    ctx.drawImage(bmp, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
    drawnIdx = idx;
    return true;
  }

  function nearestReady(idx) {
    for (let d = 1; d < count; d++) {
      if (idx - d >= 0 && bitmaps[idx - d]) return idx - d;
      if (idx + d < count && bitmaps[idx + d]) return idx + d;
    }
    return -1;
  }

  /* ── windowed decoder ── */
  function pump() {
    if (!count) return;
    const c = Math.round(pos);

    for (let i = 0; i < count; i++) {
      if (bitmaps[i] && (i < c - behind || i > c + ahead)) {
        bitmaps[i].close();
        bitmaps[i] = null;
      }
    }

    for (let d = 0; d <= ahead && decoding.size < MAX_DECODES; d++) {
      for (const i of d === 0 ? [c] : [c + d, c - d]) {
        if (i < 0 || i >= count) continue;
        if (i < c && c - i > behind) continue;
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
  function heroProgress() {
    const total = hero.offsetHeight - innerHeight;
    const scrolled = Math.min(Math.max(-hero.getBoundingClientRect().top, 0), total);
    return total > 0 ? scrolled / total : 0;
  }

  /* hero copy phases in film-progress space: [in-start, in-end, out-start, out-end] */
  /* Retimed for the current film, whose beats are: monogram plaque -> boxes ->
     reveal -> bottles -> macro -> shop. The footage also carries burned-in
     captions ("PURE OUD" left, "24K GOLD BAR" right) through most of its
     length, so each panel is placed where they are absent or weakest: the
     opening (frames 1-55), the mid-bottle run where the left caption drops
     out (~136-193), and the closing shop (from ~271). */
  const PHASES = [
    [-0.01, 0.00, 0.12, 0.18],
    [0.45, 0.51, 0.58, 0.64],
    [0.90, 0.95, 1.01, 1.02],
  ];

  function phaseAlpha(p, [a, b, c, d]) {
    if (p <= a || p >= d) return 0;
    if (p < b) return (p - a) / (b - a);
    if (p > c) return 1 - (p - c) / (d - c);
    return 1;
  }

  function updateHero(p) {
    for (let i = 0; i < heroLayers.length; i++) {
      const a = phaseAlpha(p, PHASES[i]);
      const { el, lead } = heroLayers[i];
      if (a <= 0.001) {
        el.style.visibility = "hidden";
        el.style.opacity = "0";
        continue;
      }
      const rise = (1 - a) * RISE;
      const scale = 0.965 + a * 0.035;
      el.style.visibility = "visible";
      el.style.opacity = a.toFixed(3);
      el.style.transform =
        `translate3d(${(pointerLerpX * POINTER_BLOCK).toFixed(2)}px, ` +
        `${(rise + pointerLerpY * POINTER_BLOCK).toFixed(2)}px, 0) ` +
        `scale(${scale.toFixed(4)})`;
      if (lead) {
        lead.style.transform =
          `translate3d(${(pointerLerpX * POINTER_LEAD).toFixed(2)}px, ` +
          `${(pointerLerpY * POINTER_LEAD).toFixed(2)}px, 0)`;
      }
    }
    cue.style.opacity = p < 0.035 && ready ? "1" : "0";
    frameRule.style.opacity = phaseAlpha(p, PHASES[0]).toFixed(3);
  }

  /* ── main loop ── */
  function tick(t) {
    requestAnimationFrame(tick);
    step(t);
  }

  function step(t) {
    const dt = Math.min(Math.max((t - lastT) / 1000, 0) || 0.016, 0.05);
    lastT = t;

    const k = reduced ? 1 : 1 - Math.exp(-6.5 * dt);
    pointerLerpX += (pointerX - pointerLerpX) * (reduced ? 1 : 1 - Math.exp(-4 * dt));
    pointerLerpY += (pointerY - pointerLerpY) * (reduced ? 1 : 1 - Math.exp(-4 * dt));

    const p = heroProgress();
    target = p * (count - 1 || 0);
    updateHero(p);

    const doc = document.documentElement;
    const max = doc.scrollHeight - innerHeight;
    progressBar.style.transform = `scaleX(${max > 0 ? (scrollY / max).toFixed(4) : 0})`;

    if (!ready) return;

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

  /* ── tier selection ── */
  /* A real 1×1 AVIF, encoded by the same toolchain that built the packs. */
  const AVIF_PROBE_B64 =
    "AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADrbWV0YQAAAAAAAAAhaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAAAAAAAOcGl0bQAAAAAAAQAAAB5pbG9jAAAAAEQAAAEAAQAAAAEAAAETAAAAFwAAAChpaW5mAAAAAAABAAAAGmluZmUCAAAAAAEAAGF2MDFDb2xvcgAAAABqaXBycAAAAEtpcGNvAAAAFGlzcGUAAAAAAAAAAQAAAAEAAAAQcGl4aQAAAAADCAgIAAAADGF2MUOBAAwAAAAAE2NvbHJuY2x4AAEADQAGgAAAABdpcG1hAAAAAAAAAAEAAQQBAoMEAAAAH21kYXQSAAoFGAAGBCAyDBmAEEEEBAAAsBNR4A==";

  /* Probe with createImageBitmap — the same call the film decodes through.
     HTMLImageElement.decode() is unreliable here: it can hang indefinitely
     while the document is hidden, which would stall the film in a background
     tab. The timeout is a last resort so loading can never block on this. */
  async function avifSupported() {
    try {
      const bin = atob(AVIF_PROBE_B64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const blob = new Blob([bytes], { type: "image/avif" });
      const bmp = await Promise.race([
        createImageBitmap(blob),
        new Promise((_, rej) => setTimeout(() => rej(new Error("probe timeout")), 2500)),
      ]);
      const ok = bmp.width > 0;
      bmp.close();
      return ok;
    } catch { return false; }
  }

  async function pickTier() {
    const avif = await avifSupported();
    const conn = navigator.connection || {};
    // Only genuinely constrained connections drop the top tier. "3g" is
    // reported liberally — often on connections that carry the 2K film
    // perfectly well — so a large screen keeps full quality, and only an
    // explicit data-saving preference or a 2g class downgrades it.
    const slow = conn.saveData === true ||
                 /^(slow-)?2g$/.test(conn.effectiveType || "");
    // Judge the display, not the current window: a narrow window on a large
    // retina screen still deserves the high tier, and some embedders report a
    // zero-width viewport before first paint.
    const cssPx = Math.max(
      innerWidth || 0,
      document.documentElement.clientWidth || 0,
      (screen && screen.width) || 0
    );
    const devicePx = cssPx * Math.min(devicePixelRatio || 1, DPR_CAP);
    for (const t of TIERS) {
      if (t.avif && !avif) continue;
      if (t.min && (slow || devicePx < t.min)) continue;
      return t;
    }
    return TIERS[TIERS.length - 1];
  }

  /* ── streaming pack loader ── */
  async function load() {
    const tier = await pickTier();
    const res = await fetch(`${tier.url}?v=${FILM_VERSION}`);
    if (!res.ok) throw new Error(`${tier.url}: HTTP ${res.status}`);
    const totalBytes = +res.headers.get("Content-Length") || 0;

    let received = 0;
    let header = null;
    let buf = new Uint8Array(totalBytes || 1 << 21);
    let nextFrame = 0;

    const append = (chunk) => {
      if (received + chunk.length > buf.length) {
        const grown = new Uint8Array(Math.max(buf.length * 2, received + chunk.length));
        grown.set(buf.subarray(0, received));
        buf = grown;
      }
      buf.set(chunk, received);
      received += chunk.length;
    };

    const tryHeader = () => {
      if (received < 20) return;
      const dv = new DataView(buf.buffer);
      if (dv.getUint32(0) !== 0x42475350) throw new Error("bad pack magic");
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

      // size the decode window to the memory budget for this tier
      const perFrame = frameW * frameH * 4;
      const slots = Math.max(6, Math.min(48, Math.floor(MEM_BUDGET / perFrame)));
      ahead = Math.max(4, Math.round(slots * AHEAD_RATIO));
      behind = Math.max(2, slots - ahead);
    };

    const sliceReady = () => {
      if (!header) return;
      while (nextFrame < header.n && received >= header.offsets[nextFrame + 1]) {
        blobs[nextFrame] = new Blob(
          [buf.subarray(header.offsets[nextFrame], header.offsets[nextFrame + 1])],
          { type: tier.mime }
        );
        nextFrame++;
      }
    };

    const reader = res.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      append(value);
      if (!header) tryHeader();
      sliceReady();

      if (totalBytes) {
        curtainFill.style.transform = `scaleX(${(received / totalBytes).toFixed(4)})`;
      }

      if (!ready && blobs[0]) {
        ready = true;
        resize();
        const bmp = await createImageBitmap(blobs[0]);
        bitmaps[0] = bmp;
        if (drawnIdx < 0) draw(0);
        openCurtain();
      }
    }

    sliceReady();
    curtainFill.style.transform = "scaleX(1)";
    pump();

    // the corner section reuses the film's closing frame — no extra image
    // file ships in the repo
    const img = document.getElementById("corner-img");
    if (img && blobs[count - 1]) img.src = URL.createObjectURL(blobs[count - 1]);

    return { tier: tier.url, count, frameW, frameH, ahead, behind };
  }

  let curtainOpened = false;
  function openCurtain() {
    if (curtainOpened) return;
    curtainOpened = true;
    setTimeout(() => {
      curtain.classList.add("lift");
      if (brand) brand.classList.add("lit");
    }, reduced ? 0 : 480);
  }

  /* ── wordmark letter stagger ── */
  if (brand && !reduced) {
    for (const node of [...brand.childNodes]) {
      if (node.nodeType !== Node.TEXT_NODE) continue;
      const frag = document.createDocumentFragment();
      for (const chn of node.textContent) {
        const s = document.createElement("span");
        s.className = "ch";
        s.textContent = chn;
        frag.appendChild(s);
      }
      node.replaceWith(frag);
    }
    brand.querySelectorAll(".ch").forEach((s, i) => {
      s.style.transitionDelay = (i * 0.055).toFixed(3) + "s";
    });
  } else if (brand) {
    brand.classList.add("lit");
  }

  /* ── masked line reveals: wrap each line's contents in an inner span ── */
  document.querySelectorAll("[data-lines] > span").forEach((line) => {
    const inner = document.createElement("span");
    while (line.firstChild) inner.appendChild(line.firstChild);
    line.appendChild(inner);
  });

  /* ── reveal observer ── */
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      e.target.classList.add("in");
      io.unobserve(e.target);
    }
  }, { threshold: 0.15, rootMargin: "0px 0px -8% 0px" });

  document
    .querySelectorAll("[data-reveal], [data-lines], .tex, .draw")
    .forEach((el) => io.observe(el));

  /* ── enquiry dialog ──────────────────────────────────────────
     The trigger stays an ordinary mailto link, so with no JS (or no
     <dialog> support) the click still reaches a mail client. */
  const enquire = document.getElementById("enquire");
  if (enquire && typeof enquire.showModal === "function") {
    document.querySelectorAll("[data-enquire]").forEach((trigger) => {
      trigger.addEventListener("click", (e) => {
        e.preventDefault();
        enquire.showModal();
      });
    });
    enquire.querySelector(".enquire-close")?.addEventListener("click", () => enquire.close());
    // clicking the backdrop (the dialog's own box, outside the panel) closes it
    enquire.addEventListener("click", (e) => {
      if (e.target === enquire) enquire.close();
    });
  }

  /* ── legal dialog ─────────────────────────────────────────────
     One panel, three documents; the trigger picks which pane shows. */
  const legal = document.getElementById("legal");
  if (legal && typeof legal.showModal === "function") {
    const titles = { terms: "Terms & Conditions", privacy: "Privacy Policy" };
    const label = legal.querySelector(".legal-title");
    const body = legal.querySelector(".legal-body");

    document.querySelectorAll("[data-legal]").forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const want = trigger.dataset.legal;
        legal.querySelectorAll(".legal-pane").forEach((pane) => {
          pane.hidden = pane.id !== `legal-${want}`;
        });
        label.textContent = titles[want] || "Legal";
        legal.showModal();
        body.scrollTop = 0;              // each document opens at its start
      });
    });
    legal.querySelector(".legal-close")?.addEventListener("click", () => legal.close());
    legal.addEventListener("click", (e) => {
      if (e.target === legal) legal.close();
    });
  }

  /* ── nav state + image parallax ── */
  addEventListener("scroll", () => {
    nav.classList.toggle("solid", scrollY > innerHeight * 0.55);
  }, { passive: true });

  const parallaxImg = document.querySelector(".corner-media img");
  if (parallaxImg && !reduced) {
    const pio = new IntersectionObserver((entries) => {
      for (const e of entries) parallaxImg.dataset.vis = e.isIntersecting ? "1" : "";
    });
    pio.observe(parallaxImg);
    addEventListener("scroll", () => {
      if (!parallaxImg.dataset.vis) return;
      const r = parallaxImg.getBoundingClientRect();
      const mid = (r.top + r.height / 2 - innerHeight / 2) / innerHeight;
      parallaxImg.style.transform =
        `translate3d(0, ${(-mid * 34).toFixed(2)}px, 0) scale(1.09)`;
    }, { passive: true });
  }

  /* ── pointer parallax on hero copy ── */
  if (!reduced && matchMedia("(pointer: fine)").matches) {
    addEventListener("pointermove", (e) => {
      pointerX = (e.clientX / innerWidth - 0.5) * 2;
      pointerY = (e.clientY / innerHeight - 0.5) * 2;
    }, { passive: true });
  }

  /* ── go ── */
  resize();
  updateHero(0);
  requestAnimationFrame(tick);

  // safety: never leave the curtain up if the network stalls badly
  setTimeout(openCurtain, 9000);

  load()
    .then((info) => console.info("[BGS CORNER] film ready", info))
    .catch((err) => {
      console.error(err);
      openCurtain();
    });

  // dev hook: lets tooling drive the loop when rAF is throttled
  window.__bgs = {
    info: () => ({
      count, ready, frameW, frameH, ahead, behind,
      pos: +pos.toFixed(2), target: +target.toFixed(2), drawnIdx,
      buffered: blobs.filter(Boolean).length,
      decoded: bitmaps.filter(Boolean).length,
    }),
    step: (t) => step(t),
  };
})();
