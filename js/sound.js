/* The machine's noises, synthesised with Web Audio: no audio files to host or load.

   Browsers only allow sound after a click, so nothing plays until unlock() is called
   from one (the first pull of the lever, or switching the ear-trumpet on). On by
   default from then; the ear-trumpet on the machine mutes it, and that choice is kept
   in localStorage, separate from the operator profile, so "Forget me" does not
   switch the noise back on for someone who turned it off. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.sound = (function () {
  const STORAGE_KEY = "grammatizer:sound";
  const MASTER_LEVEL = 0.5;
  const CLACK_MIN_GAP_MS = 30;

  let ctx = null;
  let master = null;
  let noiseBuffer = null;
  let enabled = loadEnabled();
  let lastClackAt = 0;
  let hum = null;

  function loadEnabled() {
    try { return localStorage.getItem(STORAGE_KEY) !== "off"; } catch (e) { return true; }
  }

  function isEnabled() { return enabled; }

  function setEnabled(on) {
    enabled = !!on;
    try { localStorage.setItem(STORAGE_KEY, enabled ? "on" : "off"); } catch (e) {}
    if (master) master.gain.setTargetAtTime(enabled ? MASTER_LEVEL : 0, ctx.currentTime, 0.03);
    if (enabled) unlock();
  }

  function unlock() {
    if (!enabled) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    if (!ctx) {
      ctx = new AudioCtx();
      master = ctx.createGain();
      master.gain.value = MASTER_LEVEL;
      master.connect(ctx.destination);
      noiseBuffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const data = noiseBuffer.getChannelData(0);
      for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
    }
    if (ctx.state === "suspended") ctx.resume();
  }

  function ready() {
    return !!(enabled && ctx && ctx.state === "running");
  }

  /* A burst of filtered noise: the raw material of every click, hiss and clack here. */
  function noise({ at = 0, dur = 0.05, type = "bandpass", freq = 2000, q = 1, gain = 0.2, attack = 0.002 }) {
    const t = ctx.currentTime + at;
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = type;
    filter.frequency.value = freq;
    filter.Q.value = q;
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.0001, t);
    amp.gain.linearRampToValueAtTime(gain, t + attack);
    amp.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(filter).connect(amp).connect(master);
    src.start(t, Math.random() * 0.9);
    src.stop(t + dur + 0.02);
  }

  /* A pitched note that can slide: thumps, knocks, the bell. */
  function tone({ at = 0, dur = 0.1, from = 440, to = null, type = "sine", gain = 0.2, attack = 0.003 }) {
    const t = ctx.currentTime + at;
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(from, t);
    if (to) osc.frequency.exponentialRampToValueAtTime(to, t + dur);
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.0001, t);
    amp.gain.linearRampToValueAtTime(gain, t + attack);
    amp.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    osc.connect(amp).connect(master);
    osc.start(t);
    osc.stop(t + dur + 0.02);
  }

  /* One key striking the page. Called per character, so it limits itself: a fast
     reveal sounds like typing, not like a buzz. Spaces land softer. */
  function clack(soft) {
    if (!ready()) return;
    const now = performance.now();
    if (now - lastClackAt < CLACK_MIN_GAP_MS) return;
    lastClackAt = now;
    const level = soft ? 0.05 : 0.13;
    noise({ dur: 0.022, freq: 1700 + Math.random() * 1500, q: 1.4, gain: level });
    tone({ dur: 0.03, from: 150 + Math.random() * 40, to: 90, gain: level * 0.7 });
  }

  function lever() {
    if (!ready()) return;
    for (let i = 0; i < 6; i += 1) {
      noise({ at: i * 0.034, dur: 0.016, type: "highpass", freq: 2600, gain: 0.16 });
    }
    tone({ at: 0.2, dur: 0.24, from: 110, to: 46, gain: 0.5 });
    noise({ at: 0.2, dur: 0.09, type: "lowpass", freq: 700, gain: 0.3 });
  }

  function knock(out) {
    if (!ready()) return;
    tone({ dur: 0.07, from: out ? 420 : 300, to: out ? 250 : 190, type: "triangle", gain: 0.3 });
    noise({ dur: 0.02, freq: 900, q: 0.8, gain: 0.12 });
  }

  function tick() {
    if (!ready()) return;
    noise({ dur: 0.012, type: "highpass", freq: 3200, gain: 0.1 });
  }

  function rattle() {
    if (!ready()) return;
    for (let i = 0; i < 12; i += 1) {
      noise({ at: i * 0.05, dur: 0.02, freq: 600 + Math.random() * 500, q: 1.2, gain: 0.14 });
    }
    tone({ at: 0.64, dur: 0.12, from: 130, to: 70, gain: 0.34 });
  }

  /* Steam let go: the whistle clears its throat as a passage arrives. */
  function hiss() {
    if (!ready()) return;
    noise({ dur: 0.55, type: "bandpass", freq: 5200, q: 0.6, gain: 0.09, attack: 0.05 });
    tone({ dur: 0.2, from: 1750, to: 1980, gain: 0.025, attack: 0.04 });
  }

  function bell() {
    if (!ready()) return;
    tone({ dur: 1.7, from: 2093, gain: 0.26 });
    tone({ dur: 1.1, from: 3140, gain: 0.1 });
    tone({ dur: 0.5, from: 5274, gain: 0.04 });
    noise({ dur: 0.012, type: "highpass", freq: 4000, gain: 0.12 });
  }

  function jam() {
    if (!ready()) return;
    tone({ dur: 0.28, from: 190, type: "square", gain: 0.16 });
    tone({ dur: 0.22, from: 293, type: "square", gain: 0.1 });
    noise({ dur: 0.1, freq: 1200, q: 0.7, gain: 0.26 });
    tone({ at: 0.18, dur: 0.85, from: 320, to: 55, type: "sawtooth", gain: 0.09, attack: 0.05 });
    noise({ at: 0.2, dur: 0.9, type: "bandpass", freq: 3800, q: 0.5, gain: 0.07, attack: 0.1 });
  }

  /* A quiet chuffing while the machine runs: low noise, pulsed a few times a second. */
  function setRunning(on) {
    if (!ctx) return;
    if (on && !hum && ready()) {
      const src = ctx.createBufferSource();
      src.buffer = noiseBuffer;
      src.loop = true;
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 240;
      const amp = ctx.createGain();
      amp.gain.value = 0;
      const lfo = ctx.createOscillator();
      lfo.frequency.value = 5.5;
      const depth = ctx.createGain();
      depth.gain.value = 0.045;
      lfo.connect(depth).connect(amp.gain);
      src.connect(filter).connect(amp).connect(master);
      amp.gain.setTargetAtTime(0.055, ctx.currentTime, 0.4);
      src.start();
      lfo.start();
      hum = { src, lfo, amp };
    } else if (!on && hum) {
      const h = hum;
      hum = null;
      h.amp.gain.setTargetAtTime(0, ctx.currentTime, 0.35);
      setTimeout(() => { try { h.src.stop(); h.lfo.stop(); } catch (e) {} }, 1600);
    }
  }

  return { unlock, isEnabled, setEnabled, clack, lever, knock, tick, rattle, hiss, bell, jam, setRunning };
})();
