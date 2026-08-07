/* Screen 1 — pick an engine, paste a key, set creativity. No client-side key
   validation call (would double API cost for no real benefit) — proceed optimistically;
   if the first real generation comes back 401, the console routes back here with the
   error shown inline. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.screenConnect = (function () {
  let els = {};

  function init() {
    els = {
      root: document.getElementById("screen-connect"),
      apiKeyField: document.getElementById("api-key-field"),
      apiKeyInput: document.getElementById("api-key-input"),
      claudeKeyNote: document.getElementById("claude-key-note"),
      creativityInput: document.getElementById("creativity-input"),
      creativityOutput: document.getElementById("creativity-output"),
      error: document.getElementById("connect-error"),
      connectBtn: document.getElementById("btn-connect"),
    };

    els.creativityInput.addEventListener("input", () => {
      els.creativityOutput.textContent = els.creativityInput.value;
    });

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
    if (typeof profile.temperature === "number") {
      els.creativityInput.value = String(profile.temperature);
      els.creativityOutput.textContent = String(profile.temperature);
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
    const temperature = parseFloat(els.creativityInput.value);

    if (engine !== "claude" && !apiKey) {
      showError("Paste an API key, or switch to the keyless Claude backup engine.");
      return;
    }

    Grammatizer.state.saveProfile({ engine, temperature });
    Grammatizer.state.setApiKey(apiKey);

    Grammatizer.router.afterConnect();
  }

  function showInlineError(message) {
    showError(message);
  }

  return { init, showInlineError };
})();
