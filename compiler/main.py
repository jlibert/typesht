# compiler/main.py
# CLI entry point for the TypeSht compiler (development / test-runner version)

import argparse
import sys
import os

# ---------------------------------------------------------------------------
# When running from the repo root the compiler/ directory is on the path,
# so we import the sibling modules directly (no package prefix).
# ---------------------------------------------------------------------------
try:
    from lexer   import lex
    from parser  import parse
    from codegen import generate
except ImportError:
    # Fallback: running as part of the installed src/typesht package
    from .lexer   import lex
    from .parser  import parse
    from .codegen import generate


def compile_file(source_path: str, target: str, output_dir: str | None) -> None:
    """Read *source_path*, compile it, and write output files."""
    with open(source_path, "r", encoding="utf-8") as fh:
        source = fh.read()

    tokens = lex(source)
    ast    = parse(tokens)
    ts_code = generate(ast)

    # Resolve output directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(source_path)), "output")
    os.makedirs(output_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(source_path))[0]

    if target in ("ts", "both"):
        ts_path = os.path.join(output_dir, base + ".ts")
        with open(ts_path, "w", encoding="utf-8") as fh:
            fh.write(ts_code)
        print(f"Wrote {ts_path}")

    if target in ("js", "both"):
        js_path = os.path.join(output_dir, base + ".js")
        # Emit JS: strip TypeScript type annotations via a lightweight pass,
        # or write the TS source and note that tsc is needed.
        # For now we emit the TS source with a header comment; users run tsc.
        js_header = "// Run: tsc --target ES2020 --module ESNext this file\n"
        with open(js_path, "w", encoding="utf-8") as fh:
            fh.write(js_header + ts_code)
        print(f"Wrote {js_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="typesht",
        description="TypeSht compiler — compile .tsht files to TypeScript/JavaScript",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # typesht compile <file> [--target ts|js|both] [--output DIR]
    compile_cmd = sub.add_parser("compile", help="Compile a .tsht source file")
    compile_cmd.add_argument("source", help="Path to the .tsht source file")
    compile_cmd.add_argument(
        "--target",
        choices=["ts", "js", "both"],
        default="js",
        help="Output target (default: js)",
    )
    compile_cmd.add_argument(
        "--output",
        metavar="DIR",
        default=None,
        help="Output directory (default: output/ next to source file)",
    )

    args = parser.parse_args()

    if args.command == "compile":
        if not os.path.isfile(args.source):
            print(f"Error: file not found: {args.source}", file=sys.stderr)
            sys.exit(1)
        compile_file(args.source, args.target, args.output)


if __name__ == "__main__":
    main()