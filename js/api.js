/* Thin fetch wrapper for the backend. In production, Nginx proxies /api/* to uvicorn on
   the same origin (see deploy/nginx/grammatizer.conf) — no CORS involved. In local dev,
   frontend and backend run as two separate static/uvicorn processes on different ports,
   so we point at localhost:8000 explicitly when we detect that dev setup. Override with
   window.GRAMMATIZER_API_BASE set before this script runs, if your dev setup differs. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.api = (function () {
  // 127.0.0.1, not "localhost" -- uvicorn's default bind is IPv4-only, but "localhost"
  // resolves to the IPv6 loopback (::1) first on most systems. When a browser's
  // IPv6-to-IPv4 fallback doesn't kick in cleanly, that mismatch alone produces a
  // connection-refused fetch failure (surfaced below as "The machine isn't answering"),
  // even though the backend is up and curl/other tools connect to it just fine.
  const API_BASE =
    window.GRAMMATIZER_API_BASE !== undefined
      ? window.GRAMMATIZER_API_BASE
      : (window.location.port === "5500" || window.location.protocol === "file:")
        ? "http://127.0.0.1:8000"
        : "";

  // The backend retries transient rate-limit hits internally (up to ~20s of waiting),
  // and raw API latency alone has been observed over 20s under real load even with no
  // retry involved -- this needs real headroom, or the frontend aborts a request the
  // backend was about to successfully complete.
  const BEAT_TIMEOUT_MS = 45000;
  const PDF_TIMEOUT_MS = 20000;
  const TITLE_TIMEOUT_MS = 20000;

  class ApiError extends Error {
    constructor(code, message, status) {
      super(message);
      this.name = "ApiError";
      this.code = code;
      this.status = status;
    }
  }

  async function withTimeout(promiseFactory, ms) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ms);
    try {
      return await promiseFactory(controller.signal);
    } catch (err) {
      // A well-formed ApiError (e.g. from parseErrorBody, after a real HTTP response
      // with a structured error) must propagate as-is — only genuine fetch-level
      // failures (network down, DNS, or our own abort) get converted to the generic
      // messages below. Without this check, every structured backend error (missing
      // key, invalid key, rate limit...) was getting masked as "Could not reach the
      // machine," which also silently broke the missing/invalid-key → back-to-connect
      // routing in console.js, since that branches on the real error code.
      if (err instanceof ApiError) throw err;
      if (err.name === "AbortError") {
        throw new ApiError("timeout", "The machine has jammed — no response in time.", 0);
      }
      throw new ApiError("network_error", "The machine isn't answering — check your connection and try again.", 0);
    } finally {
      clearTimeout(timer);
    }
  }

  async function parseErrorBody(response) {
    try {
      const body = await response.json();
      if (body && body.detail && body.detail.code) {
        return new ApiError(body.detail.code, body.detail.message || "The machine refused that.", response.status);
      }
    } catch (e) { /* body wasn't JSON-shaped — fall through */ }
    return new ApiError("engine_error", "The machine refused that.", response.status);
  }

  async function generateBeat(payload) {
    return withTimeout(async (signal) => {
      const response = await fetch(`${API_BASE}/api/generate/beat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal,
      });
      if (!response.ok) throw await parseErrorBody(response);
      return response.json();
    }, BEAT_TIMEOUT_MS);
  }

  async function exportPdf(payload) {
    return withTimeout(async (signal) => {
      const response = await fetch(`${API_BASE}/api/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal,
      });
      if (!response.ok) throw await parseErrorBody(response);
      return response.blob();
    }, PDF_TIMEOUT_MS);
  }

  async function generateTitle(payload) {
    return withTimeout(async (signal) => {
      const response = await fetch(`${API_BASE}/api/generate/title`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal,
      });
      if (!response.ok) throw await parseErrorBody(response);
      return response.json();
    }, TITLE_TIMEOUT_MS);
  }

  /* ---- ?mock=1: a stand-in engine --------------------------------------------------
     For working on the drawing and its animation without a key, a backend or any
     quota: add ?mock=1 to the address and the machine "writes" a short canned story at
     a realistic pace. ?mock=jam fails once, part-way through, to show a jam and its
     recovery. Nothing here is reachable without the query parameter. */
  const MOCK = new URLSearchParams(window.location.search).get("mock");
  const MOCK_BEATS = [
    "The owl arrived on a Tuesday, in a hatbox, ticking. Mrs Pargeter had ordered a barometer. She signed for it anyway, because the delivery boy had already gone and because the hatbox, when she put her ear to it, was humming a hymn.",
    "It was a clockwork owl, about the height of a milk bottle, with eyes like two brass sixpences and a key in its back the size of a teaspoon. \"Wind me,\" it said, \"and I shall tell you what your husband has done with the egg money.\"",
    "She wound it. She was not a woman who left a question lying about the house. The owl whirred, shuffled along the mantelpiece, and looked at the clock with open contempt.",
    "\"Seven turns gets you the truth,\" it said. \"Eight gets you an opinion. I should stop at seven.\" Mrs Pargeter, who had never stopped at seven of anything, gave it nine.",
    "By tea time the owl had audited the pantry, condemned the curtains and found Mr Pargeter's racing slips inside the piano. It was polite about all of it, which was worse.",
    "Mr Pargeter came home at six to find his wife and a small brass bird sitting side by side, waiting, with the slips laid out on the table like a hand of patience. Nobody spoke. The owl ticked.",
    "He paid back the egg money by Michaelmas. The owl stayed on the mantelpiece and was wound once a week, seven turns exactly, by a man who counted them out loud.",
  ];
  // The composer quietly retries a failed beat twice before giving up (see
  // composer.js), so a jam only shows if the stand-in fails three times running.
  let mockFailuresLeft = 3;

  function mockWait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  if (MOCK) {
    const words = (text) => (text.trim() ? text.trim().split(/\s+/).length : 0);
    return {
      ApiError,
      async generateBeat(payload) {
        await mockWait(900 + Math.random() * 700);
        const done = MOCK_BEATS.filter((beat) => payload.story_so_far.includes(beat.slice(0, 40))).length;
        if (MOCK === "jam" && done === 2 && mockFailuresLeft > 0) {
          mockFailuresLeft -= 1;
          throw new ApiError("engine_overloaded", "The engine is overloaded just now — give it a moment, then try again.", 503);
        }
        const beat = MOCK_BEATS[Math.min(done, MOCK_BEATS.length - 1)];
        return {
          beat,
          word_count: words(payload.story_so_far) + words(beat),
          concluded: done >= MOCK_BEATS.length - 1,
        };
      },
      async generateTitle() {
        await mockWait(700);
        return { title: "The Owl Who Kept Accounts" };
      },
      async exportPdf() {
        await mockWait(400);
        throw new ApiError("pdf_render_failed", "The binding press is not connected in mock mode.", 0);
      },
    };
  }

  return { generateBeat, exportPdf, generateTitle, ApiError };
})();
