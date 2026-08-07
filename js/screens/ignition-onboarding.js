/* Screen 2 — the boot sequence. Only plays for genuinely new profiles; returning
   operators skip straight to the console (decided by the router). */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.screenIgnition = (function () {
  const BOOT_CHAR_MS = 22;
  const BOOT_LINES = [
    "INITIALIZING GRAMMATIZATOR MK. IV...",
    "VALVES WARMING. PRESSURE NOMINAL.",
    "BRASS CONDUITS CLEAR.",
    "WORD-MEMORY BANKS ONLINE.",
    "OPERATOR IDENTIFICATION REQUIRED.",
  ];

  let els = {};

  function init() {
    els = {
      root: document.getElementById("screen-ignition"),
      log: document.getElementById("ignition-log"),
      form: document.getElementById("ignition-form"),
      nameInput: document.getElementById("operator-name-input"),
      agencyInput: document.getElementById("agency-name-input"),
    };

    els.form.addEventListener("submit", handleSubmit);
  }

  function typeLine(text) {
    return new Promise((resolve) => {
      const lineEl = document.createElement("div");
      els.log.appendChild(lineEl);
      let i = 0;
      function tick() {
        if (i >= text.length) {
          resolve();
          return;
        }
        i += 1;
        lineEl.textContent = text.slice(0, i);
        setTimeout(tick, BOOT_CHAR_MS);
      }
      tick();
    });
  }

  async function play() {
    els.log.innerHTML = "";
    els.form.hidden = true;

    for (const line of BOOT_LINES) {
      await typeLine(line);
      els.log.appendChild(document.createTextNode(" "));
    }

    // No lingering cursor left on the log: once the form appears, the focused
    // name field's own (already brass/amber-styled, see ignition.css) caret is
    // the one blinking cursor on screen -- exactly where input is actually needed,
    // instead of a second one stranded on the message above it.
    els.form.hidden = false;
    els.nameInput.focus();
  }

  function handleSubmit(event) {
    event.preventDefault();
    const userName = els.nameInput.value.trim();
    const agencyName = els.agencyInput.value.trim();
    if (!userName || !agencyName) return;

    Grammatizer.state.saveProfile({ userName, agencyName });
    Grammatizer.router.afterIgnition();
  }

  return { init, play };
})();
