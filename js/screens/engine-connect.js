/* Screen 1 — pick an engine, paste a key. Choosing an engine (a click on its card, or
   Enter/Space on it from the keyboard) opens a dialog over the page with that engine's
   key link, the key field and Connect: with four engines the cards fill most windows,
   and a key field below them went unseen. No client-side key validation call (would
   double API cost for no real benefit) — proceed optimistically; if the first real
   generation comes back 401, the console routes back here with the error shown inline.

   Creativity used to be a user-facing slider; it's now a fixed value (see
   DEFAULT_TEMPERATURE below) -- one fewer decision for a first-time operator to make,
   and 0.9 already covers the sweet spot between coherent and surprising for every
   engine this app supports. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.screenConnect = (function () {
  const DEFAULT_TEMPERATURE = 0.9;

  let els = {};

  function init() {
    els = {
      root: document.getElementById("screen-connect"),
      apiKeyInput: document.getElementById("api-key-input"),
      error: document.getElementById("connect-error"),
      connectBtn: document.getElementById("btn-connect"),
      dialog: document.getElementById("key-dialog"),
      dialogArt: document.getElementById("key-dialog-art"),
      dialogTitle: document.getElementById("key-dialog-title"),
      dialogTag: document.getElementById("key-dialog-tag"),
      dialogLink: document.getElementById("key-dialog-link"),
    };

    els.connectBtn.addEventListener("click", handleConnect);
    // Enter in the key field connects. (Left to the form, it would "submit" through its
    // first button, which is the close button.)
    els.apiKeyInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleConnect();
      }
    });
    bindCards();
    // A message is about the attempt that just failed: it goes when the dialog does.
    els.dialog.addEventListener("close", clearError);
    // A click on the dimmed page outside the dialog closes it, as Esc does.
    els.dialog.addEventListener("click", (event) => {
      if (event.target === els.dialog) els.dialog.close("cancel");
    });
    ["pointerenter", "focus"].forEach((type) => els.connectBtn.addEventListener(type, () => stirCogs(true)));
    ["pointerleave", "blur"].forEach((type) => els.connectBtn.addEventListener(type, () => stirCogs(false)));

    restoreFromProfile();
    els.root.querySelectorAll('input[name="engine"]').forEach((radio) => radio.addEventListener("change", paceEngines));
    paceEngines();
  }

  /* ---- the key dialog ------------------------------------------------------------- */

  function bindCards() {
    els.root.querySelectorAll(".engine-card").forEach((card) => {
      const radio = card.querySelector("input");
      // A click or tap anywhere on the card. Arrow keys moving between the radios fire
      // clicks too, but only on the radio itself, so those are left alone: arrowing
      // through the engines just chooses, and Enter or Space opens.
      card.addEventListener("click", (event) => {
        if (event.target === radio || event.target.closest("a")) return;
        // The label checks the radio after this click event; make sure it's chosen first.
        radio.checked = true;
        radio.dispatchEvent(new Event("change", { bubbles: true }));
        openKeyDialog();
      });
      radio.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          radio.checked = true;
          radio.dispatchEvent(new Event("change", { bubbles: true }));
          openKeyDialog();
        }
      });
    });
  }

  function openKeyDialog() {
    const card = els.root.querySelector(".engine-card:has(input:checked)") ||
      els.root.querySelector(".engine-card");
    const link = card.querySelector(".engine-card-link");
    els.dialogTitle.textContent = card.querySelector(".engine-card-name").textContent;
    els.dialogTag.textContent = card.querySelector(".engine-card-tag").textContent;
    els.dialogLink.href = link.href;
    els.dialogLink.textContent = link.textContent;
    els.dialogArt.src = `${window.GRAMMATIZER_ASSET_BASE || ""}assets/svg/parts/engine-${card.dataset.engineCard}.svg`;
    if (!els.dialog.open) els.dialog.showModal();
    els.apiKeyInput.focus();
  }

  // All four engines tick over on their cards; the one that is chosen goes at it
  // properly, and the others ease off. (The drawings move themselves: see js/art.js.)
  function paceEngines() {
    els.root.querySelectorAll(".engine-card").forEach((card) => {
      Grammatizer.art.setPace(card, card.querySelector("input").checked ? 1.35 : 0.6);
    });
  }

  // The two cogs behind the corners of the title page turn slowly by themselves
  // (css/animations.css). With the pointer or the focus on the button they pick up:
  // the machine can tell it is about to be started. A playback rate, not a new
  // duration, so they gather speed from where they are instead of jumping. With
  // "reduce motion" on there are no animations here to find, and this does nothing.
  function stirCogs(eager) {
    els.root.querySelectorAll(".frontispiece-cog").forEach((cog) => {
      cog.getAnimations().forEach((anim) => anim.updatePlaybackRate(eager ? 8 : 1));
    });
  }

  function selectedEngine() {
    return els.root.querySelector('input[name="engine"]:checked').value;
  }

  function restoreFromProfile() {
    const profile = Grammatizer.state.loadProfile();
    if (!profile) return;
    if (profile.engine) {
      const radio = els.root.querySelector(`input[name="engine"][value="${profile.engine}"]`);
      if (radio) radio.checked = true;
    }
  }

  // The message goes in the key dialog, beside the key, which is opened for it if it is
  // not open already: someone sent back here from the console (a rejected key, an
  // account with no credit) sees the reason and the field to fix it in one place.
  function showError(message) {
    els.error.textContent = message;
    els.error.hidden = false;
    openKeyDialog();
  }

  function clearError() {
    els.error.hidden = true;
    els.error.textContent = "";
  }

  function handleConnect() {
    clearError();
    const engine = selectedEngine();
    const apiKey = els.apiKeyInput.value.trim();

    if (!apiKey) {
      showError("Paste an API key to connect the machine.");
      return;
    }

    Grammatizer.state.saveProfile({ engine, temperature: DEFAULT_TEMPERATURE });
    Grammatizer.state.setApiKey(apiKey);
    // A modal dialog sits above everything, whichever screen is showing: close it first.
    els.dialog.close("connected");

    Grammatizer.router.afterConnect();
  }

  function showInlineError(message) {
    showError(message);
  }

  return { init, showInlineError };
})();
