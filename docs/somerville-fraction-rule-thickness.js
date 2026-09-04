/*
 * July 9, 2026
 *
 * The OpenType MATH FractionRuleThickness constant is fixed in the font, even
 * though Somerville is a variable font. This helper computes the rule thickness
 * that we want for the current variable-font coordinates and applies it to
 * MathML fractions on the page.
 *
 * The interpolation uses the internal design-space coordinates produced by the
 * font's avar table. This matches the way a variable font interpolates: first
 * map the external slider coordinates through avar, then interpolate in the
 * resulting design space.
 *
 *   internal opsz 1200, internal wght 360      -> fraction rule 2
 *   internal opsz 1200, internal wght 900      -> fraction rule 2
 *   internal opsz 5, internal wght 360         -> fraction rule 80
 *   internal opsz 5, internal wght 900         -> fraction rule 120
 *
 * Those four corners form a bilinear surface. Width has no effect.
 *
 * The rule values are font units, so this file converts them to em using the
 * font's unitsPerEm value from the head table. When this
 * page is opened from a file:// URL, browser security rules block that fetch,
 * so the helper uses Somerville's hardcoded fallback of 1240 units per em.
 */

(function () {
  const FONT_URL = "./SomervilleVF-withMathtable.ttf";
  const FALLBACK_UNITS_PER_EM = 1240;
  const OPSZ_MIN = 2;
  const OPSZ_MAX = 1200;
  const WGHT_MIN = 360;
  const WGHT_MAX = 900;
  const RULE_AT_MAX_OPSZ = 2;
  const RULE_AT_MIN_OPSZ_MIN_WGHT = 80;
  const RULE_AT_MIN_OPSZ_MAX_WGHT = 120;

  let unitsPerEm = FALLBACK_UNITS_PER_EM;

  function readTag(view, offset) {
    return String.fromCharCode(
      view.getUint8(offset),
      view.getUint8(offset + 1),
      view.getUint8(offset + 2),
      view.getUint8(offset + 3)
    );
  }

  function getTables(view) {
    const tableCount = view.getUint16(4, false);
    const tables = {};

    for (let index = 0; index < tableCount; index += 1) {
      const recordOffset = 12 + index * 16;
      const tag = readTag(view, recordOffset);
      tables[tag] = {
        offset: view.getUint32(recordOffset + 8, false),
        length: view.getUint32(recordOffset + 12, false),
      };
    }

    return tables;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function interpolate(start, end, progress) {
    return start + (end - start) * progress;
  }

  function compensateAxis(tag, value) {
    if (!window.SomervilleAvarCompensation) {
      return value;
    }

    return window.SomervilleAvarCompensation.compensateAxis(tag, value);
  }

  function fractionRuleInFontUnits(values) {
    const internalOpsz = clamp(compensateAxis("opsz", values.opsz), OPSZ_MIN, OPSZ_MAX);
    const internalWght = clamp(compensateAxis("wght", values.wght), WGHT_MIN, WGHT_MAX);
    const weightProgress = (internalWght - WGHT_MIN) / (WGHT_MAX - WGHT_MIN);
    const opszProgress = (internalOpsz - OPSZ_MIN) / (OPSZ_MAX - OPSZ_MIN);
    const bottomRule = interpolate(
      RULE_AT_MIN_OPSZ_MIN_WGHT,
      RULE_AT_MIN_OPSZ_MAX_WGHT,
      weightProgress
    );
    const topRule = interpolate(RULE_AT_MAX_OPSZ, RULE_AT_MAX_OPSZ, weightProgress);

    return interpolate(bottomRule, topRule, opszProgress);
  }

  function formatEm(fontUnits) {
    return `${fontUnits / unitsPerEm}em`;
  }

  function apply(values) {
    const fontUnits = fractionRuleInFontUnits(values);
    const thickness = formatEm(fontUnits);

    document.querySelectorAll("mfrac").forEach((fraction) => {
      fraction.setAttribute("linethickness", thickness);
    });
  }

  async function loadFont(url = FONT_URL) {
    if (window.location.protocol === "file:") {
      return;
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Could not load ${url}`);
    }

    const view = new DataView(await response.arrayBuffer());
    const tables = getTables(view);

    if (tables.head) {
      unitsPerEm = view.getUint16(tables.head.offset + 18, false);
    }
  }

  window.SomervilleFractionRuleThickness = {
    apply,
    fractionRuleInFontUnits,
    loadFont,
  };
}());
