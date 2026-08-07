/* Screen 3 — the illustrated console. Setup + auxiliary panels live in an off-canvas
   drawer that slides fully away once composition starts; only the continuous dials
   stay live, steering the next beat in real time; conclusion makes them go inert. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.screenConsole = (function () {
  const ENGINE_MODEL_NAMES = {
    gemini: "gemini-flash-lite-latest",
    groq: "llama-3.3-70b-versatile",
  };

  let els = {};
  let composerController = null;
  let composing = false;
  let lastRun = null; // { setup, storyText, wordCount } — kept for PDF export after conclusion

  // The manuscript paper is its own bounded, internally-scrolling box (not the whole
  // page) -- text fills it naturally like a real sheet of paper, and only once it
  // actually overflows does the box itself start scrolling to keep the write-head
  // (the newest character) in view, like a terminal or teleprompter. Suspends the
  // moment the reader scrolls away on their own, and re-engages on its own if they
  // scroll back down to the bottom themselves, rather than needing a "resume" control.
  let autoScrollEnabled = true;
  const AUTO_SCROLL_THRESHOLD_PX = 24;

  function isNearBottom() {
    const el = els.manuscriptPaper;
    return el.scrollHeight - (el.scrollTop + el.clientHeight) <= AUTO_SCROLL_THRESHOLD_PX;
  }

  function handlePaperScroll() {
    autoScrollEnabled = isNearBottom();
  }

  function followWriteHead() {
    if (!autoScrollEnabled || els.manuscriptWriteHead.hidden) return;
    // Before the content overflows the box this is a no-op (nothing to scroll --
    // text just fills the visible area on its own); once it does overflow, this
    // keeps pinning to the bottom every time a new character lands.
    els.manuscriptPaper.scrollTop = els.manuscriptPaper.scrollHeight;
  }

  function init() {
    els = {
      setupDrawer: document.getElementById("setup-drawer"),
      setupBank: document.getElementById("setup-bank"),
      wordageInput: document.getElementById("field-wordage"),
      wordageOutput: document.getElementById("wordage-output"),
      manuscriptPaper: document.getElementById("manuscript-paper"),
      manuscriptPlaceholder: document.getElementById("manuscript-placeholder"),
      manuscriptLetterhead: document.getElementById("manuscript-letterhead"),
      manuscriptAgency: document.getElementById("manuscript-agency"),
      manuscriptByline: document.getElementById("manuscript-byline"),
      manuscriptTextContent: document.getElementById("manuscript-text-content"),
      manuscriptWriteHead: document.getElementById("manuscript-write-head"),
      manuscriptStatus: document.getElementById("manuscript-status"),
      dialGroupStops: document.querySelector(".dial-group-stops"),
      dialGroupPedals: document.querySelector(".dial-group-pedals"),
      dialLcd: document.getElementById("dial-lcd"),
      dialLcdIdle: document.getElementById("dial-lcd-idle"),
      dialProgress: document.getElementById("dial-progress"),
      dialProgressFill: document.getElementById("dial-progress-fill"),
      pullLeverBtn: document.getElementById("btn-pull-lever"),
      pauseBtn: document.getElementById("btn-pause"),
      stopBtn: document.getElementById("btn-stop"),
      bindArchiveBtn: document.getElementById("btn-bind-archive"),
      switchEngineLink: document.getElementById("switch-engine-link"),
      newManuscriptBtn: document.getElementById("btn-new-manuscript"),
      forgetMeBtn: document.getElementById("btn-forget-me"),
      consoleError: document.getElementById("console-error"),
    };

    randomizeSetupFields();

    els.wordageInput.addEventListener("input", syncWordageOutput);
    els.pullLeverBtn.addEventListener("click", handlePullLever);
    els.pauseBtn.addEventListener("click", handleTogglePause);
    els.stopBtn.addEventListener("click", handleStop);
    els.newManuscriptBtn.addEventListener("click", handleNewManuscript);
    els.switchEngineLink.addEventListener("click", (e) => { e.preventDefault(); handleSwitchEngine(); });
    els.bindArchiveBtn.addEventListener("click", handleBindArchive);
    els.forgetMeBtn.addEventListener("click", handleForgetMe);

    document.querySelectorAll(".panel-dials [data-dial], .panel-dials [data-stop]").forEach((el) => {
      el.addEventListener("input", () => {
        if (composerController && composing) composerController.notifyDialsChanged();
      });
    });

    els.manuscriptPaper.addEventListener("scroll", handlePaperScroll, { passive: true });
  }

  function syncWordageOutput() {
    els.wordageOutput.textContent = els.wordageInput.value;
  }

  // A rough live estimate for the status line only -- onWordCount (from the actual
  // API response) stays the source of truth for lastRun.wordCount, used by Stop/
  // PDF export/etc. This just stops the counter sitting frozen for the several
  // seconds a beat takes to type out, which read as less "live" than the prose
  // actually revealing beside it.
  function countWords(text) {
    const trimmed = text.trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  }

  // A fresh page load gets a different starting combination of pre-selectors every
  // time, rather than always landing on each dropdown's first hardcoded option --
  // the machine looks freshly wound, not stuck on one setting. Only the dropdown
  // pre-selectors (Category, Theme, Style, Ending, Cast, POV, ...); the wordage
  // slider and the free-text custom-elements field are deliberately left alone.
  function randomizeSetupFields() {
    els.setupBank.querySelectorAll("select[data-field]").forEach((select) => {
      select.selectedIndex = Math.floor(Math.random() * select.options.length);
    });
  }

  function collectSetupFields() {
    const data = {};
    els.setupBank.querySelectorAll("[data-field]").forEach((el) => {
      data[el.dataset.field] = el.type === "range" ? Number(el.value) : el.value;
    });
    return data;
  }

  // Foot pedals (data-dial) stay continuous 0-10; organ stops (data-stop) are
  // discrete pulls -- collected as the flat list of engaged technique IDs the
  // backend's ORGAN_STOP_TECHNIQUES registry expects (see prompts.py).
  function collectDials() {
    const data = {};
    document.querySelectorAll(".panel-dials [data-dial]").forEach((el) => {
      data[el.dataset.dial] = Number(el.value);
    });
    data.engaged_stops = Array.from(document.querySelectorAll(".panel-dials [data-stop]:checked"))
      .map((el) => el.dataset.stop);
    return data;
  }

  function lockSetup(locked) {
    els.setupBank.querySelectorAll("[data-field]").forEach((el) => { el.disabled = locked; });
    els.setupDrawer.classList.toggle("is-locked", locked);
  }

  function setDialsInert(inert) {
    els.dialGroupStops.dataset.inert = inert ? "true" : "false";
    els.dialGroupPedals.dataset.inert = inert ? "true" : "false";
    document.querySelectorAll(".panel-dials [data-dial], .panel-dials [data-stop]").forEach((el) => { el.disabled = inert; });
  }

  function clearError() {
    els.consoleError.hidden = true;
    els.consoleError.textContent = "";
  }

  function showError(message) {
    els.consoleError.textContent = message;
    els.consoleError.hidden = false;
  }

  function setStatus(kind, text) {
    els.manuscriptStatus.hidden = false;
    els.manuscriptStatus.textContent = text;
    els.manuscriptStatus.className = "manuscript-status" + (kind ? ` is-${kind}` : "");
  }

  function hideStatus() {
    els.manuscriptStatus.hidden = true;
  }

  // The gap between moving a dial and hearing its effect isn't cosmetic latency --
  // it's structural: the beat about to be revealed, and the one already fetch-ahead
  // in flight, both locked in their dial values before this change happened. The
  // earliest beat that can reflect it is two beats out. This used to animate the
  // bar toward a GUESSED duration, which was wrong (usually short) the moment a
  // fetch was slow or a rate-limit retry kicked in -- the bar would say "done"
  // before the change had actually landed. It now advances in two real steps, each
  // fired by composer.js only once the corresponding beat has genuinely started
  // revealing (see onDialsPending/onDialsHalfway/onDialsApplied there) -- no
  // estimate, no guess, matches the actual event stream.
  const DIALS_STEP_MS = 260;

  function animateDialsFillTo(percent) {
    els.dialProgressFill.style.transition = `width ${DIALS_STEP_MS}ms ease-out`;
    els.dialProgressFill.style.width = `${percent}%`;
  }

  function showDialsPending() {
    els.dialLcdIdle.hidden = true;
    els.dialProgress.hidden = false;
    els.dialProgressFill.style.transition = "none";
    els.dialProgressFill.style.width = "0%";
    void els.dialProgressFill.offsetWidth; // force reflow so the animate-in below actually starts from 0
    animateDialsFillTo(20);
  }

  function advanceDialsHalfway() {
    if (els.dialProgress.hidden) return; // a stray late event after an unrelated reset
    animateDialsFillTo(60);
  }

  function completeDialsPending() {
    if (els.dialProgress.hidden) return;
    animateDialsFillTo(100);
    setTimeout(hideDialsPending, DIALS_STEP_MS);
  }

  // Instant reset -- used whenever composing itself ends or resets for any reason,
  // not just when a dial change resolves normally (see completeDialsPending above
  // for that case, which fills to 100% first as a small "yes, it landed" flourish).
  function hideDialsPending() {
    els.dialProgress.hidden = true;
    els.dialProgressFill.style.transition = "none";
    els.dialProgressFill.style.width = "0%";
    els.dialLcdIdle.hidden = false;
  }

  function resetManuscriptDom() {
    els.manuscriptPlaceholder.hidden = true;
    els.manuscriptLetterhead.hidden = false;
    els.manuscriptTextContent.textContent = "";
    els.manuscriptWriteHead.hidden = false;
    els.manuscriptPaper.scrollTop = 0;
  }

  function renderManuscriptText(text) {
    els.manuscriptTextContent.textContent = text;
    followWriteHead();
  }

  function engageLever() {
    // No spring-back: the lever stays thrown, in sync with the drawer that's
    // carrying it away — it doesn't reset until a fresh manuscript is started.
    els.pullLeverBtn.classList.add("is-engaged");
  }

  function handlePullLever() {
    if (composing) return;
    clearError();

    const profile = Grammatizer.state.loadProfile() || {};
    const apiKey = Grammatizer.state.getApiKey();
    const setup = Object.assign(
      {
        engine: profile.engine || "gemini",
        api_key: apiKey,
        temperature: typeof profile.temperature === "number" ? profile.temperature : 0.9,
        user_name: profile.userName || "",
        agency_name: profile.agencyName || "",
      },
      collectSetupFields()
    );

    startComposing(setup);
  }

  function startComposing(setup) {
    composing = true;
    lastRun = { setup, storyText: "", wordCount: 0 };
    autoScrollEnabled = true; // a fresh manuscript always starts by following

    engageLever();
    lockSetup(true);
    els.pullLeverBtn.hidden = true;
    els.pauseBtn.hidden = false;
    els.pauseBtn.textContent = "Pause";
    els.stopBtn.hidden = false;
    els.bindArchiveBtn.hidden = true;
    els.switchEngineLink.hidden = true;
    els.newManuscriptBtn.hidden = true;
    setDialsInert(false);
    hideDialsPending();
    els.dialLcd.classList.add("is-active"); // the LCD only ticks over while the machine is actually running

    resetManuscriptDom();
    els.manuscriptAgency.textContent = setup.agency_name || "The Great Automatic Grammatizator";
    els.manuscriptByline.textContent = setup.user_name
      ? `Manufactured for ${setup.user_name} — ${new Date().toLocaleDateString()}`
      : `Manufactured automatically — ${new Date().toLocaleDateString()}`;

    setStatus("composing", "The machine is writing... 0 words");

    composerController = Grammatizer.composer.createController({
      setup,
      getDials: collectDials,
      // Tracked continuously (not just at conclusion) so Stop always has the exact
      // text on screen, including a beat that was only partway revealed.
      onTextGrow: (text) => {
        lastRun.storyText = text;
        renderManuscriptText(text);
        if (!composerController.isPaused()) {
          setStatus("composing", `The machine is writing... ${countWords(text)} / ${setup.target_words} words`);
        }
      },
      onWordCount: (n) => {
        lastRun.wordCount = n;
      },
      onConcluded: (fullText) => handleConcluded(fullText),
      onError: (err) => handleComposeError(err),
      onDialsPending: () => showDialsPending(),
      onDialsHalfway: () => advanceDialsHalfway(),
      onDialsApplied: () => completeDialsPending(),
    });
    composerController.start();
  }

  function handleTogglePause() {
    if (!composerController) return;
    if (composerController.isPaused()) {
      composerController.resume();
      els.pauseBtn.textContent = "Pause";
      setStatus("composing", `The machine is writing... ${lastRun.wordCount} / ${lastRun.setup.target_words} words`);
    } else {
      composerController.pause();
      els.pauseBtn.textContent = "Resume";
      setStatus("paused", `Paused — ${lastRun.wordCount} words so far.`);
    }
  }

  function handleStop() {
    if (!composerController) return;
    composerController.cancel();
    composerController = null;
    composing = false;

    els.manuscriptWriteHead.hidden = true;
    setDialsInert(true);
    hideDialsPending();
    els.dialLcd.classList.remove("is-active");
    els.pauseBtn.hidden = true;
    els.stopBtn.hidden = true;
    setStatus("concluded", `Manuscript stopped — ${lastRun.wordCount} words.`);
    els.bindArchiveBtn.hidden = false;
    els.switchEngineLink.hidden = true;
    els.newManuscriptBtn.hidden = false;
  }

  function handleConcluded(fullText) {
    composing = false;
    lastRun.storyText = fullText;
    els.manuscriptWriteHead.hidden = true;
    setDialsInert(true);
    hideDialsPending();
    els.dialLcd.classList.remove("is-active");
    els.pauseBtn.hidden = true;
    els.stopBtn.hidden = true;
    setStatus("concluded", `Manuscript complete — ${lastRun.wordCount} words.`);
    els.bindArchiveBtn.hidden = false;
    els.switchEngineLink.hidden = true;
    els.newManuscriptBtn.hidden = false;
  }

  function handleComposeError(err) {
    composing = false;
    els.manuscriptWriteHead.hidden = true;
    setDialsInert(true);
    hideDialsPending();
    els.dialLcd.classList.remove("is-active");
    els.pauseBtn.hidden = true;
    els.stopBtn.hidden = true;

    if (err && (err.code === "missing_api_key" || err.code === "invalid_api_key")) {
      handleNewManuscript();
      Grammatizer.router.backToConnect(err.message || "The machine rejected that key.");
      return;
    }

    setStatus("jammed", (err && err.message) || "The machine has jammed.");
    els.newManuscriptBtn.hidden = false;
    // This engine specifically is the problem (its own rate limit or an outage) --
    // offer a direct way back to the engine picker, not just a same-engine retry.
    els.switchEngineLink.hidden = !(err && (err.code === "rate_limited" || err.code === "engine_overloaded"));
  }

  function handleSwitchEngine() {
    handleNewManuscript();
    Grammatizer.router.backToConnect();
  }

  function handleNewManuscript() {
    if (composerController) {
      composerController.cancel();
      composerController = null;
    }
    composing = false;
    lastRun = null;

    lockSetup(false);
    setDialsInert(false);
    hideDialsPending();
    els.dialLcd.classList.remove("is-active");
    els.pullLeverBtn.hidden = false;
    els.pullLeverBtn.classList.remove("is-engaged");
    els.pauseBtn.hidden = true;
    els.pauseBtn.textContent = "Pause";
    els.stopBtn.hidden = true;
    els.bindArchiveBtn.hidden = true;
    els.switchEngineLink.hidden = true;
    els.newManuscriptBtn.hidden = true;
    hideStatus();
    clearError();

    els.manuscriptPlaceholder.hidden = false;
    els.manuscriptLetterhead.hidden = true;
    els.manuscriptTextContent.textContent = "";
    els.manuscriptPaper.scrollTop = 0;
  }

  // Strips characters that are unsafe (or just ugly) in a downloaded filename --
  // deliberately permissive rather than trying to enumerate every OS's exact
  // reserved-character set, since this only ever feeds into "<slug>.pdf".
  function slugifyForFilename(text) {
    return text.trim().replace(/[\\/:*?"<>|]/g, "").replace(/\s+/g, "-").slice(0, 60);
  }

  async function handleBindArchive() {
    if (!lastRun || !lastRun.storyText) return;
    clearError();
    const prevLabel = els.bindArchiveBtn.textContent;
    els.bindArchiveBtn.disabled = true;
    els.bindArchiveBtn.textContent = "Binding...";
    try {
      const blob = await Grammatizer.api.exportPdf({
        story: lastRun.storyText,
        user_name: lastRun.setup.user_name,
        agency_name: lastRun.setup.agency_name,
        engine: lastRun.setup.engine,
        model: ENGINE_MODEL_NAMES[lastRun.setup.engine] || lastRun.setup.engine,
        word_count: lastRun.wordCount,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const nameParts = [
        "grammatizator-manuscript",
        slugifyForFilename(lastRun.setup.agency_name || ""),
        slugifyForFilename(lastRun.setup.user_name || ""),
      ].filter(Boolean);
      a.download = `${nameParts.join("-")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      showError((err && err.message) || "The binding press has jammed — try again.");
    } finally {
      els.bindArchiveBtn.disabled = false;
      els.bindArchiveBtn.textContent = prevLabel;
    }
  }

  function handleForgetMe() {
    if (composerController) {
      composerController.cancel();
      composerController = null;
    }
    composing = false;
    Grammatizer.state.clearProfile();
    Grammatizer.state.clearApiKey();
    Grammatizer.router.backToConnect();
  }

  function onShow() {
    syncWordageOutput();
    if (!composing && !lastRun) {
      handleNewManuscript();
    }
  }

  return { init, onShow };
})();
