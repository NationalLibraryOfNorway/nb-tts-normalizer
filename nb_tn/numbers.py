"""Small arithmetic verbalizer; no ASR, NLTK, or neural dependencies.

See SOURCES.md for the NbAiLab converter inspected during development.
This implementation uses its own group-based algorithm and explicit language profiles.
"""

from .profiles import NB, get_profile

ONES = NB.ones
TENS = ("", "", "tjue", "tretti", "førti", "femti", "seksti", "sytti", "åtti", "nitti")
ORDINALS = NB.ordinals
MAX_INTEGER = 10**12 - 1
DECIMAL_STYLES = ("natural", "digits")


def cardinal(number: int, *, neuter: bool = False, gender: str | None = None,
             language: str = "nb") -> str:
    """Verbalize signed integers up to 999,999,999,999 (inclusive)."""
    profile = get_profile(language)
    gender = gender if gender is not None else "n" if neuter else "m"
    if gender not in ("m", "f", "n"):
        raise ValueError("gender must be m, f or n")
    if type(number) is not int or abs(number) > MAX_INTEGER:
        raise ValueError("integer outside supported range")
    if number < 0:
        return "minus " + cardinal(-number, gender=gender, language=language)
    if number < 20:
        if number == 1:
            return ({"m": "ein", "f": "ei", "n": "eitt"} if language == "nn"
                    else {"m": "en", "f": "en", "n": "ett"})[gender]
        return profile.ones[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return TENS[tens] + (cardinal(ones, gender=gender, language=language) if ones else "")
    if number < 1000:
        hundreds, rest = divmod(number, 100)
        prefix = (cardinal(hundreds, language=language) + " " if hundreds > 1 else "") + "hundre"
        return prefix + (" og " + cardinal(rest, gender=gender, language=language) if rest else "")
    for scale, singular, plural in ((10**9, "milliard", profile.billion_plural),
                                    (10**6, "million", profile.million_plural),
                                    (1000, "tusen", "tusen")):
        if number >= scale:
            groups, rest = divmod(number, scale)
            prefix = cardinal(groups, neuter=scale == 1000, language=language) + " "
            prefix += singular if groups == 1 else plural
            if not rest:
                return prefix
            return prefix + (" og " if rest < 100 else " ") + cardinal(rest, gender=gender, language=language)
    raise AssertionError("unreachable")


def decimal_fraction(fraction: str, *, style: str = "natural", language: str = "nb") -> str:
    """Read fractional digits without losing leading zeros or precision.

    Everyday speech groups exactly two digits (10..99); technical speech
    always reads each digit. Neither policy changes the supplied digits.
    """
    get_profile(language)
    if style not in DECIMAL_STYLES:
        raise ValueError("decimal_style must be natural or digits")
    if style == "natural" and len(fraction) == 2 and int(fraction[0]) != 0:
        return cardinal(int(fraction), language=language)
    return " ".join(cardinal(int(d), language=language) for d in fraction)


def ordinal(number: int, *, language: str = "nb") -> str:
    """Ordinal forms for dates, legal subdivisions, and numbered references."""
    profile = get_profile(language)
    if not 1 <= number <= 9999:
        raise ValueError("ordinal outside 1..9999")
    if number < len(profile.ordinals):
        return profile.ordinals[number]
    if number < 100:
        tens, rest = divmod(number, 10)
        return TENS[tens] + ordinal(rest, language=language) if rest else TENS[tens] + profile.ordinal_ending
    scale, word = (1000, "tusen") if number >= 1000 else (100, "hundre")
    groups, rest = divmod(number, scale)
    prefix = (cardinal(groups, language=language) + " " if groups > 1 else "") + word
    return prefix + " og " + ordinal(rest, language=language) if rest else prefix + "de"


def year(number: int, *, language: str = "nb", style: str = "pairs") -> str:
    get_profile(language)
    if style not in ("pairs", "traditional"):
        raise ValueError("year_style must be pairs or traditional")
    if not 1 <= number <= 9999:
        raise ValueError("year outside 1..9999")
    # Project cutoff: retain familiar cardinal readings for 2000–2009;
    # short paired readings resume at 2010. NRK supports the short form,
    # but the exact cutoff is our policy, not an NRK mandate.
    if 2000 <= number <= 2009:
        return cardinal(number, language=language)
    if (1000 <= number <= 9999 if style == "pairs" else 1100 <= number <= 1999):
        century, rest = divmod(number, 100)
        if not rest:
            return cardinal(century, language=language) + " hundre"
        return cardinal(century, language=language) + (" null " if rest < 10 else " ") + cardinal(rest, language=language)
    return cardinal(number, language=language)
