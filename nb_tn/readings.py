"""Spoken readings shared by the structured-notation rules.

Sprakradet references and application-specific disambiguation policies are
recorded in SOURCES.md. These helpers do not modify source text or offsets.
"""

import re

from .numbers import cardinal

# Unicode hyphens/dashes (Pd), plus soft hyphen and the mathematical minus sign.
# They are interpreted as ranges only between numeric endpoints, after date,
# phone, legal, and version notation has claimed its source spans.
DASH_CHARS = "-\u00ad֊־᐀᠆‐‑‒–—―⸗⸚⸺⸻⹀⹝〜〰゠︱︲﹘﹣－𐺭−"
DASH = "[" + re.escape(DASH_CHARS) + "]"
SIGN_CHARS = "-−﹣－"
SIGN = "[" + re.escape(SIGN_CHARS) + "]"
LETTERS = dict(zip("abcdefghijklmnopqrstuvwxyzæøå", (
    "a", "be", "se", "de", "e", "eff", "ge", "hå", "i", "jådd", "kå", "ell",
    "emm", "enn", "o", "pe", "ku", "err", "ess", "te", "u", "ve", "dobbeltve",
    "eks", "y", "sett", "æ", "ø", "å")))
VULGAR_FRACTIONS = {
    "½": (1, 2), "¼": (1, 4), "¾": (3, 4), "⅐": (1, 7), "⅑": (1, 9), "⅒": (1, 10),
    "⅓": (1, 3), "⅔": (2, 3), "⅕": (1, 5), "⅖": (2, 5), "⅗": (3, 5), "⅘": (4, 5),
    "⅙": (1, 6), "⅚": (5, 6), "⅛": (1, 8), "⅜": (3, 8), "⅝": (5, 8), "⅞": (7, 8),
    "↉": (0, 3),
}


def letter(text: str) -> str:
    return LETTERS[text.lower()]


def digits(text: str) -> str:
    return " ".join(cardinal(int(d)) for d in text if d.isdecimal())


def fraction(numerator: int, denominator: int, *, whole: int | None = None,
             negative: bool = False, neuter: bool = False) -> str:
    if denominator <= 0 or numerator < 0 or whole is not None and whole < 0:
        raise ValueError("fraction needs a nonnegative numerator and a positive denominator")
    if denominator == 2 and numerator == 1:
        words = "ett halvt" if neuter else "en halv"
    elif denominator == 1:
        words = cardinal(numerator) + " over en"
    else:
        name = {2: "halv", 100: "hundre", 1000: "tusen"}.get(denominator)
        if name is None:
            name = cardinal(denominator).replace(" ", "")
        words = cardinal(numerator) + " " + name + ("del" if numerator == 1 else "deler")
    if whole is not None:
        words = cardinal(whole) + " og " + words
    return ("minus " if negative else "") + words


def roman(text: str) -> int:
    if not text or not re.fullmatch(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", text.upper()):
        raise ValueError("invalid Roman enumeration")
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    numbers = [values[ch] for ch in text.upper()]
    return sum(-n if i + 1 < len(numbers) and n < numbers[i + 1] else n for i, n in enumerate(numbers))


def version(text: str, *, prefix: bool = False) -> str:
    """Read components without collapsing version separators into decimals."""
    text = text.lstrip("vV")
    tokens = re.findall(r"\d+|[a-zA-Z]+|[.+-]", text)
    words = []
    names = {"alpha": "alfa", "beta": "beta", "rc": "err se", "build": "bygg"}
    for token in tokens:
        if token.isdecimal():
            words.append(digits(token) if len(token) > 1 and token.startswith("0") else cardinal(int(token)))
        elif token == ".":
            words.append("punkt")
        elif token == "+":
            words.append("pluss")
        elif token == "-":
            continue  # Release-stage separator: e.g. "tre beta punkt to".
        else:
            words.append(names.get(token.lower(), " ".join(letter(ch) for ch in token)))
    return ("versjon " if prefix else "") + " ".join(words)
