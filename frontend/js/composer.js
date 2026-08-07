/* The beat loop — the core mechanic of the whole app. Fetches one short beat/line at a
   time, reveals it character-by-character at reading pace, and fetches the *next* beat
   as soon as the current one's text is known (fetch-ahead) rather than waiting for the
   reveal animation to finish. Because the next fetch reads live dial values right
   before it's sent, moving an organ stop or foot pedal while reading changes the very
   next beat — never a replace of text already shown.

   Deliberately NOT gated on prefers-reduced-motion: the character-paced reveal is
   functional pacing (it's the whole point — "watch it write itself"), not decorative
   flourish. Reduced motion simplifies the ignition transition and ambient effects
   elsewhere, not this. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.composer = (function () {
  // A dial change made while beat N is revealing lands two beats later, not one:
  // beat N+1's fetch already went out (fetch-ahead) reading the OLD dial values the
  // instant N started revealing — before the user's change happened. The earliest
  // beat that can read the new values is N+2. onDialsPending/onDialsApplied below
  // let the UI show that real wait rather than leaving it unexplained.
  const DIALS_APPLY_LAG_BEATS = 2;
  const DEFAULT_BEAT_DURATION_MS = 90 * 48; // seed estimate before any real beat has completed

  function getCharIntervalMs() {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--pace-char-ms");
    const n = parseFloat(raw);
    return Number.isFinite(n) && n > 0 ? n : 48;
  }

  function joinBeat(existing, beat) {
    if (!existing) return beat;
    if (!beat) return existing; // a silent sentinel-only conclusion carries no new text
    const needsSpace = !/\s$/.test(existing) && !/^\s/.test(beat);
    return existing + (needsSpace ? " " : "") + beat;
  }

  function now() {
    return (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
  }

  /**
   * @param {object} opts
   * @param {object} opts.setup - locked setup fields (engine, api_key, temperature,
   *   category, theme_setting, style_voice, ending, target_words, custom_elements,
   *   characters, pov, tense, setting_era, audience, structure, user_name, agency_name)
   * @param {() => object} opts.getDials - returns current {tension, surprise, humour,
   *   pathos, mystery, passion, intensity}, read fresh on every request
   * @param {(fullText: string) => void} opts.onTextGrow
   * @param {(wordCount: number) => void} opts.onWordCount
   * @param {(fullText: string) => void} opts.onConcluded
   * @param {(err: Error) => void} opts.onError
   * @param {(estimatedMs: number) => void} [opts.onDialsPending] - a dial moved; this
   *   is the real estimated wait until a beat reflecting it starts revealing
   * @param {() => void} [opts.onDialsApplied] - that beat has now started
   */
  const PAUSE_POLL_MS = 150;

  function createController(opts) {
    const charIntervalMs = getCharIntervalMs();
    let cancelled = false;
    let paused = false;
    let pauseStartedAt = 0;
    let storyText = "";

    // Beat/generation tracking, purely for the dial-change ETA estimate above --
    // unrelated to the actual generation logic, which doesn't need any of this.
    let generation = 0;
    let currentBeatCharsTotal = 0;
    let currentBeatCharsShown = 0;
    let currentBeatStartedAt = 0;
    let lastBeatDurationMs = DEFAULT_BEAT_DURATION_MS;
    let pendingTargetGeneration = null;

    function fetchBeat(storySoFar) {
      const dials = opts.getDials();
      const payload = Object.assign({}, opts.setup, dials, { story_so_far: storySoFar });
      return Grammatizer.api.generateBeat(payload);
    }

    function beginBeatReveal(charCount) {
      generation += 1;
      currentBeatCharsTotal = charCount;
      currentBeatCharsShown = 0;
      currentBeatStartedAt = now();
      if (pendingTargetGeneration !== null && generation >= pendingTargetGeneration) {
        pendingTargetGeneration = null;
        if (opts.onDialsApplied) opts.onDialsApplied();
      }
    }

    function finishBeatReveal() {
      const elapsed = now() - currentBeatStartedAt;
      if (elapsed > 0) lastBeatDurationMs = elapsed;
    }

    function notifyDialsChanged() {
      if (generation === 0) return; // nothing revealing yet — no ETA to show
      pendingTargetGeneration = generation + DIALS_APPLY_LAG_BEATS;
      const remainingCurrentBeatMs = Math.max(
        0, (currentBeatCharsTotal - currentBeatCharsShown) * charIntervalMs
      );
      // One more full beat (whichever is already in flight) stands between here and
      // the beat that reflects the change; lastBeatDurationMs is our best estimate
      // of its length, since we won't know its real length until it arrives.
      const estimatedMs = remainingCurrentBeatMs + lastBeatDurationMs;
      if (opts.onDialsPending) opts.onDialsPending(estimatedMs);
    }

    function revealBeat(fromText, toText) {
      beginBeatReveal(toText.length - fromText.length);
      return new Promise((resolve) => {
        let i = fromText.length;
        function tick() {
          if (cancelled) { resolve(); return; }
          if (paused) { setTimeout(tick, PAUSE_POLL_MS); return; }
          if (i >= toText.length) {
            storyText = toText;
            finishBeatReveal();
            resolve();
            return;
          }
          i += 1;
          currentBeatCharsShown = i - fromText.length;
          opts.onTextGrow(toText.slice(0, i));
          setTimeout(tick, charIntervalMs);
        }
        tick();
      });
    }

    // Pause freezes the reveal in place (the fetch-ahead already in flight, if any,
    // is left to finish quietly in the background rather than cancelled -- harmless,
    // and means the next beat is ready the instant the reader resumes). The dial-ETA
    // clock is paused too: currentBeatStartedAt is nudged forward by however long the
    // pause lasted, so lastBeatDurationMs still reflects actual writing time, not
    // writing time plus however long the reader stepped away.
    function pause() {
      if (paused || cancelled) return;
      paused = true;
      pauseStartedAt = now();
    }

    function resume() {
      if (!paused) return;
      paused = false;
      currentBeatStartedAt += now() - pauseStartedAt;
    }

    async function loop() {
      try {
        let pendingFetch = fetchBeat(storyText);
        while (!cancelled) {
          const result = await pendingFetch;
          if (cancelled) return;

          const joined = joinBeat(storyText, result.beat);
          const concluded = result.concluded;

          if (!concluded) {
            pendingFetch = fetchBeat(joined);
            pendingFetch.catch(() => {}); // avoid a transient unhandled-rejection warning; real handling is at the next await
          }

          await revealBeat(storyText, joined);
          opts.onWordCount(result.word_count);

          if (concluded) {
            opts.onConcluded(storyText);
            return;
          }
        }
      } catch (err) {
        if (!cancelled) opts.onError(err);
      }
    }

    return {
      start() { loop(); },
      cancel() { cancelled = true; },
      pause,
      resume,
      isPaused() { return paused; },
      getStoryText() { return storyText; },
      notifyDialsChanged,
    };
  }

  return { createController };
})();
