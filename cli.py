"""Command-line interface: property JSON in, MP4 out.

Example:
    python cli.py samples/sample_property.json -o output/skyline.mp4
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from propvid.config import RenderOptions
from propvid.errors import InputError
from propvid.pipeline import generate_video

EXIT_OK, EXIT_UNEXPECTED, EXIT_INPUT = 0, 1, 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a short property promo video (MP4) from a JSON file.")
    p.add_argument("input", help="Path to the property JSON file (image paths are relative to it)")
    p.add_argument("-o", "--output", help="Output MP4 path (default: output/<input-name>.mp4)")
    p.add_argument("--horizontal", action="store_true", help="1280x720 landscape instead of 720x1280 vertical")
    p.add_argument("--no-voice", action="store_true", help="Disable text-to-speech narration")
    p.add_argument("--no-music", action="store_true", help="Disable background music")
    p.add_argument("--ai", action="store_true", help="Write the script with Claude (needs ANTHROPIC_API_KEY)")
    p.add_argument("--fps", type=int, help="Frames per second (default 24)")
    p.add_argument("--debug", action="store_true", help="Show full tracebacks for unexpected errors")
    return p.parse_args(argv)


def _progress_printer():
    last = {"label": None}

    def report(fraction: float, label: str) -> None:
        stage = label.split(" (")[0]
        if stage != last["label"]:
            print(f"  [{fraction:4.0%}] {stage}...", flush=True)
            last["label"] = stage

    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        # Windows consoles may not support characters like "₹": never crash on printing them,
        # and write proper UTF-8 when output is redirected to a file
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding=None if stream.isatty() else "utf-8", errors="replace")
    in_path = Path(args.input)
    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Error: input file not found: {in_path}", file=sys.stderr)
        return EXIT_INPUT
    except json.JSONDecodeError as exc:
        print(f"Error: {in_path} is not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}", file=sys.stderr)
        return EXIT_INPUT

    output = Path(args.output) if args.output else Path("output") / f"{in_path.stem}.mp4"
    options = RenderOptions(
        orientation="horizontal" if args.horizontal else "vertical",
        narration=not args.no_voice,
        music=not args.no_music,
        use_ai=args.ai,
    )
    if args.fps:
        options.fps = max(12, min(60, args.fps))

    print(f"Generating video from {in_path} ...")
    started = time.perf_counter()
    try:
        result = generate_video(data, output, options, base_dir=in_path.parent, progress=_progress_printer())
    except InputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except Exception as exc:  # noqa: BLE001 - last line of defence for the CLI
        if args.debug:
            traceback.print_exc()
        print(f"Unexpected error: {exc}. Re-run with --debug for details.", file=sys.stderr)
        return EXIT_UNEXPECTED

    for warning in result.warnings:
        print(f"  Warning: {warning}")
    print(f"\nScript ({result.script.source}):")
    for i, scene in enumerate(result.script.scenes, 1):
        spoken = f'  "{scene.narration}"' if scene.narration else ""
        print(f"  {i}. [{scene.kind:7}] {scene.duration:4.1f}s  {scene.caption}{spoken}")
    print(f"\nSaved {result.output_path} ({result.duration:.1f}s) in {time.perf_counter() - started:.0f}s")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
