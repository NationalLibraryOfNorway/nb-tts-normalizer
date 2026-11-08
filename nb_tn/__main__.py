import argparse
from dataclasses import asdict
import json
import sys

from .normalizer import NorwegianNormalizer


def main():
    parser = argparse.ArgumentParser(description="Normalize Bokmaal text for TTS")
    parser.add_argument("text", nargs="?", help="Text, or read stdin if omitted")
    parser.add_argument("--json", action="store_true", help="Include original spans and review issues")
    parser.add_argument("--strict", action="store_true", help="Exit 2 without emitting text if review is needed")
    args = parser.parse_args()
    result = NorwegianNormalizer().analyze(args.text if args.text is not None else sys.stdin.read())
    if args.json:
        print(json.dumps({**asdict(result), "needs_review": result.needs_review}, ensure_ascii=False, indent=2))
    elif not (args.strict and result.needs_review):
        print(result.text)
    if result.needs_review and not args.json:
        for issue in result.issues:
            print(f"Review [{issue.start}:{issue.end}] {issue.original!r}: {issue.reason}", file=sys.stderr)
    if args.strict and result.needs_review:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
