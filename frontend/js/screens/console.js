/* Screen 3 — the illustrated console. Setup + auxiliary panels live in an off-canvas
   drawer that slides fully away once composition starts; only the continuous dials
   stay live, steering the next beat in real time; conclusion makes them go inert. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.screenConsole = (function () {
  const ENGINE_MODEL_NAMES = {
    gemini: "gemini-flash-lite-latest",
    groq: "llama-3.3-70b-versatile",
    claude: "claude-haiku-4-5",
  };

  let els = {};
  let composerController = null;
  let composing = false;
  let lastRun = null; // { setup, storyText, wordCount } — kept for PDF export after conclusion

  // Follows the write-head as the manuscript grows, like a terminal or chat log --
  // but only while the reader hasn't deliberately scrolled away. Re-engages on its
  // own if they scroll back down, rather than needing an explicit "resume" control.
  let autoScrollEnabled = true;
  const AUTO_SCROLL_THRESHOLD_PX = 96;

  function isNearBottom() {
    const doc = document.documentElement;
    return doc.scrollHeight - (window.scrollY + window.innerHeight) <= AUTO_SCROLL_THRESHOLD_PX;
  }

  function handleWindowScroll() {
    autoScrollEnabled = isNearBottom();
  }

  function followWriteHead() {
    if (!autoScrollEnabled || els.manuscriptWriteHead.hidden) return;
    const rect = els.manuscriptWriteHead.getBoundingClientRect();
    if (rect.bottom > window.innerHeight || rect.top < 0) {
      els.manuscriptWriteHead.scrollIntoView({ block: "end", behavior: "auto" });
    }
  }

  function init() {
    els = {
      setupDrawer: document.getElementById("setup-drawer"),
      setupBank: document.getElementById("setup-bank"),
      wordageInput: document.getElementById("field-wordage"),
      wordageOutput: document.getElementById("wordage-output"),
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

    window.addEventListener("scroll", handleWindowScroll, { passive: true });
  }

  function syncWordageOutput() {
    els.wordageOutput.textContent = els.wordageInput.value;
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
  // earliest beat that can reflect it is two beats out. Rather than hide that, show
  // it: a small gauge that fills over composer.js's own real estimate of the wait.
  function showDialsPending(estimatedMs) {
    els.dialLcdIdle.hidden = true;
    els.dialProgress.hidden = false;
    els.dialProgressFill.style.transition = "none";
    els.dialProgressFill.style.width = "0%";
    void els.dialProgressFill.offsetWidth; // force reflow so the fill transition below actually starts from 0
    els.dialProgressFill.style.transition = `width ${Math.max(estimatedMs, 200)}ms linear`;
    els.dialProgressFill.style.width = "100%";
  }

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
      },
      onWordCount: (n) => {
        lastRun.wordCount = n;
        if (!composerController.isPaused()) {
          setStatus("composing", `The machine is writing... ${n} / ${setup.target_words} words`);
        }
      },
      onConcluded: (fullText) => handleConcluded(fullText),
      onError: (err) => handleComposeError(err),
      onDialsPending: (ms) => showDialsPending(ms),
      onDialsApplied: () => hideDialsPending(),
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
      a.download = "grammatizator-manuscript.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      showError((err && err.message) || "Could not bind the manuscript.");
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
