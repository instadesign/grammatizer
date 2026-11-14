/* The drawn machine: everything that makes the artwork respond.

   console.js still owns what the app DOES (composing, pausing, errors); this module
   only shows it. It dresses the plain form controls in their drawn parts, and turns
   the machine's state into motion and sound:

     setState("idle" | "composing" | "paused" | "concluded" | "jammed")

   sets data-machine-state on the stage, which css/animations.css keys everything off.
   Nothing here decides anything; if this file failed to load the app would still
   work, just with a still picture. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.machine = (function () {
  // Where the artwork lives. Empty when the app is served from its own folder; set by
  // the page (before this script) when it is embedded somewhere the relative path would
  // not resolve, as on the WordPress site (see tools/embed_wordpress.py).
  const ASSET_BASE = window.GRAMMATIZER_ASSET_BASE || "";
  const PARTS = `${ASSET_BASE}assets/svg/parts/`;
  const FLAG_TEXT = {
    idle: "At rest",
    composing: "Writing",
    paused: "Paused",
    concluded: "Finis",
    jammed: "Jammed",
  };
  const SPIN_DOWN_MS = 2200;

  let els = {};
  let state = "idle";
  let spinToken = 0;
  let typedCount = 0;

  function reducedMotion() {
    return Grammatizer.state.prefersReducedMotion;
  }

  function img(name, className) {
    const el = document.createElement("img");
    el.src = `${PARTS}${name}.svg`;
    el.alt = "";
    if (className) el.className = className;
    return el;
  }

  function init() {
    els = {
      stage: document.getElementById("stage"),
      safe: document.querySelector("#stage .safe"),
      flagText: document.getElementById("flag-text"),
      odoCount: document.getElementById("odo-count"),
      odoTarget: document.getElementById("odo-target"),
      sight: document.getElementById("dial-lcd"),
      puffs: document.getElementById("puffs"),
      bell: document.getElementById("bell"),
      writeHead: document.getElementById("manuscript-write-head"),
      soundBtn: document.getElementById("btn-sound"),
      crank: document.querySelector("#btn-scramble img"),
      cardName: document.getElementById("op-card-name"),
      cardAgency: document.getElementById("op-card-agency"),
      shutterHost: document.getElementById("setup-drawer"),
    };

    buildDrums();
    buildStops();
    bindPedals();
    bindSound();
    watchShutter();
  }

  /* ---- pre-selector drums -------------------------------------------------------- */

  // The <select> is the card you read through the drum's window. This wraps it in the
  // clipping window and adds the thumbwheel; the list itself stays the native one, so
  // keyboard and screen-reader behaviour are the browser's own.
  function buildDrums() {
    document.querySelectorAll(".drum").forEach((drum) => {
      const select = drum.querySelector("select");
      const windowEl = document.createElement("span");
      windowEl.className = "drum-window";
      drum.insertBefore(windowEl, select);
      windowEl.appendChild(select);

      const wheel = document.createElement("button");
      wheel.type = "button";
      wheel.className = "drum-wheel";
      wheel.tabIndex = -1; // the select itself is the keyboard control
      wheel.setAttribute("aria-hidden", "true");
      wheel.appendChild(img("thumbwheel"));
      drum.appendChild(wheel);

      wheel.addEventListener("click", (event) => {
        const box = wheel.getBoundingClientRect();
        step(select, event.clientY < box.top + box.height / 2 ? -1 : 1);
      });
      drum.addEventListener("wheel", (event) => {
        if (select.disabled) return;
        event.preventDefault();
        step(select, event.deltaY > 0 ? 1 : -1);
      }, { passive: false });
      select.addEventListener("change", (event) => {
        if (event.isTrusted) roll(select, 1);
      });
    });
  }

  function step(select, direction) {
    if (select.disabled) return;
    const count = select.options.length;
    select.selectedIndex = (select.selectedIndex + direction + count) % count;
    select.dispatchEvent(new Event("input", { bubbles: true }));
    select.dispatchEvent(new Event("change", { bubbles: true }));
    roll(select, direction);
  }

  function roll(select, direction) {
    Grammatizer.sound.tick();
    if (reducedMotion()) return;
    select.animate(
      [{ transform: `translateY(${direction > 0 ? 105 : -105}%)` }, { transform: "translateY(0)" }],
      { duration: 240, easing: "cubic-bezier(0.3, 1.4, 0.6, 1)" }
    );
  }

  // All ten drums spin and settle one after another, like a fruit machine. Purely a
  // flourish over values console.js has already chosen.
  function spinDrums() {
    if (els.crank && !reducedMotion()) {
      els.crank.animate([{ rotate: "0deg" }, { rotate: "720deg" }], { duration: 900, easing: "cubic-bezier(0.3, 0, 0.2, 1)" });
    }
    if (reducedMotion()) return;
    document.querySelectorAll(".drum select").forEach((select, i) => {
      const spins = 3 + i;
      const anim = select.animate(
        [{ transform: "translateY(110%)" }, { transform: "translateY(-110%)" }],
        { duration: 95, iterations: spins }
      );
      anim.onfinish = () => roll(select, 1);
    });
  }

  /* ---- organ stops ----------------------------------------------------------------- */

  function buildStops() {
    document.querySelectorAll(".stop-toggle").forEach((stop) => {
      const art = stop.querySelector(".stop-toggle-knob");
      art.append(
        img("stop-seat", "stop-seat"),
        img("stop-shadow", "stop-shadow"),
        img("stop-shaft", "stop-shaft"),
        img("stop-knob", "stop-knob"),
        img("jewel", "stop-jewel"),
        img("jewel-glow", "stop-glow")
      );
      const input = stop.querySelector("input");
      input.addEventListener("change", () => Grammatizer.sound.knock(input.checked));
    });
  }

  /* ---- pedals ------------------------------------------------------------------------ */

  function bindPedals() {
    document.querySelectorAll(".pedal").forEach((pedal) => {
      const input = pedal.querySelector("input");
      const sync = () => pedal.style.setProperty("--v", String(Number(input.value) / Number(input.max || 10)));
      input.addEventListener("input", sync);
      sync();
    });
  }

  /* ---- sound ------------------------------------------------------------------------- */

  function bindSound() {
    const paint = () => els.soundBtn.setAttribute("aria-pressed", String(Grammatizer.sound.isEnabled()));
    els.soundBtn.addEventListener("click", () => {
      Grammatizer.sound.setEnabled(!Grammatizer.sound.isEnabled());
      paint();
      if (Grammatizer.sound.isEnabled()) {
        Grammatizer.sound.knock(true);
        Grammatizer.sound.setRunning(state === "composing");
      } else {
        Grammatizer.sound.setRunning(false);
      }
    });
    paint();
  }

  // The shutter is moved by console.js toggling a class; this only gives it its rattle.
  function watchShutter() {
    let wasLocked = els.shutterHost.classList.contains("is-locked");
    new MutationObserver(() => {
      const locked = els.shutterHost.classList.contains("is-locked");
      if (locked !== wasLocked) {
        wasLocked = locked;
        Grammatizer.sound.rattle();
      }
    }).observe(els.shutterHost, { attributes: true, attributeFilter: ["class"] });
  }

  /* ---- machine state ----------------------------------------------------------------- */

  function turningAnimations() {
    const list = [];
    els.stage.querySelectorAll(".turns, .runs").forEach((el) => {
      el.getAnimations().forEach((anim) => list.push(anim));
    });
    return list;
  }

  function setRate(rate) {
    turningAnimations().forEach((anim) => { anim.playbackRate = rate; });
  }

  // Coming to rest: everything that turns slows to a stop over a couple of seconds,
  // rather than freezing mid-turn as if the picture had been paused.
  function spinDown() {
    const token = ++spinToken;
    if (reducedMotion()) {
      els.stage.classList.remove("is-running");
      return;
    }
    const started = performance.now();
    function frame(now) {
      if (token !== spinToken) return; // the machine was started again meanwhile
      const t = Math.min(1, (now - started) / SPIN_DOWN_MS);
      setRate(Math.pow(1 - t, 1.6));
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        els.stage.classList.remove("is-running");
        setRate(1);
      }
    }
    requestAnimationFrame(frame);
  }

  function setState(next) {
    if (!FLAG_TEXT[next]) return;
    const previous = state;
    state = next;
    els.stage.dataset.machineState = next;
    els.flagText.textContent = FLAG_TEXT[next];

    if (next === "composing") {
      spinToken += 1; // cancels a spin-down still in progress
      setRate(1);
      els.stage.classList.add("is-running");
      Grammatizer.sound.setRunning(true);
    } else if (next === "paused") {
      Grammatizer.sound.setRunning(false);
    } else if (next === "concluded") {
      Grammatizer.sound.setRunning(false);
      spinDown();
      if (previous === "composing" || previous === "paused") ringBell();
    } else if (next === "jammed") {
      Grammatizer.sound.setRunning(false);
      spinDown();
      shudder();
      Grammatizer.sound.jam();
    } else {
      Grammatizer.sound.setRunning(false);
      spinToken += 1;
      els.stage.classList.remove("is-running", "is-waiting");
      setRate(1);
    }
    if (next !== "composing") els.stage.classList.remove("is-waiting");
  }

  function setWords(count, target) {
    els.odoCount.textContent = String(Math.max(0, count | 0)).padStart(4, "0");
    if (target != null) els.odoTarget.textContent = String(target);
  }

  // percent: 0-100, how far the change to the dials has got (see console.js).
  function setRecalibration(percent) {
    els.sight.style.setProperty("--fill", String(percent));
  }

  // A request for the next passage is out (true) or has come back (false).
  function setWaiting(waiting, arrived) {
    els.stage.classList.toggle("is-waiting", !!waiting && state === "composing");
    if (!waiting && arrived && state === "composing") puff();
  }

  // One character has just been typed.
  function typed(character) {
    Grammatizer.sound.clack(character === " " || character === "\n");
    typedCount += 1;
    if (reducedMotion() || typedCount % 2) return;
    els.writeHead.animate(
      [{ transform: "translateY(-3px) rotate(-8deg)" }, { transform: "translateY(0) rotate(0)" }],
      { duration: 70, easing: "ease-out" }
    );
  }

  /* ---- one-off flourishes ------------------------------------------------------------ */

  function puff() {
    Grammatizer.sound.hiss();
    if (reducedMotion()) return;
    const cloud = img("puff");
    els.puffs.appendChild(cloud);
    const drift = -18 - Math.random() * 26;
    const anim = cloud.animate(
      [
        { transform: "translate(0, 8px) scale(0.3)", opacity: 0 },
        { transform: `translate(${drift * 0.3}px, -22px) scale(0.8)`, opacity: 0.95, offset: 0.25 },
        { transform: `translate(${drift}px, -96px) scale(1.45)`, opacity: 0 },
      ],
      { duration: 1700, easing: "cubic-bezier(0.2, 0.6, 0.4, 1)" }
    );
    anim.onfinish = () => cloud.remove();
  }

  function ringBell() {
    Grammatizer.sound.bell();
    if (reducedMotion()) return;
    els.bell.animate(
      [
        { rotate: "0deg" }, { rotate: "24deg" }, { rotate: "-19deg" }, { rotate: "14deg" },
        { rotate: "-9deg" }, { rotate: "5deg" }, { rotate: "-2deg" }, { rotate: "0deg" },
      ],
      { duration: 1500, easing: "ease-out" }
    );
  }

  function shudder() {
    if (reducedMotion()) return;
    els.safe.animate(
      [
        { translate: "0 0" }, { translate: "-3px 1px" }, { translate: "3px -1px" }, { translate: "-2px 2px" },
        { translate: "2px 0" }, { translate: "-1px -1px" }, { translate: "0 0" },
      ],
      { duration: 460, easing: "linear" }
    );
  }

  function leverPulled() {
    Grammatizer.sound.unlock();
    Grammatizer.sound.lever();
  }

  function refreshCard() {
    const profile = Grammatizer.state.loadProfile() || {};
    els.cardName.textContent = profile.userName || "unknown";
    els.cardAgency.textContent = profile.agencyName || "none given";
  }

  return {
    init, setState, setWords, setRecalibration, setWaiting, typed,
    spinDrums, leverPulled, refreshCard,
  };
})();
