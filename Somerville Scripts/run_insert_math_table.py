#MenuTitle: Insert Math Table to Variable Font
# -*- coding: utf-8 -*-

#!/usr/bin/env python3

import subprocess


def main():
    result = subprocess.run(
        ["/Users/juliusross/Documents/mathtestingtool/insertmathtable.sh"],
        cwd="/Users/juliusross/Documents/mathtestingtool",
        capture_output=True,
        text=True,
    )

    print("Return code:", result.returncode)

    if result.stdout:
        print("\n=== STDOUT ===")
        print(result.stdout)

    if result.stderr:
        print("\n=== STDERR ===")
        print(result.stderr)


if __name__ == "__main__":
    main()
