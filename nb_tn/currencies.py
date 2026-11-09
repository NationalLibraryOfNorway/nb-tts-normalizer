"""Foreign-currency amounts read in Bokmaal, with explicit input conventions.

No exchange rates, monetary conversion, floating-point arithmetic, rounding,
language identification, or runtime currency-table downloads are used.
"""

from dataclasses import dataclass
import re
from typing import Mapping

from .numbers import cardinal
from .readings import DASH, DASH_CHARS, SIGN, SIGN_CHARS


@dataclass(frozen=True)
class Currency:
    singular: str
    plural: str
    decimals: int = 2
    neuter: bool = False
    minor_singular: str | None = "cent"
    minor_plural: str | None = "cent"
    minor_neuter: bool = False


CURRENCIES = {
    "NOK": Currency("krone", "kroner", minor_singular="øre", minor_plural="øre", minor_neuter=True),
    "EUR": Currency("euro", "euro"),
    "USD": Currency("amerikansk dollar", "amerikanske dollar"),
    "GBP": Currency("britisk pund", "britiske pund", neuter=True, minor_singular="penny", minor_plural="pence"),
    "SEK": Currency("svensk krone", "svenske kroner", minor_singular="øre", minor_plural="øre", minor_neuter=True),
    "DKK": Currency("dansk krone", "danske kroner", minor_singular="øre", minor_plural="øre", minor_neuter=True),
    "CAD": Currency("kanadisk dollar", "kanadiske dollar"),
    "AUD": Currency("australsk dollar", "australske dollar"),
    "CHF": Currency("sveitsisk franc", "sveitsiske franc", minor_singular=None, minor_plural=None),
    "CNY": Currency("kinesisk yuan", "kinesiske yuan", minor_singular=None, minor_plural=None),
    "JPY": Currency("japansk yen", "japanske yen", decimals=0, minor_singular=None, minor_plural=None),
    "KWD": Currency("kuwaitisk dinar", "kuwaitiske dinarer", decimals=3, minor_singular="fils", minor_plural="fils"),
}
QUALIFIED = {"US$": "USD", "C$": "CAD", "CA$": "CAD", "A$": "AUD", "AU$": "AUD", "CN¥": "CNY", "JP¥": "JPY"}
SYMBOL_DEFAULTS = {"kr": "NOK", "kr.": "NOK", "€": "EUR", "£": "GBP", "$": None, "¥": None}
SYMBOL_FAMILIES = {"$": {"USD", "CAD", "AUD"}, "¥": {"JPY", "CNY"},
                   "kr": {"NOK", "SEK", "DKK"}, "kr.": {"NOK", "SEK", "DKK"},
                   "€": {"EUR"}, "£": {"GBP"}}
WORDS = {"euro": "EUR", "euros": "EUR", "kroner": "NOK", "krone": "NOK",
         "amerikansk dollar": "USD", "amerikanske dollar": "USD", "US dollar": "USD", "US dollars": "USD",
         "britisk pund": "GBP", "britiske pund": "GBP", "British pound": "GBP", "British pounds": "GBP",
         "svensk krone": "SEK", "svenske kroner": "SEK", "dansk krone": "DKK", "danske kroner": "DKK",
         "kanadisk dollar": "CAD", "kanadiske dollar": "CAD", "Canadian dollar": "CAD", "Canadian dollars": "CAD",
         "australsk dollar": "AUD", "australske dollar": "AUD", "Australian dollar": "AUD", "Australian dollars": "AUD"}
_WORDS = {word.casefold(): code for word, code in WORDS.items()}
_AMBIGUOUS_WORDS = {"dollar", "dollars"}
_FIXED = {**QUALIFIED, **SYMBOL_DEFAULTS}
_MARKER = ("(?:" + "|".join(re.escape(s) for s in sorted(_FIXED, key=len, reverse=True))
           + "|(?i:" + "|".join(re.escape(s).replace(r"\ ", r"[ \t]+")
                                for s in sorted((*WORDS, *_AMBIGUOUS_WORDS), key=len, reverse=True))
           + r")|[A-Z]{3}|[₹₩₽₺₴₪₫₦₱₡₲₵₸₾₼₿฿])")
_LEFT = r"(?<![\w.,:/+" + re.escape(DASH_CHARS) + r"])"
_END = r"(?!\w|[.,]\d)"
_SPACE = r"[ \t\u00a0\u202f]*"
_AMOUNT = rf"{SIGN}?(?:\d+(?:(?:[.,]+|[ \t\u00a0\u202f]+)\d+)*|[.,]\d+)(?:,-)?"


@dataclass(frozen=True)
class Amount:
    whole: int
    minor: int
    fraction: str
    negative: bool


class CurrencyPolicy:
    def __init__(self, locale: str = "nb-NO", symbol_currencies: Mapping[str, str | None] | None = None):
        if locale not in ("nb-NO", "en-US"):
            raise ValueError("currency_locale must be nb-NO or en-US")
        self.locale = locale
        self.symbols = dict(SYMBOL_DEFAULTS)
        for symbol, code in (symbol_currencies or {}).items():
            if symbol not in ("$", "¥") or code is not None and code not in SYMBOL_FAMILIES[symbol]:
                raise ValueError("unsupported currency-symbol mapping: " + repr((symbol, code)))
            self.symbols[symbol] = code

    def _code(self, marker: str) -> str:
        if marker in QUALIFIED:
            return QUALIFIED[marker]
        if marker in self.symbols:
            code = self.symbols[marker]
            if code is None:
                raise ValueError("ambiguous currency symbol; specify an ISO code or symbol_currencies: " + marker)
            return code
        word = re.sub(r"[ \t]+", " ", marker).casefold()
        if word in _AMBIGUOUS_WORDS:
            raise ValueError("unqualified dollar name needs an explicit currency code")
        if word in _WORDS:
            return _WORDS[word]
        if marker not in CURRENCIES:
            raise ValueError("unsupported currency marker or code: " + marker)
        return marker

    def _resolve(self, markers: list[str]) -> str:
        # An explicit code/qualified name disambiguates a compatible symbol:
        # $10 CAD is CAD even when the optional bare-$ default is USD.
        explicit = [self._code(m) for m in markers if m not in SYMBOL_FAMILIES
                    and m.casefold() not in _AMBIGUOUS_WORDS]
        if explicit:
            if len(set(explicit)) != 1:
                raise ValueError("conflicting currency markers")
            code = explicit[0]
            for marker in markers:
                family = SYMBOL_FAMILIES.get(marker)
                if marker.casefold() in _AMBIGUOUS_WORDS:
                    family = SYMBOL_FAMILIES["$"]
                if family is not None and code not in family:
                    raise ValueError("conflicting currency markers")
            return code
        codes = [self._code(m) for m in markers]
        if len(set(codes)) != 1:
            raise ValueError("conflicting currency markers")
        return codes[0]

    def parse(self, raw: str, code: str) -> Amount:
        text = raw.strip()
        negative = text[0] in SIGN_CHARS
        if negative:
            text = text[1:]
        if text.endswith(",-"):
            if self.locale != "nb-NO":
                raise ValueError("comma-dash amounts require currency_locale=nb-NO")
            text = text[:-2]
        decimal, grouping = (",", ".") if self.locale == "nb-NO" else (".", ",")
        fields = text.split(decimal)
        if len(fields) > 2:
            raise ValueError("multiple decimal separators in currency amount")
        integer, fraction = fields[0], fields[1] if len(fields) == 2 else ""
        if len(fields) == 2 and (not fraction or not fraction.isdecimal()):
            raise ValueError("invalid decimal currency amount for " + self.locale)
        integer = re.sub(r"[\t\u00a0\u202f]", " ", integer)
        if not integer and fraction:
            integer = "0"
        if grouping in integer and " " in integer:
            raise ValueError("mixed grouping separators in currency amount")
        separator = grouping if grouping in integer else " " if " " in integer else None
        if separator:
            groups = integer.split(separator)
            if not 1 <= len(groups[0]) <= 3 or not groups[0].isdecimal() or any(len(g) != 3 or not g.isdecimal() for g in groups[1:]):
                raise ValueError("invalid currency grouping for " + self.locale)
            integer = "".join(groups)
        if not integer.isdecimal():
            raise ValueError("invalid currency amount for " + self.locale)
        precision = CURRENCIES[code].decimals
        if len(fraction) > precision:
            raise ValueError(f"{code} supports {precision} decimal places; amount is not rounded")
        minor = int(fraction.ljust(precision, "0")) if fraction else 0
        return Amount(int(integer), minor, fraction, negative)

    def amount_words(self, amount: Amount, code: str) -> str:
        currency = CURRENCIES[code]
        major = currency.singular if amount.whole == 1 else currency.plural
        words = cardinal(amount.whole, neuter=currency.neuter)
        if amount.minor and currency.minor_singular is None:
            words += " komma " + " ".join(cardinal(int(d)) for d in amount.fraction)
            major = currency.plural
        words += " " + major
        if amount.minor and currency.minor_singular is not None:
            minor = currency.minor_singular if amount.minor == 1 else currency.minor_plural
            words += " og " + cardinal(amount.minor, neuter=currency.minor_neuter) + " " + minor
        return ("minus " if amount.negative else "") + words

    def render(self, match: re.Match) -> str:
        groups = match.groupdict()
        markers = [groups[name] for name in ("prefix", "prefix2", "suffix", "suffix2") if groups.get(name)]
        code = self._resolve(markers)
        first = self.parse(groups["first"], code)
        if groups.get("sign"):
            if first.negative:
                raise ValueError("duplicate negative signs on currency amount")
            first = Amount(first.whole, first.minor, first.fraction, True)
        if not groups.get("last"):
            return self.amount_words(first, code)
        last = self.parse(groups["last"], code)
        if not first.minor and not last.minor:
            def number(a: Amount) -> str:
                return ("minus " if a.negative else "") + cardinal(a.whole, neuter=CURRENCIES[code].neuter)
            return number(first) + " til " + number(last) + " " + CURRENCIES[code].plural
        return self.amount_words(first, code) + " til " + self.amount_words(last, code)

    def rules(self):
        first, last = rf"(?P<first>{_AMOUNT})", rf"(?P<last>{_AMOUNT})"
        prefix, suffix = rf"(?P<prefix>{_MARKER})", rf"(?P<suffix>{_MARKER})"
        boundary = r"(?!\w)"
        # Longer forms first, so ranges and paired markers own their full span.
        yield (_LEFT + first + _SPACE + suffix + boundary + _SPACE + DASH + _SPACE
               + last + _SPACE + rf"(?P<suffix2>{_MARKER})" + boundary, "currency_range")
        yield (_LEFT + rf"(?P<sign>{SIGN})?" + prefix + _SPACE + first + _SPACE + DASH + _SPACE
               + rf"(?:(?P<prefix2>{_MARKER}){_SPACE})?" + last
               + rf"(?:{_SPACE}{suffix}{boundary})?" + _END, "currency_range")
        yield (_LEFT + first + _SPACE + DASH + _SPACE + last + _SPACE + suffix + boundary, "currency_range")
        yield (_LEFT + rf"(?P<sign>{SIGN})?" + prefix + _SPACE + first
               + rf"(?:{_SPACE}{suffix}{boundary})?" + _END, "currency")
        yield (_LEFT + first + _SPACE + suffix + boundary, "currency")
