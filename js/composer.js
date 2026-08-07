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

  function getCharIntervalMs() {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--pace-char-ms");
    const n = parseFloat(raw);
    return Number.isFinite(n) && n > 0 ? n : 36;
  }

  function joinBeat(existing, beat) {
    if (!existing) return beat;
    if (!beat) return existing; // a silent sentinel-only conclusion carries no new text
    const needsSpace = !/\s$/.test(existing) && !/^\s/.test(beat);
    return existing + (needsSpace ? " " : "") + beat;
  }

  /**
   * @param {object} opts
   * @param {object} opts.setup - locked setup fields (engine, api_key, temperature,
   *   category, theme_setting, style_voice, ending, target_words, custom_elements,
   *   characters, pov, tense, setting_era, audience, structure, user_name, agency_name)
   * @param {() => object} opts.getDials - returns current {passion, intensity,
   *   engaged_stops: string[]}, read fresh on every request
   * @param {(fullText: string) => void} opts.onTextGrow
   * @param {(wordCount: number) => void} opts.onWordCount
   * @param {(fullText: string) => void} opts.onConcluded
   * @param {(err: Error) => void} opts.onError
   * @param {() => void} [opts.onDialsPending] - a dial moved; the wait for it to land
   *   is now two REAL events, not a guessed duration -- see onDialsHalfway/onDialsApplied
   * @param {() => void} [opts.onDialsHalfway] - the one intervening beat (still on the
   *   old values) has actually started revealing -- a genuine progress checkpoint
   * @param {() => void} [opts.onDialsApplied] - the beat reflecting the change has
   *   actually started revealing
   */
  const PAUSE_POLL_MS = 150;

  function createController(opts) {
    const charIntervalMs = getCharIntervalMs();
    let cancelled = false;
    let paused = false;
    let storyText = "";

    // Beat/generation tracking, purely for reporting genuine dial-change progress --
    // unrelated to the actual generation logic, which doesn't need any of this.
    let generation = 0;
    let pendingTargetGeneration = null;

    function fetchBeat(storySoFar) {
      const dials = opts.getDials();
      const payload = Object.assign({}, opts.setup, dials, { story_so_far: storySoFar });
      return Grammatizer.api.generateBeat(payload);
    }

    function beginBeatReveal() {
      generation += 1;
      if (pendingTargetGeneration === null) return;
      if (generation >= pendingTargetGeneration) {
        pendingTargetGeneration = null;
        if (opts.onDialsApplied) opts.onDialsApplied();
      } else if (generation === pendingTargetGeneration - DIALS_APPLY_LAG_BEATS + 1 && opts.onDialsHalfway) {
        // The one beat that stands between "the dial changed" and "the beat that
        // reflects it" has just started revealing -- a real event, not a guess.
        opts.onDialsHalfway();
      }
    }

    function notifyDialsChanged() {
      if (generation === 0) return; // nothing revealing yet — no wait to show
      pendingTargetGeneration = generation + DIALS_APPLY_LAG_BEATS;
      if (opts.onDialsPending) opts.onDialsPending();
    }

    function revealBeat(fromText, toText) {
      beginBeatReveal();
      return new Promise((resolve) => {
        let i = fromText.length;
        function tick() {
          if (cancelled) { resolve(); return; }
          if (paused) { setTimeout(tick, PAUSE_POLL_MS); return; }
          if (i >= toText.length) {
            storyText = toText;
            resolve();
            return;
          }
          i += 1;
          opts.onTextGrow(toText.slice(0, i));
          setTimeout(tick, charIntervalMs);
        }
        tick();
      });
    }

    // Pause freezes the reveal in place (the fetch-ahead already in flight, if any,
    // is left to finish quietly in the background rather than cancelled -- harmless,
    // and means the next beat is ready the instant the reader resumes).
    function pause() {
      if (paused || cancelled) return;
      paused = true;
    }

    function resume() {
      paused = false;
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
