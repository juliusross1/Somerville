/*
 * July 9, 2026
 *
 * This file converts the slider's external axis coordinates into the internal
 * coordinates produced by the font's avar table. It was originally used to
 * compensate for browser MathML rendering that appeared to ignore avar. After
 * fixing the font's invalid wdth avar entry, browser MathML rendering should
 * receive the same external coordinates as text; this helper remains useful for
 * page-side calculations that need internal coordinates, such as variable
 * fraction-rule thickness.
 *
 * The helper tries to read fvar and avar directly from SomervilleVF-withMathtable.ttf
 * in the browser. When this page is opened from a file:// URL, browser security
 * rules block that fetch, so the helper uses hardcoded values from the current
 * Somerville font instead.
 */

(function () {
  const fallbackAxes = {
    opsz: {
      min: 5,
      defaultValue: 5,
      max: 1200,
      map: [
        [-1, -1],
        [0, 0],
        [0.00085, 0.1632],
        [0.00165, 0.26776],
        [0.0025, 0.33057],
        [0.00586, 0.45605],
        [0.0092, 0.5314],
        [0.01337, 0.5816],
        [0.0226, 0.6653],
        [0.03015, 0.71545],
        [0.036, 0.74896],
        [0.0561, 0.8159],
        [0.0762, 0.84937],
        [1, 1],
      ],
    },
    wdth: {
      min: 88,
      defaultValue: 88,
      max: 113,
      map: [
        [-1, -1],
        [0, 0],
        [0.48, 0.2778],
        [0.98, 1],
        [1, 1],
      ],
    },
    wght: {
      min: 360,
      defaultValue: 360,
      max: 900,
      map: [
        [-1, -1],
        [0, 0],
        [0.0741, 0.0741],
        [0.2593, 0.21295],
        [0.44446, 0.35187],
        [0.62964, 0.53705],
        [0.8148, 0.7222],
        [1, 1],
      ],
    },
  };

  let axes = fallbackAxes;

  function readTag(view, offset) {
    return String.fromCharCode(
      view.getUint8(offset),
      view.getUint8(offset + 1),
      view.getUint8(offset + 2),
      view.getUint8(offset + 3)
    );
  }

  function readFixed(view, offset) {
    return view.getInt32(offset, false) / 65536;
  }

  function readF2Dot14(view, offset) {
    return view.getInt16(offset, false) / 16384;
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

  function parseFvar(view, table) {
    const offset = table.offset;
    const axesOffset = offset + view.getUint16(offset + 4, false);
    const axisCount = view.getUint16(offset + 8, false);
    const axisSize = view.getUint16(offset + 10, false);
    const parsedAxes = [];

    for (let index = 0; index < axisCount; index += 1) {
      const axisOffset = axesOffset + index * axisSize;
      parsedAxes.push({
        tag: readTag(view, axisOffset),
        min: readFixed(view, axisOffset + 4),
        defaultValue: readFixed(view, axisOffset + 8),
        max: readFixed(view, axisOffset + 12),
      });
    }

    return parsedAxes;
  }

  function parseAvar(view, table, parsedAxes) {
    const offset = table.offset;
    const axisCount = view.getUint16(offset + 6, false);
    const parsedMaps = {};
    let cursor = offset + 8;

    for (let axisIndex = 0; axisIndex < axisCount; axisIndex += 1) {
      const pairCount = view.getUint16(cursor, false);
      const axis = parsedAxes[axisIndex];
      cursor += 2;

      if (!axis) {
        cursor += pairCount * 4;
        continue;
      }

      parsedMaps[axis.tag] = [];

      for (let pairIndex = 0; pairIndex < pairCount; pairIndex += 1) {
        parsedMaps[axis.tag].push([
          readF2Dot14(view, cursor),
          readF2Dot14(view, cursor + 2),
        ]);
        cursor += 4;
      }
    }

    return parsedMaps;
  }

  function normalize(value, axis) {
    if (value === axis.defaultValue) {
      return 0;
    }

    if (value > axis.defaultValue) {
      const range = axis.max - axis.defaultValue;
      return range === 0 ? 0 : (value - axis.defaultValue) / range;
    }

    const range = axis.defaultValue - axis.min;
    return range === 0 ? 0 : (value - axis.defaultValue) / range;
  }

  function denormalize(value, axis) {
    if (value >= 0) {
      return axis.defaultValue + value * (axis.max - axis.defaultValue);
    }

    return axis.defaultValue + value * (axis.defaultValue - axis.min);
  }

  function interpolate(value, points) {
    if (!points || points.length === 0) {
      return value;
    }

    if (value <= points[0][0]) {
      return points[0][1];
    }

    for (let index = 1; index < points.length; index += 1) {
      const [from, to] = points[index];
      const [previousFrom, previousTo] = points[index - 1];

      if (value <= from) {
        const span = from - previousFrom;
        const progress = span === 0 ? 0 : (value - previousFrom) / span;
        return previousTo + progress * (to - previousTo);
      }
    }

    return points[points.length - 1][1];
  }

  function compensateAxis(tag, value) {
    const axis = axes[tag];

    if (!axis) {
      return value;
    }

    const normalized = Math.max(-1, Math.min(1, normalize(value, axis)));
    const mapped = interpolate(normalized, axis.map);
    return denormalize(mapped, axis);
  }

  function formatNumber(value) {
    return Number(value.toFixed(4)).toString();
  }

  function settingsFor(values) {
    return `"wght" ${formatNumber(compensateAxis("wght", values.wght))}, ` +
      `"opsz" ${formatNumber(compensateAxis("opsz", values.opsz))}, ` +
      `"wdth" ${formatNumber(compensateAxis("wdth", values.wdth))}`;
  }

  async function loadFont(url) {
    if (window.location.protocol === "file:") {
      return;
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Could not load ${url}`);
    }

    const view = new DataView(await response.arrayBuffer());
    const tables = getTables(view);

    if (!tables.fvar || !tables.avar) {
      return;
    }

    const parsedAxes = parseFvar(view, tables.fvar);
    const parsedMaps = parseAvar(view, tables.avar, parsedAxes);
    const nextAxes = {};

    parsedAxes.forEach((axis) => {
      if (parsedMaps[axis.tag]) {
        nextAxes[axis.tag] = {
          min: axis.min,
          defaultValue: axis.defaultValue,
          max: axis.max,
          map: parsedMaps[axis.tag],
        };
      }
    });

    axes = { ...fallbackAxes, ...nextAxes };
  }

  window.SomervilleAvarCompensation = {
    compensateAxis,
    loadFont,
    settingsFor,
  };
}());
