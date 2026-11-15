/* Drawings that move.

   Some of the SVG files carry their own animation, written into them by the drawing
   code (tools/draw/): the engines on the title page, the key, and the small lives of
   the console's workshop (the cat, the kettle, the mouse). Shown in a plain <img> they
   animate by themselves, and that is how the page is written and how it stays if this
   file does nothing.

   It is, though, an expensive way to move a picture. Every pen stroke in these
   drawings is a filled outline, so they are slow to paint, and a browser repaints an
   animated image whole on every frame. Measured on the console (Nov 2026, a 120Hz
   screen): the ten workshop pictures alone, as images, kept nearly half a processor
   core busy between the page and the graphics process. Putting the same SVG straight
   into the page was no better (it is still repainted every frame).

   What IS cheap is moving something that has already been painted: the browser keeps
   it as a layer and only slides, turns or fades it. So this module takes each drawing
   apart along the seams the drawing code left in it. Every moving part (a <g> marked
   data-p) becomes an HTML element of its own, holding its share of the picture, and
   the animation written in the file is applied to that element instead: same
   keyframes, same timing, same result on screen, at under a third of the cost.

   Each drawing goes in a shadow tree, which keeps its styles to itself: the files
   reuse plain class names like "head" and "tail" and must not see one another's.

   If a file cannot be fetched (the page opened straight from disk, say) its <img> is
   simply left alone, and animates itself the slow way. */

window.Grammatizer = window.Grammatizer || {};

Grammatizer.art = (function () {
  // Which images to look at. Anything else on the page is a still drawing.
  const SELECTOR = "img.life, img.engine-card-art, img.key-plate-art, img.flourish";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const fetched = new Map();

  function load(url) {
    if (!fetched.has(url)) {
      fetched.set(url, fetch(url).then((response) => {
        if (!response.ok) throw new Error(`art ${response.status}`);
        return response.text();
      }));
    }
    return fetched.get(url);
  }

  function isPart(node) {
    return node.nodeType === 1 && node.hasAttribute("data-p");
  }

  // Shared by every element made here: each one is the full size of the drawing and
  // sits exactly over the others, so nothing has to be measured or positioned.
  const FILL = "position:absolute;left:0;top:0;width:100%;height:100%;";

  // Takes the children of one SVG group and rebuilds them inside `into`, in the same
  // painting order: runs of still artwork as small SVGs, each moving part as a <div>
  // (recursively, since parts nest: an eye in a head on a bird).
  function takeApart(group, into, view, ink) {
    let run = null;
    Array.from(group.childNodes).forEach((node) => {
      if (!isPart(node)) {
        if (node.nodeType !== 1) return;
        if (!run) {
          const layer = document.createElementNS(SVG_NS, "svg");
          layer.setAttribute("viewBox", `${view.x} ${view.y} ${view.width} ${view.height}`);
          layer.style.cssText = `${FILL}display:block;overflow:visible;`;
          run = document.createElementNS(SVG_NS, "g");
          run.setAttribute("fill", ink);
          layer.appendChild(run);
          into.appendChild(layer);
        }
        run.appendChild(node);
        return;
      }

      run = null; // whatever follows this part is painted over it, so starts a new run
      const pivot = node.getAttribute("data-p");
      // A part with a pivot is three nested groups in the file (move the origin to the
      // pivot, the part itself, move it back); here the pivot is just transform-origin.
      const mover = pivot ? node.firstElementChild : node;
      const content = pivot ? mover.firstElementChild : node;
      const part = document.createElement("div");
      part.className = mover.getAttribute("class");
      let origin = "";
      if (pivot) {
        const [px, py] = pivot.split(" ").map(Number);
        origin = `transform-origin:${px - view.x}px ${py - view.y}px;`;
      }
      part.style.cssText = FILL + origin;

      const squash = node.getAttribute("data-s");
      if (squash) {
        // A wheel seen at an angle: it turns as a circle and is flattened afterwards.
        const flat = document.createElement("div");
        flat.style.cssText = `${FILL}${origin}transform:scale(${squash.replace(" ", ",")});`;
        flat.appendChild(part);
        into.appendChild(flat);
      } else {
        into.appendChild(part);
      }
      takeApart(content, part, view, ink);
    });
  }

  function place(img, markup) {
    const holder = document.createElement("div");
    holder.innerHTML = markup;
    const source = holder.querySelector("svg");
    const style = source && source.querySelector("style");
    const body = source && source.querySelector(":scope > g");
    // No <style> means nothing in it moves: leave it as the image it is.
    if (!style || !body) return;

    const view = source.viewBox.baseVal;
    const host = document.createElement("span");
    host.className = `${img.className} art`;
    host.setAttribute("aria-hidden", "true");
    // Where the stylesheet gives the image only a width, its height came from its
    // proportions. The host has none of its own, so it is told them.
    host.style.aspectRatio = `${view.width} / ${view.height}`;

    // Everything is laid out at the drawing's own size (one unit to the pixel, the
    // scale its keyframes are written in) and then scaled, as one, to fit the host.
    const sheet = document.createElement("div");
    sheet.style.cssText = `position:absolute;left:0;top:0;width:${view.width}px;height:${view.height}px;transform-origin:0 0;`;
    takeApart(body, sheet, view, body.getAttribute("fill") || "#2a211b");

    const root = host.attachShadow({ mode: "open" });
    const frame = document.createElement("style");
    frame.textContent = ":host{position:relative}";
    root.append(frame, style, sheet);

    img.replaceWith(host);
    // A pace set on something round the drawing (see setPace) has to be given to each
    // animation as it starts: they start afresh whenever the drawing comes into view,
    // which for a screen that was hidden is long after this.
    root.addEventListener("animationstart", () => {
      const holder = host.closest("[data-art-pace]");
      if (holder) applyPace(host, Number(holder.dataset.artPace));
    });
    // Most are shown at exactly their own size; the key and the flourish are not.
    const fit = () => {
      const scale = host.clientWidth / view.width;
      sheet.style.transform = Math.abs(scale - 1) < 0.002 ? "" : `scale(${scale})`;
    };
    fit();
    if (window.ResizeObserver) new ResizeObserver(fit).observe(host);
  }

  /* ---- pace ------------------------------------------------------------------------ */

  // How briskly a drawing goes about its business: 1 is as written. The title page
  // uses it to perk up whichever engine is chosen. `holder` is anything that contains
  // the drawing (it may still be an <img> when this is called, hence the dataset:
  // place() reads it back once the drawing is in the page).
  function setPace(holder, pace) {
    holder.dataset.artPace = String(pace);
    const host = holder.querySelector(".art");
    if (host) applyPace(host, pace);
  }

  function applyPace(host, pace) {
    // updatePlaybackRate, not a new duration: the motion changes speed from where it
    // is, without jumping.
    host.shadowRoot.getAnimations().forEach((anim) => anim.updatePlaybackRate(pace));
  }

  /* ---- dozing ---------------------------------------------------------------------- */

  // Anything that moves makes the browser draw sixty or more new frames a second for
  // as long as the page is in view, whether or not anybody is looking. So when
  // nothing has been touched for a few minutes, everything ambient is paused where it
  // stands (css/animations.css, html.is-dozing) and picks up again at the first sign
  // of life. Never while the machine is writing: someone is watching that.
  const DOZE_AFTER_MS = 3 * 60 * 1000;
  let dozeTimer = 0;

  function stir() {
    document.documentElement.classList.remove("is-dozing");
    clearTimeout(dozeTimer);
    dozeTimer = setTimeout(() => {
      const stage = document.getElementById("stage");
      if (stage && stage.dataset.machineState === "composing") {
        stir();
        return;
      }
      document.documentElement.classList.add("is-dozing");
    }, DOZE_AFTER_MS);
  }

  function init() {
    ["pointermove", "pointerdown", "keydown", "wheel", "touchstart", "focus"].forEach((type) => {
      window.addEventListener(type, stir, { passive: true, capture: true });
    });
    stir();

    if (!window.fetch || !document.documentElement.attachShadow) return;
    document.querySelectorAll(SELECTOR).forEach((img) => {
      load(img.currentSrc || img.src)
        .then((markup) => place(img, markup))
        .catch(() => { /* stays an <img>, which animates itself */ });
    });
  }

  return { init, setPace };
})();
