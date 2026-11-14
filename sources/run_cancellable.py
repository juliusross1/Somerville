"""Run one build step in its own process group, with reliable cancellation.

The launcher receives terminal Control-C even if the command ignores SIGINT.
On cancellation it sends SIGTERM to that command's process group, then SIGKILL
after two seconds (or a second Control-C) if processes remain. No other Glyphs
process or GUI application is targeted. Command output passes through directly.
"""

import os
import signal
import subprocess
import sys
import time


TERMINATE_GRACE_SECONDS = 2.0


def signal_group(process, signum):
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if not arguments:
        print("Usage: run_cancellable.py COMMAND [ARGUMENT ...]", file=sys.stderr)
        return 2

    cancellation = {"signal": None, "count": 0}

    def request_cancel(signum, unused_frame):
        if cancellation["signal"] is None:
            cancellation["signal"] = signum
        cancellation["count"] += 1

    signal.signal(signal.SIGINT, request_cancel)
    signal.signal(signal.SIGTERM, request_cancel)
    try:
        process = subprocess.Popen(arguments, start_new_session=True)
    except OSError as error:
        print("Could not start build step: %s" % error, file=sys.stderr)
        return 127

    while True:
        if cancellation["signal"] is not None:
            print("\nBuild cancelled; stopping %s." % arguments[0], file=sys.stderr, flush=True)
            signal_group(process, signal.SIGTERM)
            deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
            while True:
                # Reap the leader, but also check for workers remaining after it exits.
                process.poll()
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() >= deadline or cancellation["count"] > 1:
                    signal_group(process, signal.SIGKILL)
                    break
                time.sleep(0.05)
            process.wait()
            return 128 + cancellation["signal"]
        result = process.poll()
        if result is not None:
            return result if result >= 0 else 128 - result
        time.sleep(0.05)


if __name__ == "__main__":
    sys.exit(main())
