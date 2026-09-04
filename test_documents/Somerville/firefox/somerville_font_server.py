#!/usr/bin/env python3
"""Serve the Somerville MathML test page and report font file changes.

Run this from /Users/juliusross/Documents/mathtestingtool:

    python3 somerville_font_server.py

Then open http://127.0.0.1:8000/somerville-mathml.html. The HTML and font are
served from the same origin, so browser JavaScript can poll the font status and
fetch fresh font-table data when SomervilleVF-withMathtable.ttf changes on disk.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = 8000
WATCH_INTERVAL_SECONDS = 1.0
ROOT = Path(__file__).resolve().parent
DEFAULT_FONT = "SomervilleVF-withMathtable.ttf"
SOURCE_PACKAGE = Path("~/Documents/Somerville/sources/SomervilleA.glyphspackage").expanduser()
REGULAR_SOURCE_FONT = Path("~/Documents/mathconstantseditor/fonts/Somerville-Regular.otf").expanduser()
REGULAR_LOCAL_FONT = ROOT / "Somerville-Regular.otf"
BUILD_SCRIPT = ROOT / "insertmathtable.sh"
RUN_INSERT_MATHTABLE = True

build_lock = threading.Lock()
build_state = {
    "sourceSignature": None,
    "running": False,
    "lastStatus": "not_run",
    "lastRunStartedNs": None,
    "lastRunFinishedNs": None,
    "lastReturnCode": None,
    "lastMessage": "No build has run in this server session.",
}
regular_font_state = {
    "sourceSignature": None,
    "lastStatus": "not_run",
    "lastCopiedNs": None,
    "lastMessage": "No regular font copy has run in this server session.",
}


def now_ns() -> int:
    return time.time_ns()


def source_signature() -> str | None:
    """Return a cheap recursive signature for the Glyphs package on disk."""

    if not SOURCE_PACKAGE.exists():
        return None

    if SOURCE_PACKAGE.is_file():
        stat = SOURCE_PACKAGE.stat()
        return f"{stat.st_mtime_ns}-{stat.st_size}"

    newest_mtime = 0
    total_size = 0
    file_count = 0

    for path in SOURCE_PACKAGE.rglob("*"):
        if not path.is_file():
            continue

        stat = path.stat()
        newest_mtime = max(newest_mtime, stat.st_mtime_ns)
        total_size += stat.st_size
        file_count += 1

    package_stat = SOURCE_PACKAGE.stat()
    newest_mtime = max(newest_mtime, package_stat.st_mtime_ns)
    return f"{newest_mtime}-{file_count}-{total_size}"


def file_signature(path: Path) -> str | None:
    if not path.exists():
        return None

    stat = path.stat()
    return f"{stat.st_mtime_ns}-{stat.st_size}"


def short_output(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text

    return text[-limit:]


def run_build(expected_signature: str | None) -> None:
    if not RUN_INSERT_MATHTABLE:
        return

    print(f"[build] Starting {BUILD_SCRIPT.name}", flush=True)

    with build_lock:
        build_state.update({
            "running": True,
            "lastStatus": "running",
            "lastRunStartedNs": now_ns(),
            "lastRunFinishedNs": None,
            "lastReturnCode": None,
            "lastMessage": f"Running {BUILD_SCRIPT.name}...",
        })

    try:
        process = subprocess.Popen(
            ["sh", str(BUILD_SCRIPT)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output_parts = []

        if process.stdout:
            for line in process.stdout:
                print(line, end="", flush=True)
                output_parts.append(line)

        return_code = process.wait()
        output = short_output("".join(output_parts))
        status = "success" if return_code == 0 else "failed"
        message = output or ("Build completed." if return_code == 0 else "Build failed with no output.")

        print(f"[build] {BUILD_SCRIPT.name} {status} with exit {return_code}", flush=True)

        with build_lock:
            build_state.update({
                "sourceSignature": expected_signature,
                "running": False,
                "lastStatus": status,
                "lastRunFinishedNs": now_ns(),
                "lastReturnCode": return_code,
                "lastMessage": message,
            })
    except Exception as error:
        print(f"[build] {BUILD_SCRIPT.name} failed: {error}", flush=True)

        with build_lock:
            build_state.update({
                "sourceSignature": expected_signature,
                "running": False,
                "lastStatus": "failed",
                "lastRunFinishedNs": now_ns(),
                "lastReturnCode": None,
                "lastMessage": str(error),
            })


def check_source_and_maybe_build() -> None:
    if not RUN_INSERT_MATHTABLE:
        return

    signature = source_signature()

    with build_lock:
        if build_state["sourceSignature"] is None:
            build_state["sourceSignature"] = signature
            return

        if build_state["running"] or signature == build_state["sourceSignature"]:
            return

    threading.Thread(target=run_build, args=(signature,), daemon=True).start()


def check_regular_font_and_maybe_copy() -> None:
    signature = file_signature(REGULAR_SOURCE_FONT)

    with build_lock:
        if regular_font_state["sourceSignature"] is None:
            regular_font_state["sourceSignature"] = signature
            return

        if signature == regular_font_state["sourceSignature"]:
            return

    try:
        print(f"[regular-font] Copying {REGULAR_SOURCE_FONT} to {REGULAR_LOCAL_FONT}", flush=True)
        shutil.copy2(REGULAR_SOURCE_FONT, REGULAR_LOCAL_FONT)
        copied_ns = now_ns()

        with build_lock:
            regular_font_state.update({
                "sourceSignature": signature,
                "lastStatus": "success",
                "lastCopiedNs": copied_ns,
                "lastMessage": f"Copied {REGULAR_SOURCE_FONT.name}.",
            })

        print(f"[regular-font] Copied {REGULAR_SOURCE_FONT.name}", flush=True)
    except Exception as error:
        with build_lock:
            regular_font_state.update({
                "sourceSignature": signature,
                "lastStatus": "failed",
                "lastCopiedNs": now_ns(),
                "lastMessage": str(error),
            })

        print(f"[regular-font] Copy failed: {error}", flush=True)


def watch_sources() -> None:
    """Continuously watch source files, independently of browser requests."""

    while True:
        try:
            check_source_and_maybe_build()
            check_regular_font_and_maybe_copy()
        except Exception as error:
            print(f"[watch] Source check failed: {error}", flush=True)

        time.sleep(WATCH_INTERVAL_SECONDS)


def public_build_state() -> dict:
    with build_lock:
        state = dict(build_state)
        regular_state = dict(regular_font_state)

    state["source"] = str(SOURCE_PACKAGE)
    state["script"] = BUILD_SCRIPT.name
    state["enabled"] = RUN_INSERT_MATHTABLE
    state["regularFont"] = {
        **regular_state,
        "source": str(REGULAR_SOURCE_FONT),
        "destination": str(REGULAR_LOCAL_FONT),
    }
    return state


class SomervilleHandler(SimpleHTTPRequestHandler):
    """Static-file handler with one JSON endpoint for font modification status."""

    def log_message(self, format: str, *args: object) -> None:
        # Suppress the default per-request access log; the page polls often.
        return

    def end_headers(self) -> None:
        # Allow the status endpoint and font files to be read even if someone
        # accidentally opens the HTML through file:// while this server is up.
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/__somerville_font_status":
            self.send_font_status(parsed.query)
            return

        super().do_GET()

    def send_font_status(self, query: str) -> None:
        check_source_and_maybe_build()
        check_regular_font_and_maybe_copy()

        params = parse_qs(query)
        requested = params.get("file", [DEFAULT_FONT])[0]
        font_path = (ROOT / requested).resolve()

        if ROOT not in font_path.parents and font_path != ROOT:
            self.send_error(403, "Font path must stay inside the test directory")
            return

        if not font_path.exists():
            self.send_error(404, "Font file not found")
            return

        stat = font_path.stat()
        payload = {
            "file": font_path.name,
            "mtimeNs": stat.st_mtime_ns,
            "size": stat.st_size,
            "signature": f"{stat.st_mtime_ns}-{stat.st_size}",
            "build": public_build_state(),
        }
        encoded = json.dumps(payload).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-insert-mathtable",
        action="store_true",
        help=f"serve files without running {BUILD_SCRIPT.name} when the Glyphs source changes",
    )
    return parser.parse_args()


def main() -> None:
    global RUN_INSERT_MATHTABLE

    arguments = parse_arguments()
    RUN_INSERT_MATHTABLE = not arguments.no_insert_mathtable
    if not RUN_INSERT_MATHTABLE:
        build_state.update({
            "lastStatus": "disabled",
            "lastMessage": f"Automatic {BUILD_SCRIPT.name} runs are disabled.",
        })

    mimetypes.add_type("font/ttf", ".ttf")
    mimetypes.add_type("font/otf", ".otf")

    server = ThreadingHTTPServer((HOST, PORT), SomervilleHandler)
    print(f"Serving {ROOT} at http://{HOST}:{PORT}/somerville-mathml.html")
    print(f"Watching {ROOT / DEFAULT_FONT}")
    print(f"Watching source package {SOURCE_PACKAGE}")
    print(f"Watching regular font {REGULAR_SOURCE_FONT}")
    if RUN_INSERT_MATHTABLE:
        print(f"Running {BUILD_SCRIPT} when the source package changes")
    else:
        print(f"Automatic {BUILD_SCRIPT.name} runs are disabled")

    watcher = threading.Thread(target=watch_sources, daemon=True, name="somerville-source-watcher")
    watcher.start()
    print(f"Polling source files every {WATCH_INTERVAL_SECONDS:g} second(s)")
    server.serve_forever()


if __name__ == "__main__":
    main()
