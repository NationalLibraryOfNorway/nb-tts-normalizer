"""Case-sensitive physical unit names; no numerical conversion is performed.

Names and prefixes follow SI/SSB references in SOURCES.md. A small set of
non-SI/typographic aliases is explicit, rather than lowercasing symbols.
"""

from dataclasses import dataclass
import re

from .numbers import ordinal


@dataclass(frozen=True)
class UnitReading:
    singular: str
    plural: str
    neuter: bool = False


BASE_UNITS = {
    "m": UnitReading("meter", "meter"),
    "g": UnitReading("gram", "gram", True),
    "s": UnitReading("sekund", "sekunder", True),
    "A": UnitReading("ampere", "ampere"),
    "K": UnitReading("kelvin", "kelvin"),
    "mol": UnitReading("mol", "mol", True),
    "cd": UnitReading("candela", "candela"),
    "Hz": UnitReading("hertz", "hertz"),
    "N": UnitReading("newton", "newton"),
    "Pa": UnitReading("pascal", "pascal"),
    "J": UnitReading("joule", "joule"),
    "W": UnitReading("watt", "watt"),
    "C": UnitReading("coulomb", "coulomb"),
    "V": UnitReading("volt", "volt"),
    "F": UnitReading("farad", "farad"),
    "Ω": UnitReading("ohm", "ohm"),
    "S": UnitReading("siemens", "siemens"),
    "Wb": UnitReading("weber", "weber"),
    "T": UnitReading("tesla", "tesla"),
    "H": UnitReading("henry", "henry"),
    "lm": UnitReading("lumen", "lumen"),
    "lx": UnitReading("lux", "lux"),
    "Bq": UnitReading("becquerel", "becquerel"),
    "Gy": UnitReading("gray", "gray"),
    "Sv": UnitReading("sievert", "sievert"),
    "kat": UnitReading("katal", "katal"),
    "rad": UnitReading("radian", "radianer"),
    "sr": UnitReading("steradian", "steradianer"),
    "l": UnitReading("liter", "liter"),
    "L": UnitReading("liter", "liter"),
    "Wh": UnitReading("wattime", "wattimer"),
    "Ah": UnitReading("amperetime", "amperetimer"),
    "eV": UnitReading("elektronvolt", "elektronvolt"),
    "bar": UnitReading("bar", "bar"),
}
PREFIXES = {
    "Q": "quetta", "R": "ronna", "Y": "yotta", "Z": "zetta", "E": "exa", "P": "peta",
    "T": "tera", "G": "giga", "M": "mega", "k": "kilo", "h": "hekto", "da": "deka",
    "d": "desi", "c": "centi", "m": "milli", "µ": "mikro", "μ": "mikro", "u": "mikro",
    "n": "nano", "p": "piko", "f": "femto", "a": "atto", "z": "zepto", "y": "yokto",
    "r": "ronto", "q": "quecto",
}
ALIASES = {
    "kg": UnitReading("kilo", "kilo"),  # Preserve the existing everyday reading.
    "min": UnitReading("minutt", "minutter", True),
    "h": UnitReading("time", "timer"),
    "t": UnitReading("tonn", "tonn", True),
    "d": UnitReading("døgn", "døgn", True),
    "sek": UnitReading("sekund", "sekunder", True),
    "°C": UnitReading("grad celsius", "grader celsius"),
    "°c": UnitReading("grad celsius", "grader celsius"),
    "°F": UnitReading("grad fahrenheit", "grader fahrenheit"),
    "°": UnitReading("grad", "grader"),
    "ha": UnitReading("hektar", "hektar", True),
    "daa": UnitReading("dekar", "dekar", True),
    "mil": UnitReading("mil", "mil"),
    "dB": UnitReading("desibel", "desibel"),
    "kn": UnitReading("knop", "knop"),
    "ohm": UnitReading("ohm", "ohm"),
    "stk": UnitReading("stykk", "stykker", True),
    "stk.": UnitReading("stykk", "stykker", True),
}
SPECIAL_COMPOUNDS = {
    "km/t": UnitReading("kilometer i timen", "kilometer i timen"),
    "km/h": UnitReading("kilometer i timen", "kilometer i timen"),
    "m/s": UnitReading("meter per sekund", "meter per sekund"),
}

_SUPER = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_POWER = r"(?:[ \t]*\^[ \t]*[+−-]?\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+|[23]|[−-][123])?"
_ATOM = rf"(?:stk\.|[A-Za-zµμΩΩℓ°]+){_POWER}"
# Parentheses are captured to reject the whole expression rather than reading a
# valid prefix of unsupported grouping. Implicit products (kg m-3) are not parsed.
_FACTOR = rf"(?:{_ATOM}|\([A-Za-zµμΩΩℓ°0-9²³⁻⁺^+−/·⋅∙*×. \t-]+\))"
UNIT_PATTERN = rf"{_FACTOR}(?:[ \t]*[/·⋅∙*×][ \t]*{_FACTOR})*"
UNIT_END = r"(?![\w²³⁻⁺^/·⋅∙*×]|[ \t]*[/·⋅∙*×])"
# A second, deliberately loose candidate catches malformed expressions such as
# m//s and m^ after the structured rule has had its chance. The parser still
# validates the candidate, and prose count nouns are filtered by the caller.
_RAW_FACTOR = r"[A-Za-zµμΩΩℓ°][A-Za-zµμΩΩℓ°0-9⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺^+−/·⋅∙*×()-]*"
UNKNOWN_UNIT_PATTERN = rf"{_RAW_FACTOR}(?:[ \t]*[/·⋅∙*×][ \t]*[A-Za-zµμΩΩℓ°0-9⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺^+−/·⋅∙*×()-]*)*"
_FOLDED = {s.casefold() for s in (*BASE_UNITS, *ALIASES)}
_FOLDED.update((p + base).casefold() for p in PREFIXES for base in BASE_UNITS)


def _atom(symbol: str) -> tuple[UnitReading, int]:
    symbol = symbol.replace("Ω", "Ω").replace("ℓ", "l")
    match = re.fullmatch(r"(?P<base>[A-Za-zµμΩ°]+\.?)(?P<power>.*)", symbol)
    if not match:
        raise ValueError("unsupported unit syntax")
    base = match["base"]
    power = match["power"].replace("^", "").replace("−", "-").translate(_SUPER).strip()
    if match["power"] and not power:
        raise ValueError("incomplete unit power")
    exponent = int(power) if power else 1
    if not 1 <= abs(exponent) <= 9:
        raise ValueError("unit powers outside supported ±1..±9")
    reading = ALIASES.get(base) or BASE_UNITS.get(base)
    root = base
    if reading is None:
        for prefix in sorted(PREFIXES, key=len, reverse=True):
            if base.startswith(prefix) and base[len(prefix):] in BASE_UNITS:
                root = base[len(prefix):]
                original = BASE_UNITS[root]
                reading = UnitReading(PREFIXES[prefix] + original.singular,
                                      PREFIXES[prefix] + original.plural, original.neuter)
                break
    if reading is None:
        raise ValueError("unknown or incorrectly cased unit symbol: " + symbol)
    power = abs(exponent)
    if power != 1:
        if root == "m" and power in (2, 3):
            name = ("kvadrat" if power == 2 else "kubikk") + reading.singular
        else:
            name = reading.singular + (" i kvadrat" if power == 2 else " i " + ordinal(power) + " potens")
        reading = UnitReading(name, name, reading.neuter)
    return reading, exponent


def parse_unit(symbol: str) -> UnitReading:
    normalized = re.sub(r"[ \t]+", "", symbol)
    if normalized in SPECIAL_COMPOUNDS:
        return SPECIAL_COMPOUNDS[normalized]
    if "(" in normalized or ")" in normalized:
        raise ValueError("parenthesized unit expressions need review")
    parts = re.split(r"([/·⋅∙*×])", normalized)
    numerator, denominator = [], []
    division = False
    for part in parts:
        if part in ("/", "·", "⋅", "∙", "*", "×"):
            division = part == "/"
            continue
        reading, power = _atom(part)
        (denominator if division != (power < 0) else numerator).append(reading)
    if not numerator:
        phrase = "per " + " ".join(r.singular for r in denominator)
        return UnitReading(phrase, phrase)
    def words(plural: bool) -> str:
        names = [numerator[0].plural if plural else numerator[0].singular]
        names.extend(r.singular for r in numerator[1:])
        if denominator:
            names.extend(("per", " ".join(r.singular for r in denominator)))
        return " ".join(names)
    return UnitReading(words(False), words(True), numerator[0].neuter)


def looks_like_unit(symbol: str, *, attached: bool = False) -> bool:
    """Flag symbol-shaped unknown units without treating every count noun as one."""
    if attached or symbol.casefold() in _FOLDED:
        return True
    if re.search(r"[µμΩΩℓ°²³⁻⁺^/·⋅∙*×()]", symbol):
        return True
    return symbol.isupper() or any(ch.isupper() for ch in symbol[1:])
