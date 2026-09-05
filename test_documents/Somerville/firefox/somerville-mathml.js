    const axes = ["wght", "opsz", "wdth", "MGHT", "STYA", "STYB", "INSL", "ARLN", "ARHD"];
    const defaultValues = {
      wght: 400,
      wdth: 100,
      opsz: 12,
      MGHT: 400,
      STYA: 5,
      STYB: 5,
      INSL: 0,
      ARLN: 100,
      ARHD: 100,
      mathSize: 12,
      expand: 2,
    };
    const weightStops = [360, 400, 475, 550, 650, 750, 900];
    const widthStops = [94, 100, 114];
    const opticalSizeStops = [5, 6, 7, 8, 12, 16, 21, 32, 41, 48, 72, 96, 120, 160, 240, 360, 600, 900, 1200];
    const axisNames = {
      wght: {
        360: "SemiLight",
        400: "Regular",
        475: "Medium",
        550: "SemiBold",
        650: "Bold",
        750: "ExtraBold",
        900: "Black",
      },
      wdth: {
        94: "SemiCondensed",
        100: "Regular",
        114: "SemiExpanded",
      },
      opsz: {
        5: "Micro",
        6: "Minuscule",
        7: "Miniature",
        8: "Caption",
        12: "Regular",
        16: "SubHeading",
        21: "Trumpet",
        32: "Headline",
        48: "Display",
        72: "Titling",
        96: "Hairline",
      },
    };
    axisNames.MGHT = axisNames.wght;
    axisNames.STYA = axisNames.opsz;
    axisNames.STYB = axisNames.opsz;
    const expandStep = 0.2;
    const repeatDelay = 320;
    const repeatInterval = 90;
    const snippetsUrl = "./somerville-snippets.js";
    const snippetsRefreshInterval = 1000;
    const heldKeys = new Map();
    const defaultPlaceholders = ["M", "N", "p"];
    let mathSnippets = [{ tex: "c = \\pm\\sqrt{a^2 + b^2}", placeholders: defaultPlaceholders }];
    let snippetsSignature = "";
    let snippetsRefreshTimer = null;
    let snippetsLoadInFlight = false;
    let currentSnippetIndex = 0;
    let currentPlaceholderIndex = 0;

    function texCommandDefinition(name, replacement) {
      return `\\newcommand\\${name}{${replacement}}`;
    }

    function slidersAreLocked() {
      return document.getElementById("opsz-size-lock").checked;
    }

    function setMathSizeValue(value) {
      const input = document.getElementById("math-size");
      const min = Number(input.min);
      const max = Number(input.max);
      input.value = Math.min(max, Math.max(min, Number(value)));
    }

    function setAxisValue(axis, value) {
      const input = document.getElementById(axis);
      const min = Number(input.min);
      const max = Number(input.max);
      input.value = Math.min(max, Math.max(min, Number(value)));
    }

    function updateRenderedMathSize() {
      const mathSize = Number(document.getElementById("math-size").value);
      const expand = Number(document.getElementById("expand").value);
      document.documentElement.style.setProperty("--math-size", `${mathSize * expand}px`);
    }

    function axisDisplayValue(axis, value) {
      const numericValue = Number(value);
      return axis === "STYA" || axis === "STYB"
        ? numericValue.toFixed(1)
        : value;
    }

    function updateValueInputTitle(axis, value) {
      const name = axisNames[axis]?.[Number(value)];
      const output = document.getElementById(`${axis}-value`);
      const nameElement = document.getElementById(`${axis}-name`);
      output.title = name ? `${value} ${name}` : "";

      if (nameElement) {
        nameElement.textContent = name || "";
      }
    }

    function clampSliderValue(slider, value) {
      const min = Number(slider.min);
      const max = Number(slider.max);
      return Math.min(max, Math.max(min, Number(value)));
    }

    function commitManualValue(sliderId) {
      const slider = document.getElementById(sliderId);
      const valueInput = document.getElementById(`${sliderId}-value`);
      const typedValue = Number(valueInput.value);

      if (!Number.isFinite(typedValue)) {
        valueInput.value = sliderId === "expand"
          ? Number(slider.value).toFixed(2).replace(/\.?0+$/, "")
          : axisDisplayValue(sliderId, slider.value);
        return;
      }

      slider.value = clampSliderValue(slider, typedValue);

      if (axes.includes(sliderId)) {
        updateAxis(sliderId);
      } else if (sliderId === "math-size") {
        updateMathSize();
      } else if (sliderId === "expand") {
        updateExpand();
      }
    }

    function setupManualValue(sliderId) {
      const valueInput = document.getElementById(`${sliderId}-value`);

      valueInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") {
          return;
        }

        event.preventDefault();
        commitManualValue(sliderId);
        valueInput.blur();
      });
    }

    function updateAxis(axis, syncLockedSlider = true) {
      const input = document.getElementById(axis);
      const output = document.getElementById(`${axis}-value`);

      document.documentElement.style.setProperty(`--${axis}`, input.value);
      if (axis === "wdth") {
        document.documentElement.style.setProperty("--wdth-percent", `${input.value}%`);
      }
      output.value = axisDisplayValue(axis, input.value);
      updateValueInputTitle(axis, input.value);

      if (syncLockedSlider && axis === "opsz" && slidersAreLocked()) {
        setMathSizeValue(input.value);
        updateMathSize(false);
      }

      applyMathVariations();
    }

    function getAxisValues() {
      return {
        wght: Number(document.getElementById("wght").value),
        opsz: Number(document.getElementById("opsz").value),
        wdth: Number(document.getElementById("wdth").value),
        MGHT: Number(document.getElementById("MGHT").value),
        STYA: Number(document.getElementById("STYA").value),
        STYB: Number(document.getElementById("STYB").value),
        INSL: Number(document.getElementById("INSL").value),
        ARLN: Number(document.getElementById("ARLN").value),
        ARHD: Number(document.getElementById("ARHD").value),
      };
    }

    function getVariationSettings() {
      const { wght, opsz, wdth, MGHT, STYA, STYB, INSL, ARLN, ARHD } = getAxisValues();
      // CSS takes external coordinates; the browser applies the font's avar table.
      return `"wght" ${wght}, "opsz" ${opsz}, "wdth" ${wdth}, "MGHT" ${MGHT}, "STYA" ${STYA}, "STYB" ${STYB}, "INSL" ${INSL}, "ARLN" ${ARLN}, "ARHD" ${ARHD}`;
    }

    function applyMathVariations() {
      const axisValues = getAxisValues();
      const variationSettings = getVariationSettings();
      const featureSettings = axisValues.wght > 600 ? '"ss11" 1' : '"ss11" 0';
      const mathFontFamily = window.SomervilleLiveFontFamily || "SomervilleVF";

      document.querySelectorAll("#math-display math").forEach((element) => {
        element.style.fontFamily = `"${mathFontFamily}", "SomervilleVF", "MissingGlyphBlocker"`;
        element.style.fontWeight = axisValues.wght;
        element.style.fontStretch = `${axisValues.wdth}%`;
        element.style.fontVariationSettings = variationSettings;
        element.style.fontFeatureSettings = featureSettings;
        element.style.fontOpticalSizing = "none";
      });

      if (window.SomervilleFractionRuleThickness) {
        window.SomervilleFractionRuleThickness.apply(axisValues);
      }
    }

    function applyLetterVariant() {
      const uprightToggle = document.getElementById("upright-toggle");

      document.querySelectorAll("mi").forEach((identifier) => {
        if (uprightToggle.checked) {
          identifier.setAttribute("mathvariant", "normal");
          identifier.dataset.uprightVariant = "true";
        } else if (identifier.dataset.uprightVariant) {
          identifier.removeAttribute("mathvariant");
          delete identifier.dataset.uprightVariant;
        }
      });
    }

    function applyStretchyOperators() {
      const stretchy = document.getElementById("stretchy-toggle").checked;

      document.querySelectorAll("#math-display mo").forEach((operator) => {
        operator.setAttribute("stretchy", String(stretchy));
      });
    }

    function applyMathmlPlaceholder(root, placeholder) {
      const textNodes = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let textNode = textNodes.nextNode();

      while (textNode) {
        textNode.textContent = textNode.textContent.replaceAll("__PH__", placeholder);
        textNode = textNodes.nextNode();
      }
    }

    function updatePlaceholderInfo(placeholders, labels = []) {
      const placeholderInfo = document.getElementById("snippet-placeholders");
      const glyphs = placeholders.map((placeholder, index) => {
        const glyph = document.createElement("span");
        glyph.textContent = labels[index] || placeholder;
        glyph.classList.toggle("current-placeholder", index === currentPlaceholderIndex);
        return glyph;
      });

      placeholderInfo.replaceChildren(...glyphs);
    }

    function wrapSnippetText(flow) {
      [...flow.childNodes].forEach((node) => {
        if (node.nodeType !== Node.TEXT_NODE || !node.textContent) {
          if (
            node.nodeType === Node.ELEMENT_NODE &&
            node.matches("span") &&
            node.querySelector("math:not([display='block'])")
          ) {
            node.classList.add("snippet-inline-math");
          }
          return;
        }

        const fragment = document.createDocumentFragment();
        const lines = node.textContent.split(/\r?\n/);

        lines.forEach((line, index) => {
          if (index > 0) {
            fragment.append(document.createElement("br"));
          }

          if (!line) {
            return;
          }

          const text = document.createElement("span");
          text.className = "snippet-text";
          text.textContent = line;
          fragment.append(text);
        });

        node.replaceWith(fragment);
      });
    }

    function normalizeSnippets(data) {
      const snippets = Array.isArray(data) ? data : data?.snippets;

      if (!Array.isArray(snippets)) {
        throw new Error("Snippet file must define an array or an object with a snippets array.");
      }

      return snippets
        .map((snippet) => {
          if (typeof snippet === "string") {
            return { tex: snippet, placeholders: defaultPlaceholders };
          }

          const tex = typeof snippet?.tex === "string" && snippet.tex.trim() ? snippet.tex : undefined;
          const mathml = typeof snippet?.mathml === "string" && snippet.mathml.trim() ? snippet.mathml : undefined;
          const title = typeof snippet?.title === "string" ? snippet.title : "";
          const comment = typeof snippet?.comment === "string" ? snippet.comment : "";
          const stretchy = typeof snippet?.stretchy === "boolean" ? snippet.stretchy : undefined;
          // A placeholder can be a TeX string or { value: TeX, label: text }.
          const entries = (Array.isArray(snippet?.placeholders)
            ? snippet.placeholders
            : defaultPlaceholders)
            .map((entry) => typeof entry === "string" ? { value: entry } : entry)
            .filter((entry) => typeof entry?.value === "string");
          const placeholders = entries.map((entry) => entry.value);
          const placeholderLabels = entries.map((entry) =>
            typeof entry.label === "string" && entry.label.trim() ? entry.label : entry.value);

          return { title, comment, tex, mathml, stretchy, placeholders, placeholderLabels };
        })
        .filter((snippet) => snippet.tex || snippet.mathml);
    }

    function parseSnippetSource(source) {
      const sandbox = { SomervilleSnippets: undefined };
      const snippetModule = new Function(
        "window",
        `"use strict";\n${source}\n;return window.SomervilleSnippets;`
      );

      return snippetModule(sandbox);
    }

    function loadEmbeddedSnippets() {
      try {
        const snippets = normalizeSnippets(window.SomervilleSnippets);

        if (snippets.length) {
          mathSnippets = snippets;
          snippetsSignature = JSON.stringify(snippets);
        }
      } catch (error) {
        console.warn("Could not use the embedded Somerville snippets.", error);
      }
    }

    async function loadSnippets({ rerender = false } = {}) {
      if (snippetsLoadInFlight) {
        return;
      }

      snippetsLoadInFlight = true;

      try {
        const response = await fetch(`${snippetsUrl}?v=${Date.now()}`, { cache: "no-store" });

        if (!response.ok) {
          throw new Error(`Snippet request failed: ${response.status}`);
        }

        const data = parseSnippetSource(await response.text());
        const snippets = normalizeSnippets(data);
        const signature = JSON.stringify(snippets);

        if (!snippets.length || signature === snippetsSignature) {
          return;
        }

        const previousSnippetIndex = currentSnippetIndex;
        mathSnippets = snippets;
        snippetsSignature = signature;
        currentSnippetIndex = Math.min(previousSnippetIndex, mathSnippets.length - 1);
        const placeholderCount = mathSnippets[currentSnippetIndex].placeholders.length;
        currentPlaceholderIndex = placeholderCount
          ? Math.min(currentPlaceholderIndex, placeholderCount - 1)
          : 0;

        if (rerender) {
          renderSnippet({ initializeSnippetOptions: true });
        }
      } catch (error) {
        console.warn("Could not load Somerville snippets.", error);
      } finally {
        snippetsLoadInFlight = false;
      }
    }

    function renderSnippet({ initializeSnippetOptions = false } = {}) {
      const target = document.getElementById("math-display");
      const snippet = mathSnippets[currentSnippetIndex] || mathSnippets[0];
      const placeholders = snippet.placeholders || defaultPlaceholders;
      const placeholder = placeholders[currentPlaceholderIndex] ?? placeholders[0] ?? "";
      const macros = temml.definePreamble(texCommandDefinition("ph", placeholder));
      const flow = document.createElement("span");
      flow.className = "snippet-flow";
      flow.classList.toggle("mathml-snippet-flow", Boolean(snippet.mathml));
      document.getElementById("snippet-title").textContent = snippet.title || "";
      document.getElementById("snippet-comment").textContent = snippet.comment || "";
      updatePlaceholderInfo(placeholders, snippet.placeholderLabels);
      if (initializeSnippetOptions && typeof snippet.stretchy === "boolean") {
        document.getElementById("stretchy-toggle").checked = snippet.stretchy;
      }
      target.replaceChildren(flow);

      if (snippet.tex) {
        flow.textContent = snippet.tex.replace(/^\n/, "").replace(/\n\s*$/, "");
        temml.renderMathInElement(flow, {
          macros,
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\[", right: "\\]", display: true },
            { left: "\\(", right: "\\)", display: false },
          ],
        });
      } else {
        const template = document.createElement("template");
        template.innerHTML = snippet.mathml.trim();
        const firstElement = template.content.firstElementChild;

        if (firstElement?.localName === "math") {
          flow.append(template.content);
        } else {
          const math = document.createElementNS("http://www.w3.org/1998/Math/MathML", "math");
          math.innerHTML = snippet.mathml.trim();
          flow.append(math);
        }

        applyMathmlPlaceholder(flow, placeholder);
      }

      wrapSnippetText(flow);
      applyMathVariations();
      applyLetterVariant();
      applyStretchyOperators();
    }

    function cycleSnippet(direction) {
      currentSnippetIndex = (currentSnippetIndex + direction + mathSnippets.length) % mathSnippets.length;
      renderSnippet({ initializeSnippetOptions: true });
    }

    function startSnippetRefresh() {
      if (snippetsRefreshTimer) {
        return;
      }

      loadSnippets({ rerender: true });
      snippetsRefreshTimer = window.setInterval(
        () => loadSnippets({ rerender: true }),
        snippetsRefreshInterval
      );
    }

    function stopSnippetRefresh() {
      if (!snippetsRefreshTimer) {
        return;
      }

      window.clearInterval(snippetsRefreshTimer);
      snippetsRefreshTimer = null;
    }

    function updateMathSize(syncLockedSlider = true) {
      const input = document.getElementById("math-size");
      const output = document.getElementById("math-size-value");
      output.value = input.value;
      updateRenderedMathSize();

      if (syncLockedSlider && slidersAreLocked()) {
        setAxisValue("opsz", input.value);
        updateAxis("opsz");
      }

      applyMathVariations();
    }

    function updateExpand() {
      const input = document.getElementById("expand");
      const output = document.getElementById("expand-value");
      output.value = Number(input.value).toFixed(2).replace(/\.?0+$/, "");
      updateRenderedMathSize();
    }

    function stepAxis(axis, stops, direction) {
      const input = document.getElementById(axis);
      const current = Number(input.value);
      const target = direction < 0
        ? [...stops].reverse().find((stop) => stop < current) ?? stops[0]
        : stops.find((stop) => stop > current) ?? stops[stops.length - 1];

      input.value = target;
      updateAxis(axis);
    }

    function stepExpand(direction) {
      const input = document.getElementById("expand");
      const min = Number(input.min);
      const max = Number(input.max);
      const nextValue = Number(input.value) + direction * expandStep;

      input.value = Math.min(max, Math.max(min, nextValue));
      updateExpand();
    }

    function stepWeight(direction) {
      stepAxis("wght", weightStops, direction);
    }

    function stepWidth(direction) {
      stepAxis("wdth", widthStops, direction);
    }

    function stepOpticalSize(direction) {
      stepAxis("opsz", opticalSizeStops, direction);
    }

    function cyclePlaceholder(direction) {
      const snippet = mathSnippets[currentSnippetIndex] || mathSnippets[0];
      const placeholders = snippet.placeholders || defaultPlaceholders;
      if (!placeholders.length) {
        return;
      }
      currentPlaceholderIndex = (currentPlaceholderIndex + direction + placeholders.length) % placeholders.length;
      renderSnippet();
    }

    function jumpToFirstPlaceholder() {
      currentPlaceholderIndex = 0;
      renderSnippet();
    }

    function resetSliders() {
      document.getElementById("wght").value = defaultValues.wght;
      document.getElementById("wdth").value = defaultValues.wdth;
      document.getElementById("opsz").value = defaultValues.opsz;
      document.getElementById("MGHT").value = defaultValues.MGHT;
      document.getElementById("STYA").value = defaultValues.STYA;
      document.getElementById("STYB").value = defaultValues.STYB;
      document.getElementById("INSL").value = defaultValues.INSL;
      document.getElementById("ARLN").value = defaultValues.ARLN;
      document.getElementById("ARHD").value = defaultValues.ARHD;
      document.getElementById("math-size").value = defaultValues.mathSize;
      document.getElementById("expand").value = defaultValues.expand;

      if (slidersAreLocked()) {
        setMathSizeValue(defaultValues.opsz);
      }

      axes.forEach((axis) => updateAxis(axis));
      updateMathSize();
      updateExpand();
    }

    function updateSliderLock() {
      if (!slidersAreLocked()) {
        return;
      }

      setMathSizeValue(document.getElementById("opsz").value);
      updateMathSize(false);
    }

    function updateGridVisibility() {
      document.body.classList.toggle("show-grid", document.getElementById("grid-toggle").checked);
    }

    function updateTitleVisibility() {
      document.body.classList.toggle("hide-snippet-title", !document.getElementById("title-toggle").checked);
    }

    function updateGridSize() {
      const input = document.getElementById("grid-size");
      const output = document.getElementById("grid-size-value");
      output.value = Number(input.value).toFixed(2).replace(/\.?0+$/, "");
      document.documentElement.style.setProperty("--grid-size", `${input.value}em`);
    }

    function toggleUprightLetters() {
      const input = document.getElementById("upright-toggle");
      input.checked = !input.checked;
      applyLetterVariant();
    }

    function toggleSnippetTitle() {
      const input = document.getElementById("title-toggle");
      input.checked = !input.checked;
      updateTitleVisibility();
    }

    function toggleControlPanel() {
      const panel = document.getElementById("control-panel");
      const button = document.getElementById("controls-toggle");
      const panelIsHidden = !panel.hidden;

      panel.hidden = panelIsHidden;
      button.textContent = panelIsHidden ? "Show" : "Hide";
      button.title = panelIsHidden ? "Show controls" : "Hide controls";
      button.setAttribute("aria-expanded", String(!panelIsHidden));
    }

    const shortcuts = {
      q: () => stepWeight(-1),
      w: () => stepWeight(1),
      a: () => stepWidth(-1),
      s: () => stepWidth(1),
      z: () => stepOpticalSize(-1),
      x: () => stepOpticalSize(1),
      ArrowLeft: () => cycleSnippet(-1),
      ArrowRight: () => cycleSnippet(1),
      ArrowUp: () => cyclePlaceholder(1),
      ArrowDown: () => cyclePlaceholder(-1),
      1: () => stepExpand(-1),
      2: () => stepExpand(1),
      f: jumpToFirstPlaceholder,
      u: toggleUprightLetters,
      t: toggleSnippetTitle,
      r: resetSliders,
      h: toggleControlPanel,
    };

    function stopRepeatingKey(key) {
      const timers = heldKeys.get(key);

      if (!timers) {
        return;
      }

      clearTimeout(timers.delayTimer);
      clearInterval(timers.intervalTimer);
      heldKeys.delete(key);
    }

    function stopAllRepeatingKeys() {
      [...heldKeys.keys()].forEach(stopRepeatingKey);
    }

    function startRepeatingKey(key) {
      const action = shortcuts[key];

      if (!action || heldKeys.has(key)) {
        return;
      }

      action();

      const timers = {
        delayTimer: window.setTimeout(() => {
          action();
          timers.intervalTimer = window.setInterval(action, repeatInterval);
        }, repeatDelay),
        intervalTimer: null,
      };

      heldKeys.set(key, timers);
    }

    axes.forEach((axis) => {
      const input = document.getElementById(axis);
      input.addEventListener("input", () => updateAxis(axis));
      setupManualValue(axis);
      updateAxis(axis);
    });

    document.getElementById("math-size").addEventListener("input", () => updateMathSize());
    document.getElementById("expand").addEventListener("input", updateExpand);
    setupManualValue("math-size");
    setupManualValue("expand");
    document.getElementById("upright-toggle").addEventListener("change", applyLetterVariant);
    document.getElementById("stretchy-toggle").addEventListener("change", applyStretchyOperators);
    document.getElementById("title-toggle").addEventListener("change", updateTitleVisibility);
    document.getElementById("grid-toggle").addEventListener("change", updateGridVisibility);
    document.getElementById("grid-size").addEventListener("input", updateGridSize);
    document.getElementById("opsz-size-lock").addEventListener("change", updateSliderLock);
    document.getElementById("controls-toggle").addEventListener("click", toggleControlPanel);
    loadEmbeddedSnippets();
    renderSnippet({ initializeSnippetOptions: true });
    updateMathSize();
    updateExpand();
    updateTitleVisibility();

    document.addEventListener("keydown", (event) => {
      if (event.target.matches("input[type='text']")) {
        return;
      }

      const shortcutKey = event.key;

      if (event.metaKey || event.ctrlKey || !shortcuts[shortcutKey]) {
        return;
      }

      event.preventDefault();
      startRepeatingKey(shortcutKey);
    });

    document.addEventListener("keyup", (event) => {
      stopRepeatingKey(event.key);
    });

    window.addEventListener("blur", stopAllRepeatingKeys);

    Promise.allSettled([
      window.SomervilleAvarCompensation
        ? window.SomervilleAvarCompensation.loadFont("./SomervilleVF-withMathtable.ttf")
        : Promise.resolve(),
      window.SomervilleFractionRuleThickness
        ? window.SomervilleFractionRuleThickness.loadFont("./SomervilleVF-withMathtable.ttf")
        : Promise.resolve(),
    ]).then(applyMathVariations);

    if (window.SomervilleFontWatcher) {
      window.SomervilleFontWatcher.start({
        onServerAvailable: startSnippetRefresh,
        onServerUnavailable: stopSnippetRefresh,
      });
    }
