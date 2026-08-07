/* The 3-screen router. Decides the initial screen from saved state, wires the
   transitions each screen module calls back into, and owns the signature
   ignition→console transition (a genuinely different code path under reduced motion,
   not just a shorter one). */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.router = (function () {
  let screens = {};
  let transitionOverlay = null;

  function init() {
    screens = {
      connect: document.getElementById("screen-connect"),
      ignition: document.getElementById("screen-ignition"),
      console: document.getElementById("screen-console"),
    };
    transitionOverlay = document.getElementById("machine-transition");

    Grammatizer.screenConnect.init();
    Grammatizer.screenIgnition.init();
    Grammatizer.screenConsole.init();

    decideInitialScreen();
  }

  function showOnly(name) {
    Object.keys(screens).forEach((key) => {
      screens[key].hidden = key !== name;
    });
    if (name === "console") Grammatizer.screenConsole.onShow();
  }

  function hasCompleteProfile(profile) {
    return !!(profile && profile.engine && profile.userName && profile.agencyName);
  }

  function decideInitialScreen() {
    const profile = Grammatizer.state.loadProfile();
    const hasKey = !!Grammatizer.state.getApiKey();

    if (hasCompleteProfile(profile) && hasKey) {
      showOnly("console");
      return;
    }
    showOnly("connect");
  }

  // Called by screen-connect after engine + key are saved.
  function afterConnect() {
    const profile = Grammatizer.state.loadProfile();
    if (hasCompleteProfile(profile)) {
      // Returning operator whose session key just expired (browser restart) —
      // no need to replay the boot sequence, per the plan.
      playTransition().then(() => showOnly("console"));
      return;
    }
    showOnly("ignition");
    Grammatizer.screenIgnition.play();
  }

  // Called by ignition-onboarding after name + agency are saved.
  function afterIgnition() {
    playTransition().then(() => showOnly("console"));
  }

  // Called by console (or on a rejected key) to return to screen 1 with an inline
  // error. This used to be a hard instant swap -- no transition at all -- which
  // read as more disruptive than the underlying problem (a bad key, nothing about
  // the manuscript setup is actually lost) warranted. A quick fade softens the
  // jump-cut without touching the ignition->console handoff's own choreographed
  // transition elsewhere in this file.
  function backToConnect(message) {
    showOnly("connect");
    if (!Grammatizer.state.prefersReducedMotion) {
      screens.connect.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 220, easing: "ease-out" });
    }
    if (message) Grammatizer.screenConnect.showInlineError(message);
  }

  function playTransition() {
    return new Promise((resolve) => {
      transitionOverlay.style.opacity = "1";
      transitionOverlay.style.pointerEvents = "none";

      if (Grammatizer.state.prefersReducedMotion) {
        const anim = transitionOverlay.animate(
          [{ opacity: 1 }, { opacity: 0 }],
          { duration: 150, easing: "linear", fill: "forwards" }
        );
        anim.onfinish = finish;
        return;
      }

      transitionOverlay.style.clipPath = "circle(150% at 50% 18%)";
      const anim = transitionOverlay.animate(
        [
          { clipPath: "circle(150% at 50% 18%)", backgroundColor: "#171512", offset: 0 },
          { clipPath: "circle(150% at 50% 18%)", backgroundColor: "#d98a2b", offset: 0.18 },
          { clipPath: "circle(0% at 50% 18%)", backgroundColor: "#d98a2b", offset: 1 },
        ],
        { duration: 1100, easing: "cubic-bezier(0.65,0,0.35,1)", fill: "forwards" }
      );
      anim.onfinish = finish;

      function finish() {
        transitionOverlay.style.opacity = "0";
        transitionOverlay.style.clipPath = "";
        resolve();
      }
    });
  }

  return { init, afterConnect, afterIgnition, backToConnect };
})();

document.addEventListener("DOMContentLoaded", Grammatizer.router.init);
