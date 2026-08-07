/* Shared state: localStorage (profile — no secrets) + sessionStorage (API key only,
   deliberately not persisted across browser restarts) + the reduced-motion flag every
   other module branches on. Plain global namespace, no build step. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.state = (function () {
  const PROFILE_KEY = "grammatizer:profile";
  const API_KEY_KEY = "grammatizer:apiKey";

  let prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", (e) => {
    prefersReducedMotion = e.matches;
  });

  function loadProfile() {
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveProfile(partial) {
    const current = loadProfile() || {};
    const next = Object.assign({}, current, partial);
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(next));
    } catch (e) {
      /* localStorage unavailable (private mode, quota) — the app still works, it just
         won't remember the operator between visits. */
    }
    return next;
  }

  function clearProfile() {
    try { localStorage.removeItem(PROFILE_KEY); } catch (e) {}
  }

  function getApiKey() {
    try { return sessionStorage.getItem(API_KEY_KEY) || ""; } catch (e) { return ""; }
  }

  function setApiKey(key) {
    try { sessionStorage.setItem(API_KEY_KEY, key); } catch (e) {}
  }

  function clearApiKey() {
    try { sessionStorage.removeItem(API_KEY_KEY); } catch (e) {}
  }

  return {
    loadProfile,
    saveProfile,
    clearProfile,
    getApiKey,
    setApiKey,
    clearApiKey,
    get prefersReducedMotion() { return prefersReducedMotion; },
  };
})();
