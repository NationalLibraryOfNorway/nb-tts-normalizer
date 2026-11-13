"""Conservative scientific-number syntax, not an equation evaluator.

Source facts and first-party reading/disambiguation choices: SOURCES.md.
Candidates deliberately include malformed notation so later number/date rules
cannot silently normalize fragments of a rejected expression.
"""

import re
from decimal import Decimal

from .numbers import cardinal, decimal_fraction

SPACE = r"[ \t\u00a0\u202f]*"
SUPER = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻"
TRANSLATE = str.maketrans(SUPER + "−", "0123456789+--")
NUM = r"[0-9]+(?:[.,][0-9]+)*"
EXP = rf"[+−\-⁺⁻]*(?:[0-9{SUPER}]+(?:[.,][0-9]+)*|[a-zA-Z]+)?"
# Parentheses/braces are caught but intentionally not accepted in this version.
POWER = rf"10(?:{SPACE}\^{SPACE}[({{]?{SPACE}{EXP}[)}}]?|[{SUPER}]+)"
BODY = rf"[+−-]?{NUM}(?:{SPACE}[eE](?=[+−0-9-]|$|[ \t]+[+−0-9-]){SPACE}{EXP}|{SPACE}[×·⋅*xX]{SPACE}(?:{POWER}|10[−-][0-9]+))|[+−-]?{POWER}"
CANDIDATE = rf"(?:{BODY})(?:[a-zA-Z_][\w]*)?"
VALID_SHAPE = rf"(?:[+−-]?{NUM}[eE][+−-]?[0-9]+|(?:[+−-]?{NUM}{SPACE}[×·⋅*]{SPACE})?10(?:\^[+−-]?[0-9]+|[{SUPER}]+))"


def render(raw: str, *, language: str, decimal_style: str, unit=None) -> str:
    """Read notation as written; integer exponent bounded to -999..999."""
    compact = re.sub(r"[ \t\u00a0\u202f]+", "", raw)
    machine = re.fullmatch(r"([+−-]?[0-9]+(?:[.,][0-9]+)?)[eE]([+−-]?[0-9]+)", compact)
    if machine:
        coefficient, exponent = machine.groups()
        if not any(ch in coefficient for ch in ",.") and exponent[0] not in "+−-":
            raise ValueError("unsigned integer e/E form may be an identifier")
        # Spaces inside machine notation are not a supported convention.
        if compact != raw:
            raise ValueError("whitespace inside e/E notation is ambiguous")
    else:
        display = re.fullmatch(
            rf"(?:([+−-]?[0-9]+(?:,[0-9]+)?)[×·⋅*])?10(?:\^([+−-]?[0-9]+)|([{SUPER}]+))",
            compact,
        )
        if not display:
            raise ValueError("ambiguous or unsupported scientific-number syntax")
        coefficient, normal, superscript = display.groups()
        exponent = (normal or superscript).translate(TRANSLATE)
    if not re.fullmatch(r"[+-]?[0-9]+", exponent.replace("−", "-")):
        raise ValueError("invalid scientific exponent")
    exp_digits = exponent.lstrip("+−-")
    if len(exp_digits) > 3 or (len(exp_digits) > 1 and exp_digits.startswith("0")):
        raise ValueError("scientific exponent must be -999..999 without leading zeros")
    n = int(exponent.replace("−", "-"))
    def with_unit(words: str) -> str:
        if unit is None:
            return words
        # Decimal construction is exact and bounded, including trailing zeros.
        # This comparison selects agreement only; we never expand the value.
        value = Decimal((coefficient or "1").replace(",", ".").replace("−", "-") + "E" + str(n))
        return words + " " + (unit.singular if value.copy_abs() == 1 else unit.plural)

    power = ("ti opphøgd i " if language == "nn" else "ti opphøyd i ")
    power += ("pluss " if exponent.startswith("+") else "") + cardinal(n, language=language)
    if coefficient is None:
        return with_unit(power)
    coefficient = coefficient.replace(".", ",").replace("−", "-")
    integer, comma, fraction = coefficient.partition(",")
    unsigned = integer.lstrip("+-")
    if len(unsigned + fraction) > 18 or (len(unsigned) > 1 and unsigned.startswith("0")):
        raise ValueError("scientific coefficient too long or has leading zeros")
    words = ("pluss " if integer.startswith("+") else "minus " if integer.startswith("-") else "")
    words += cardinal(int(unsigned), language=language)
    if comma:
        words += " komma " + decimal_fraction(fraction, style=decimal_style, language=language)
    return with_unit(words + (" gonger " if language == "nn" else " ganger ") + power)
