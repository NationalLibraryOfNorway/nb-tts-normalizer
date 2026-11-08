"""Legal citation structure: a chapter separator is not a range separator."""

import re

from .numbers import cardinal, ordinal
from .readings import DASH, letter

# Attached letters are section suffixes; spaced i is usually the preposition i.
SECTION = (rf"\d+(?:[ \t]*{DASH}[ \t]*\d+|[ \t]*\.[ \t]*\d+)*"
           r"(?:[a-zæøå](?!\w)|[ \t]+[a-hj-zæøå](?!\w))?(?!\d|\.[ \t]*(?:ledd|punktum)\b)")
LEGAL_PATTERN = (rf"(?P<sign>§{{1,2}})[ \t]*(?P<refs>{SECTION}"
                 rf"(?:[ \t]*(?:til\b|og\b|eller\b|,)[ \t]*{SECTION})*)"
                 r"(?:[ \t]*\([ \t]*(?P<sub>\d+)[ \t]*\)"
                 r"(?:[ \t]*\([ \t]*(?P<letter>[a-zæøå])[ \t]*\))?)?")


def _section(text: str) -> str:
    parts = re.findall(r"\d+|[a-zæøå]", text.lower())
    return " ".join(cardinal(int(p)) if p.isdecimal() else letter(p) for p in parts)


def legal_reference(match: re.Match) -> str:
    plural = match["sign"] == "§§"
    pieces = re.split(r"(\b(?:til|og|eller)\b|,)", match["refs"], flags=re.I)
    sections = [p.strip() for p in pieces if p.strip() and p.strip().lower() not in ("til", "og", "eller", ",")]
    path_list = len(sections) > 1 and all(re.fullmatch(rf"\d+\s*{DASH}\s*\d+[a-zæøå]?", p, re.I) for p in sections)
    words = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if piece.lower() in ("til", "og", "eller", ","):
            words.append(piece.lower())
            continue
        if plural:
            # §§ 3-4 means a range, whereas §§ 3-4 til 3-7 contains two
            # chapter/section paths. An explicit til makes that unambiguous.
            explicit = path_list or bool(re.search(r"\btil\b", match["refs"], re.I))
            compound_range = re.fullmatch(r"(.+?\d)\s*[–—]\s*(\d.+)", piece)
            if compound_range and re.search(r"[-‐‑]", compound_range[1]) and re.search(r"[-‐‑]", compound_range[2]):
                words.append(_section(compound_range[1]) + " til " + _section(compound_range[2]))
                continue
            if not explicit and re.fullmatch(rf"\d+\s*{DASH}\s*\d+", piece):
                first, last = re.split(DASH, piece)
                words.append(cardinal(int(first)) + " til " + cardinal(int(last)))
                continue
            if not explicit and len(re.findall(DASH, piece)) > 1:
                raise ValueError("ambiguous compound section range; use explicit til")
        words.append(_section(piece))
    result = ("paragrafene " if plural else "paragraf ") + " ".join(words).replace(" ,", ",")
    if match["sub"]:
        result += " " + ordinal(int(match["sub"])) + " ledd"
    if match["letter"]:
        result += " bokstav " + letter(match["letter"])
    return result
