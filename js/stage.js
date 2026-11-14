/* Fits the console drawing to the window.

   The console is one fixed 1600 x 900 scene (see css/stage.css), scaled as a whole.
   This sets --stage-scale to the largest scale at which that whole scene is visible.
   Below MIN_SCALE the lettering on the machine stops being readable, so the scale
   holds there and the screen scrolls instead; below TOO_SMALL_W there is no honest way
   to show a desktop-sized illustration at all, and a notice says so. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.stage = (function () {
  const SAFE_W = 1600;
  const SAFE_H = 900;
  const MIN_SCALE = 0.72;
  const TOO_SMALL_W = 760;

  let screen = null;
  let tooSmall = null;
  let centred = false;

  function fit() {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const scale = Math.max(MIN_SCALE, Math.min(vw / SAFE_W, vh / SAFE_H));
    document.documentElement.style.setProperty("--stage-scale", scale.toFixed(4));
    if (tooSmall) tooSmall.hidden = vw >= TOO_SMALL_W;

    // When the scale is being held at its floor the drawing is bigger than the
    // window: start in the middle of it (the paper), not the top-left corner.
    if (screen && !screen.hidden && !centred) {
      screen.scrollLeft = (screen.scrollWidth - screen.clientWidth) / 2;
      screen.scrollTop = 0;
      centred = true;
    }
  }

  function init() {
    screen = document.getElementById("screen-console");
    tooSmall = document.getElementById("too-small");
    window.addEventListener("resize", fit);
    fit();
  }

  return { init, fit };
})();
