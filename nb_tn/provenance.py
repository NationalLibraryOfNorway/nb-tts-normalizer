"""Audit the shipped Nynorsk provenance record; networking is opt-in only.

Hashes establish byte identity, not authorship, linguistic correctness, or
continued availability of an upstream URL. See SOURCES.md for those limits.
"""

import argparse
import hashlib
from importlib.resources import files
import json
from pathlib import PurePosixPath
import re
import urllib.error
import urllib.request


def load_manifest() -> dict:
    return json.loads(files("nb_tn").joinpath("provenance.json").read_text(encoding="utf-8"))


def verify_provenance(manifest: dict | None = None, *, fetch: bool = False) -> list[str]:
    """Return audit errors; never refresh hashes or silently update references."""
    manifest = load_manifest() if manifest is None else manifest
    errors = []
    if manifest.get("schema_version") != 1:
        errors.append("unsupported provenance schema")
    sources = manifest.get("sources", {})
    artifacts = manifest.get("artifacts", {})
    if not sources or not artifacts:
        errors.append("provenance must contain sources and artifacts")
    digest_pattern = r"[0-9a-f]{64}"
    for name, source in sources.items():
        if not source.get("url", "").startswith("https://") or not source.get("role") or not source.get("accessed"):
            errors.append("incomplete source reference: " + name)
        digest = source.get("sha256")
        if digest is not None and not re.fullmatch(digest_pattern, digest):
            errors.append("invalid source digest: " + name)
        if not fetch or digest is None:
            continue
        try:
            # Documents are inspected in memory, not vendored or used at runtime.
            with urllib.request.urlopen(source["url"], timeout=30) as response:
                data = response.read(10 * 1024 * 1024 + 1)
            if len(data) != source.get("bytes") or hashlib.sha256(data).hexdigest() != digest:
                errors.append("upstream content changed: " + name)
        except (OSError, urllib.error.URLError, ValueError) as error:
            errors.append(f"cannot verify {name}: {error}")
    for name, artifact in artifacts.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
            errors.append("invalid package artifact path: " + name)
            continue
        if (not artifact.get("origin") or not artifact.get("sources")
                or not set(artifact["sources"]).issubset(sources)):
            errors.append("incomplete artifact provenance: " + name)
        if not re.fullmatch(digest_pattern, artifact.get("sha256", "")):
            errors.append("invalid artifact digest: " + name)
            continue
        try:
            data = files("nb_tn").joinpath(name).read_bytes()
        except (OSError, ValueError) as error:
            errors.append(f"cannot read {name}: {error}")
            continue
        if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            errors.append("artifact changed without provenance update: " + name)
    return errors


def main():
    parser = argparse.ArgumentParser(description="Verify the shipped Nynorsk provenance record")
    parser.add_argument("--fetch", action="store_true",
                        help="Also fetch hash-recorded references; other source URLs remain reference-only")
    args = parser.parse_args()
    errors = verify_provenance(fetch=args.fetch)
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    print("Nynorsk provenance verified" + (" (including hash-recorded upstream references)" if args.fetch else " (offline)"))


if __name__ == "__main__":
    main()
