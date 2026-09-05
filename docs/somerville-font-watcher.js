/*
 * July 9, 2026
 *
 * This script keeps the Somerville MathML test page in sync with the local
 * SomervilleVF-withMathtable.ttf file while the page is open.
 *
 * Browsers do not let a file:// page watch the filesystem directly, and they
 * are often aggressive about caching font URLs. The companion Python server
 * exposes the font's modification time at /__somerville_font_status. This script
 * polls that endpoint, and when the timestamp changes it loads the font through
 * the FontFace API with a cache-busting query string.
 *
 * The page is not reloaded. Instead, we install the new font under a versioned
 * family name and ask the existing page code to reapply its current MathML
 * variation settings. That preserves all sliders, the selected sample, the
 * placeholder letter, and the current MathML content.
 */

(function () {
  const DEFAULT_FONT_FILE = "SomervilleVF-withMathtable.ttf";
  const DEFAULT_STATUS_URL = `./__somerville_font_status?file=${encodeURIComponent(DEFAULT_FONT_FILE)}`;
  const DEFAULT_POLL_INTERVAL_MS = 100;
  const BASE_FAMILY = "SomervilleVF";

  let lastSignature = null;
  let pollTimer = null;
  let activeFace = null;
  let reloadInFlight = false;
  let toastTimer = null;
  let toastMode = null;
  let lastFailedBuildKey = null;
  let displayedLoadedStatus = false;

  function hideRefreshToast() {
    const toast = document.getElementById("font-refresh-toast");
    const icon = document.getElementById("font-refresh-toast-icon");

    if (!toast || !icon) {
      return;
    }

    if (toastTimer) {
      window.clearTimeout(toastTimer);
      toastTimer = null;
    }

    toast.classList.remove("is-visible", "is-done", "is-failed", "is-sticky");
    toast.setAttribute("aria-hidden", "true");
    icon.textContent = "";
    toastMode = null;
  }

  function showRefreshToast(message, options = {}) {
    const toast = document.getElementById("font-refresh-toast");
    const icon = document.getElementById("font-refresh-toast-icon");
    const text = document.getElementById("font-refresh-toast-text");

    if (!toast || !icon || !text) {
      return;
    }

    const done = Boolean(options.done);
    const failed = Boolean(options.failed);
    const sticky = Boolean(options.sticky);
    toastMode = options.mode || null;

    if (toastTimer) {
      window.clearTimeout(toastTimer);
      toastTimer = null;
    }

    text.textContent = message;
    icon.textContent = failed ? "!" : done ? "✓" : "";
    toast.classList.toggle("is-done", done);
    toast.classList.toggle("is-failed", failed);
    toast.classList.toggle("is-sticky", sticky);
    toast.classList.add("is-visible");
    toast.setAttribute("aria-hidden", "false");

    if (done) {
      toastTimer = window.setTimeout(() => {
        toast.classList.remove("is-visible", "is-done");
        toast.setAttribute("aria-hidden", "true");
        icon.textContent = "";
        toastMode = null;
      }, 2200);
    }
  }

  function hideBuildRunningToast() {
    if (toastMode === "build-running") {
      hideRefreshToast();
    }
  }

  function updateBuildRunningToast(build) {
    if (build?.running) {
      if (toastMode !== "build-running") {
        showRefreshToast("Building", { mode: "build-running" });
      }
      return;
    }

    hideBuildRunningToast();
  }

  function failedBuildKey(build) {
    if (!build || build.lastStatus !== "failed") {
      return null;
    }

    return `${build.lastRunFinishedNs || "unknown"}:${build.lastReturnCode}`;
  }

  function updateBuildFailureToast(build) {
    const key = failedBuildKey(build);

    if (!key || key === lastFailedBuildKey) {
      return;
    }

    lastFailedBuildKey = key;
    hideBuildRunningToast();
    showRefreshToast("failed compile", { failed: true, sticky: true });
  }

  function timestampForStatus(status) {
    return new Date(status.mtimeNs / 1000000);
  }

  function timestampFromNs(ns) {
    return ns ? new Date(ns / 1000000) : null;
  }

  function formatTimestamp(status) {
    return timestampForStatus(status).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function formatDate(date) {
    return date.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function buildStatusText(build) {
    if (!build) {
      return "";
    }

    const regularFontText = regularFontStatusText(build.regularFont);

    if (build.running) {
      const started = timestampFromNs(build.lastRunStartedNs);
      const buildText = started
        ? ` · build running since <time datetime="${started.toISOString()}">${formatDate(started)}</time>`
        : " · build running";
      return buildText + regularFontText;
    }

    if (build.lastStatus === "success" || build.lastStatus === "failed") {
      const finished = timestampFromNs(build.lastRunFinishedNs);
      const label = build.lastStatus === "success" ? "build succeeded" : "build failed";
      const timestamp = finished
        ? ` at <time datetime="${finished.toISOString()}">${formatDate(finished)}</time>`
        : "";
      const code = build.lastReturnCode === null ? "" : `, exit ${build.lastReturnCode}`;
      return ` · ${label}${timestamp}${code}` + regularFontText;
    }

    return " · build not run" + regularFontText;
  }

  function regularFontStatusText(regularFont) {
    if (!regularFont || regularFont.lastStatus === "not_run") {
      return "";
    }

    const copied = timestampFromNs(regularFont.lastCopiedNs);
    const timestamp = copied
      ? ` at <time datetime="${copied.toISOString()}">${formatDate(copied)}</time>`
      : "";

    if (regularFont.lastStatus === "success") {
      return ` · regular font copied${timestamp}`;
    }

    if (regularFont.lastStatus === "failed") {
      return ` · regular font copy failed${timestamp}`;
    }

    return "";
  }

  function updateStatusDisplay(status, loaded) {
    const statusElement = document.getElementById("font-status");

    if (!statusElement) {
      return;
    }

    const timestamp = timestampForStatus(status);
    const label = loaded ? "Font loaded" : "Font timestamp";

    statusElement.innerHTML =
      `${label}: <time datetime="${timestamp.toISOString()}">${formatTimestamp(status)}</time>` +
      ` · ${status.file} · ${status.size} bytes` +
      buildStatusText(status.build);
  }

  function fontUrlForStatus(status) {
    return `./${encodeURIComponent(status.file)}?v=${encodeURIComponent(status.signature)}`;
  }

  function familyForStatus(status) {
    return `${BASE_FAMILY}-live-${status.signature}`.replace(/[^A-Za-z0-9_-]/g, "-");
  }

  async function loadVersionedFont(status) {
    showRefreshToast("Refreshing");

    const family = familyForStatus(status);
    const fontUrl = fontUrlForStatus(status);
    const face = new FontFace(family, `url("${fontUrl}") format("truetype")`, {
      display: "block",
      stretch: "94% 114%",
      style: "normal",
      weight: "360 900",
    });

    await face.load();
    document.fonts.add(face);

    if (activeFace) {
      document.fonts.delete(activeFace);
    }

    activeFace = face;
    window.SomervilleLiveFontFamily = family;
    displayedLoadedStatus = true;
    updateStatusDisplay(status, true);

    await Promise.allSettled([
      window.SomervilleAvarCompensation
        ? window.SomervilleAvarCompensation.loadFont(fontUrl)
        : Promise.resolve(),
      window.SomervilleFractionRuleThickness
        ? window.SomervilleFractionRuleThickness.loadFont(fontUrl)
        : Promise.resolve(),
    ]);

    if (typeof window.applyMathVariations === "function") {
      window.applyMathVariations();
    }

    showRefreshToast("Updated", { done: true });
  }

  async function getFontStatus(statusUrl) {
    const response = await fetch(statusUrl, { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`Font status request failed: ${response.status}`);
    }

    return response.json();
  }

  async function poll(statusUrl) {
    if (reloadInFlight) {
      return;
    }

    reloadInFlight = true;

    try {
      const status = await getFontStatus(statusUrl);
      updateBuildRunningToast(status.build);
      updateBuildFailureToast(status.build);

      if (!lastSignature) {
        lastSignature = status.signature;
        updateStatusDisplay(status, displayedLoadedStatus);
        return;
      }

      if (status.signature !== lastSignature) {
        lastSignature = status.signature;
        await loadVersionedFont(status);
      } else {
        updateStatusDisplay(status, displayedLoadedStatus);
      }
    } catch (error) {
      console.warn("Somerville font watcher could not check for updates.", error);
    } finally {
      reloadInFlight = false;
    }
  }

  function start(options = {}) {
    const statusUrl = options.statusUrl || DEFAULT_STATUS_URL;
    const pollIntervalMs = options.pollIntervalMs || DEFAULT_POLL_INTERVAL_MS;

    if (!("FontFace" in window)) {
      console.warn("Somerville font watcher needs the FontFace API.");
      return;
    }

    if (pollTimer) {
      window.clearInterval(pollTimer);
    }

    const toast = document.getElementById("font-refresh-toast");
    if (toast) {
      toast.addEventListener("click", hideRefreshToast);
    }

    poll(statusUrl);
    pollTimer = window.setInterval(() => poll(statusUrl), pollIntervalMs);
  }

  window.SomervilleFontWatcher = { start };
}());
