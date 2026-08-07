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
      apiKeyField: document.getElementById("api-key-field"),
      apiKeyInput: document.getElementById("api-key-input"),
      claudeKeyNote: document.getElementById("claude-key-note"),
      error: document.getElementById("connect-error"),
      connectBtn: document.getElementById("btn-connect"),
    };

    els.root.querySelectorAll('input[name="engine"]').forEach((radio) => {
      radio.addEventListener("change", syncApiKeyVisibility);
    });

    els.connectBtn.addEventListener("click", handleConnect);

    restoreFromProfile();
    syncApiKeyVisibility();
  }

  // The Claude backup engine runs on a shared, budget-capped house key -- there's
  // deliberately no BYOK field for it (see engines.py). Everything else is BYOK.
  function selectedEngine() {
    return els.root.querySelector('input[name="engine"]:checked').value;
  }

  function syncApiKeyVisibility() {
    const isKeyless = selectedEngine() === "claude";
    els.apiKeyField.hidden = isKeyless;
    els.claudeKeyNote.hidden = !isKeyless;
    if (isKeyless) els.apiKeyInput.value = "";
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
  }

  function clearError() {
    els.error.hidden = true;
    els.error.textContent = "";
  }

  function handleConnect() {
    clearError();
    const engine = selectedEngine();
    const apiKey = engine === "claude" ? "" : els.apiKeyInput.value.trim();

    if (engine !== "claude" && !apiKey) {
      showError("Paste an API key, or switch to the keyless Claude backup engine.");
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
