"""Small arithmetic verbalizer; no ASR, NLTK, or neural dependencies.

See SOURCES.md for the NbAiLab converter inspected during development.
This implementation uses its own group-based algorithm and a fixed Bokmaal policy.
"""

ONES = ("null", "en", "to", "tre", "fire", "fem", "seks", "sju", "åtte", "ni",
        "ti", "elleve", "tolv", "tretten", "fjorten", "femten", "seksten", "sytten",
        "atten", "nitten")
TENS = ("", "", "tjue", "tretti", "førti", "femti", "seksti", "sytti", "åtti", "nitti")
ORDINALS = ("", "første", "andre", "tredje", "fjerde", "femte", "sjette", "sjuende",
            "åttende", "niende", "tiende", "ellevte", "tolvte", "trettende",
            "fjortende", "femtende", "sekstende", "syttende", "attende", "nittende",
            "tjuende", "tjueførste", "tjueandre", "tjuetredje", "tjuefjerde",
            "tjuefemte", "tjuesjette", "tjuesjuende", "tjueåttende", "tjueniende",
            "trettiende", "trettiførste")
MAX_INTEGER = 10**12 - 1


def cardinal(number: int, *, neuter: bool = False) -> str:
    """Verbalize signed integers up to 999,999,999,999 (inclusive)."""
    if type(number) is not int or abs(number) > MAX_INTEGER:
        raise ValueError("integer outside supported range")
    if number < 0:
        return "minus " + cardinal(-number, neuter=neuter)
    if number < 20:
        return "ett" if number == 1 and neuter else ONES[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return TENS[tens] + (cardinal(ones, neuter=neuter) if ones else "")
    if number < 1000:
        hundreds, rest = divmod(number, 100)
        prefix = (cardinal(hundreds) + " " if hundreds > 1 else "") + "hundre"
        return prefix + (" og " + cardinal(rest, neuter=neuter) if rest else "")
    for scale, singular, plural in ((10**9, "milliard", "milliarder"),
                                    (10**6, "million", "millioner"),
                                    (1000, "tusen", "tusen")):
        if number >= scale:
            groups, rest = divmod(number, scale)
            prefix = cardinal(groups, neuter=scale == 1000) + " "
            prefix += singular if groups == 1 else plural
            if not rest:
                return prefix
            return prefix + (" og " if rest < 100 else " ") + cardinal(rest, neuter=neuter)
    raise AssertionError("unreachable")


def ordinal(number: int) -> str:
    """Ordinal forms for dates, legal subdivisions, and numbered references."""
    if not 1 <= number <= 9999:
        raise ValueError("ordinal outside 1..9999")
    if number < len(ORDINALS):
        return ORDINALS[number]
    if number < 100:
        tens, rest = divmod(number, 10)
        return TENS[tens] + ordinal(rest) if rest else TENS[tens] + "ende"
    scale, word = (1000, "tusen") if number >= 1000 else (100, "hundre")
    groups, rest = divmod(number, scale)
    prefix = (cardinal(groups) + " " if groups > 1 else "") + word
    return prefix + " og " + ordinal(rest) if rest else prefix + "de"


def year(number: int) -> str:
    if not 1 <= number <= 9999:
        raise ValueError("year outside 1..9999")
    if 1100 <= number <= 1999:
        century, rest = divmod(number, 100)
        if not rest:
            return cardinal(century) + " hundre"
        return cardinal(century) + (" null " if rest < 10 else " ") + cardinal(rest)
    return cardinal(number)
