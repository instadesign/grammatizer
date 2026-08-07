/* Thin fetch wrapper for the backend. In production, Nginx proxies /api/* to uvicorn on
   the same origin (see deploy/nginx/grammatizer.conf) — no CORS involved. In local dev,
   frontend and backend run as two separate static/uvicorn processes on different ports,
   so we point at localhost:8000 explicitly when we detect that dev setup. Override with
   window.GRAMMATIZER_API_BASE set before this script runs, if your dev setup differs. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.api = (function () {
  const API_BASE =
    window.GRAMMATIZER_API_BASE !== undefined
      ? window.GRAMMATIZER_API_BASE
      : (window.location.port === "5500" || window.location.protocol === "file:")
        ? "http://localhost:8000"
        : "";

  // The backend retries transient rate-limit hits internally (up to ~20s of waiting),
  // and raw API latency alone has been observed over 20s under real load even with no
  // retry involved -- this needs real headroom, or the frontend aborts a request the
  // backend was about to successfully complete.
  const BEAT_TIMEOUT_MS = 45000;
  const PDF_TIMEOUT_MS = 20000;

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
      throw new ApiError("network_error", "Could not reach the machine.", 0);
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

  return { generateBeat, exportPdf, ApiError };
})();
