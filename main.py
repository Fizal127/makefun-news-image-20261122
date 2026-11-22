# main.py -- entrypoint: draws the front page and writes entry.png.
# Output goes to /output/entry.png when that directory exists (the grader's
# writable directory), otherwise to ./output/entry.png next to this file.
import os

import main_src


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = "/output" if os.path.isdir("/output") else os.path.join(here, "output")
    os.makedirs(outdir, exist_ok=True)
    main_src.render(os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()
