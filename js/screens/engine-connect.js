/* Screen 1 — pick an engine, paste a key. No client-side key validation call (would
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
    };

    els.connectBtn.addEventListener("click", handleConnect);

    restoreFromProfile();
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

  function showError(message) {
    els.error.textContent = message;
    els.error.hidden = false;
    // With four engines the title page is taller than most windows, and this message
    // sits near the foot of it, beside the key. Someone sent back here from the
    // console (a rejected key, an account with no credit) lands at the top of the
    // page, so bring the reason into view rather than leave it to be found.
    els.error.scrollIntoView({
      block: "nearest",
      behavior: Grammatizer.state.prefersReducedMotion ? "auto" : "smooth",
    });
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

    Grammatizer.router.afterConnect();
  }

  function showInlineError(message) {
    showError(message);
  }

  return { init, showInlineError };
})();
