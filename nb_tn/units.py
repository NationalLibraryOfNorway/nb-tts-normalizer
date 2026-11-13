"""Case-sensitive physical unit names; no numerical conversion is performed.

Names and prefixes follow SI/SSB references in SOURCES.md. A small set of
non-SI/typographic aliases is explicit, rather than lowercasing symbols.
Squared non-length units follow the supplied government draft's table 3:
"i annen" (Bokmaal), adapted to "i andre" (Nynorsk); area/volume names stay
kvadrat-/kubikkmeter. This is a reading policy, not an SI definition change.
"""

from dataclasses import dataclass
import re

from .numbers import ordinal
from .profiles import get_profile


@dataclass(frozen=True)
class UnitReading:
    singular: str
    plural: str
    neuter: bool = False
    gender: str | None = None

    @property
    def number_gender(self) -> str:
        return self.gender or ("n" if self.neuter else "m")


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
    "a": UnitReading("ar", "ar", True),
    "t": UnitReading("tonn", "tonn", True),
}
PREFIXES = {
    "Q": "quetta", "R": "ronna", "Y": "yotta", "Z": "zetta", "E": "exa", "P": "peta",
    "T": "tera", "G": "giga", "M": "mega", "k": "kilo", "h": "hekto", "da": "deka",
    "d": "desi", "c": "centi", "m": "milli", "µ": "mikro", "μ": "mikro", "u": "mikro",
    "n": "nano", "p": "piko", "f": "femto", "a": "atto", "z": "zepto", "y": "yokto",
    "r": "ronto", "q": "quecto",
}
ALIASES = {
    "mins": UnitReading("minutt", "minutter", True),
    "hr": UnitReading("time", "timer"),
    "hrs": UnitReading("time", "timer"),
    "sec": UnitReading("sekund", "sekunder", True),
    "secs": UnitReading("sekund", "sekunder", True),
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
    "deg": UnitReading("grad", "grader"),
    "gon": UnitReading("gon", "gon"),
    "ar": UnitReading("ar", "ar", True),
    "mmHg": UnitReading("millimeter kvikksølv", "millimeter kvikksølv"),
    "karat": UnitReading("karat", "karat"),
    "nautisk mil": UnitReading("nautisk mil", "nautiske mil"),
    "nautiske mil": UnitReading("nautisk mil", "nautiske mil"),
    "arcmin": UnitReading("bueminutt", "bueminutter", True),
    "arcsec": UnitReading("buesekund", "buesekunder", True),
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
_POWER = r"(?:[ \t]*\^[ \t]*[+−-]?\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+|\d+|[−-]\d+)?"
_NAMED = r"nautisk(?:e)?[ \t]+mil"
_ATOM = rf"(?:{_NAMED}|stk\.|[A-Za-zµμΩΩℓ°]+){_POWER}"
_TOKEN = re.compile(_ATOM)
_GROUP_CHARS = r"[A-Za-zµμΩΩℓ°0-9⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺^+−/·⋅∙*×. \t-]"
_GROUP_CONTENT = _GROUP_CHARS + "*"
for _ in range(7):
    _GROUP_CONTENT = rf"(?:{_GROUP_CHARS}|\({_GROUP_CONTENT}\))*"
# Group powers are candidates so the parser can flag the complete unsupported
# expression instead of letting its numeric pieces fall through separately.
_FACTOR = rf"(?:{_ATOM}|\({_GROUP_CONTENT}\){_POWER})"


def _symbols_pattern(symbols) -> str:
    return "(?:" + "|".join(re.escape(s).replace(r"\ ", r"[ \t]+")
                            for s in sorted(symbols, key=len, reverse=True)) + ")"


# Only registered symbols may extend a candidate across plain whitespace.
# This prevents "5 m kabel" from being swallowed as a malformed unit product.
_KNOWN = (rf"(?:{_symbols_pattern(set(BASE_UNITS) | set(ALIASES))}|"
          rf"{_symbols_pattern(PREFIXES)}{_symbols_pattern(BASE_UNITS)}){_POWER}(?![\w°])")
UNIT_PATTERN = (rf"{_FACTOR}(?:[ \t]*[/·⋅∙*×][ \t]*{_FACTOR}|"
                rf"(?:[ \t]+\.[ \t]+|\.(?=\S)){_KNOWN}|[ \t]+{_KNOWN})*")
UNIT_END = r"(?![\w²³⁻⁺^/·⋅∙*×]|[ \t]*[/·⋅∙*×])"
# A second, deliberately loose candidate catches malformed expressions such as
# m//s and m^ after the structured rule has had its chance. The parser still
# validates the candidate, and prose count nouns are filtered by the caller.
_RAW_FACTOR = r"[A-Za-zµμΩΩℓ°(][A-Za-zµμΩΩℓ°0-9⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺^+−/·⋅∙*×()-]*"
UNKNOWN_UNIT_PATTERN = rf"{_RAW_FACTOR}(?:[ \t]*[/·⋅∙*×][ \t]*[A-Za-zµμΩΩℓ°0-9⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺^+−/·⋅∙*×()-]*)*"
_FOLDED = {s.casefold() for s in (*BASE_UNITS, *ALIASES)}
_FOLDED.update((p + base).casefold() for p in PREFIXES for base in BASE_UNITS)


def _atom(symbol: str, language: str = "nb") -> tuple[UnitReading, int]:
    profile = get_profile(language)
    symbol = symbol.replace("Ω", "Ω").replace("ℓ", "l")
    match = re.fullmatch(rf"(?P<base>{_NAMED}|[A-Za-zµμΩ°]+\.?)(?P<power>.*)", symbol)
    if not match:
        raise ValueError("unsupported unit syntax")
    base = re.sub(r"[ \t]+", " ", match["base"])
    power = match["power"].replace("^", "").replace("−", "-").translate(_SUPER).strip()
    if match["power"] and not power:
        raise ValueError("incomplete unit power")
    exponent = int(power) if power else 1
    if not 1 <= abs(exponent) <= 9:
        raise ValueError("unit powers outside supported ±1..±9")
    reading = ALIASES.get(base) or BASE_UNITS.get(base)
    if base in profile.unit_forms:
        singular, plural, gender = profile.unit_forms[base]
        reading = UnitReading(singular, plural, gender == "n", gender)
    root = base
    if reading is None:
        for prefix in sorted(PREFIXES, key=len, reverse=True):
            if base.startswith(prefix) and base[len(prefix):] in BASE_UNITS:
                root = base[len(prefix):]
                original = BASE_UNITS[root]
                if root in profile.unit_forms:
                    singular, plural, gender = profile.unit_forms[root]
                    original = UnitReading(singular, plural, gender == "n", gender)
                reading = UnitReading(PREFIXES[prefix] + original.singular,
                                      PREFIXES[prefix] + original.plural, original.neuter, original.gender)
                break
    if reading is None:
        raise ValueError("unknown or incorrectly cased unit symbol: " + symbol)
    power = abs(exponent)
    if power != 1:
        if root == "m" and power in (2, 3):
            name = ("kvadrat" if power == 2 else "kubikk") + reading.singular
        else:
            name = reading.singular + (" i " + profile.squared_unit_ordinal if power == 2
                                       else " i " + ordinal(power, language=language) + " potens")
        reading = UnitReading(name, name, reading.neuter, reading.gender)
    return reading, exponent


def parse_unit(symbol: str, *, language: str = "nb", english_unit_aliases: bool = False) -> UnitReading:
    get_profile(language)
    if not isinstance(english_unit_aliases, bool):
        raise ValueError("english_unit_aliases must be a bool")
    if not english_unit_aliases and any(token in {"mins", "hr", "hrs", "sec", "secs"}
                                       for token in re.findall(r"[A-Za-zµμΩΩℓ°]+", symbol)):
        raise ValueError("English time-unit alias requires english_unit_aliases=True")
    normalized = re.sub(r"[ \t]+", "", symbol)
    if normalized in SPECIAL_COMPOUNDS:
        return SPECIAL_COMPOUNDS[normalized]
    if len(symbol) > 512:
        raise ValueError("unit expression exceeds 512 characters")
    position = 0
    factor_count = 0

    def whitespace() -> bool:
        nonlocal position
        start = position
        while position < len(symbol) and symbol[position] in " \t":
            position += 1
        return position > start

    def factor(depth: int) -> list[tuple[UnitReading, int]]:
        nonlocal position, factor_count
        whitespace()
        if position >= len(symbol):
            raise ValueError("missing unit factor")
        if symbol[position] == "(":
            if depth >= 8:
                raise ValueError("unit grouping exceeds depth 8")
            position += 1
            result = expression(depth + 1)
            if position >= len(symbol) or symbol[position] != ")":
                raise ValueError("unbalanced unit group")
            position += 1
            return result
        match = _TOKEN.match(symbol, position)
        if match is None:
            raise ValueError("invalid unit factor")
        position = match.end()
        factor_count += 1
        if factor_count > 64:
            raise ValueError("unit expression exceeds 64 factors")
        return [_atom(match[0], language)]

    def expression(depth: int) -> list[tuple[UnitReading, int]]:
        nonlocal position
        result = factor(depth)
        while position < len(symbol):
            spaced = whitespace()
            if position >= len(symbol) or symbol[position] == ")":
                break
            operator = symbol[position]
            if operator in "/·⋅∙*×.":
                position += 1
            elif spaced and _TOKEN.match(symbol, position):
                operator = "*"
            else:
                raise ValueError("unsupported unit operator or group power")
            following = factor(depth)
            result.extend((reading, -power if operator == "/" else power) for reading, power in following)
        return result

    factors = expression(0)
    whitespace()
    if position != len(symbol):
        raise ValueError("unbalanced unit group")
    numerator, denominator = [], []
    for reading, power in factors:
        (denominator if power < 0 else numerator).append(reading)
    if not numerator:
        phrase = "per " + " ".join(r.singular for r in denominator)
        return UnitReading(phrase, phrase)
    def words(plural: bool) -> str:
        names = [numerator[0].plural if plural else numerator[0].singular]
        names.extend(r.singular for r in numerator[1:])
        if denominator:
            names.extend(("per", " ".join(r.singular for r in denominator)))
        return " ".join(names)
    return UnitReading(words(False), words(True), numerator[0].neuter, numerator[0].gender)


def looks_like_unit(symbol: str, *, attached: bool = False) -> bool:
    """Flag symbol-shaped unknown units without treating every count noun as one."""
    if attached or symbol.casefold() in _FOLDED:
        return True
    if re.search(r"[µμΩΩℓ°²³⁻⁺^/·⋅∙*×()]", symbol):
        return True
    # A known implicit product that exceeds parser bounds must still own its
    # complete source span; it must not fall back to its first valid factor.
    if re.fullmatch(rf"{_KNOWN}(?:[ \t]+{_KNOWN})+", symbol):
        return True
    return symbol.isupper() or any(ch.isupper() for ch in symbol[1:])
