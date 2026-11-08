"""Bokmaal orthography -> spoken text, with auditable original-text spans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Callable, Mapping

from .numbers import cardinal, ordinal, year
from .legal import LEGAL_PATTERN, legal_reference
from .readings import (DASH, DASH_CHARS, SIGN, SIGN_CHARS, VULGAR_FRACTIONS,
                       digits, fraction, letter, roman, version)

INTEGER = r"(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+)"
NUMBER = rf"{SIGN}?{INTEGER}(?:,\d+)?"
AMOUNT = rf"{SIGN}?(?:\d{{1,3}}(?:\.\d{{3}})+|{INTEGER})(?:,\d+|,-)?"
LEFT = r"(?<![\w.,+" + re.escape(DASH_CHARS) + r"])"
RIGHT = r"(?!\w|[.,]\d)"
MONTHS = ("januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
          "september", "oktober", "november", "desember")
MONTH_ALIASES = dict(zip(MONTHS, range(1, 13)))
MONTH_ALIASES.update(dict(zip(("jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "okt", "nov", "des"),
                                  (1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12))))
MONTH_ALIASES["sept"] = 9
MONTH_PATTERN = "(?:" + "|".join(sorted(MONTH_ALIASES, key=len, reverse=True)) + ")"
UNITS = {
    "km/t": ("kilometer i timen", "kilometer i timen"),
    "m/s": ("meter per sekund", "meter per sekund"),
    "km": ("kilometer", "kilometer"), "cm": ("centimeter", "centimeter"),
    "mm": ("millimeter", "millimeter"), "m": ("meter", "meter"),
    "m²": ("kvadratmeter", "kvadratmeter"), "m³": ("kubikkmeter", "kubikkmeter"),
    "m2": ("kvadratmeter", "kvadratmeter"), "m3": ("kubikkmeter", "kubikkmeter"),
    "cm²": ("kvadratcentimeter", "kvadratcentimeter"), "cm2": ("kvadratcentimeter", "kvadratcentimeter"),
    "cm³": ("kubikkcentimeter", "kubikkcentimeter"), "cm3": ("kubikkcentimeter", "kubikkcentimeter"),
    "kg": ("kilo", "kilo"), "g": ("gram", "gram"),
    "mg": ("milligram", "milligram"), "µg": ("mikrogram", "mikrogram"), "μg": ("mikrogram", "mikrogram"),
    "ml": ("milliliter", "milliliter"), "dl": ("desiliter", "desiliter"),
    "l": ("liter", "liter"), "min": ("minutt", "minutter"),
    "sek": ("sekund", "sekunder"), "°c": ("grad celsius", "grader celsius"),
    "stk.": ("stykk", "stykker"), "stk": ("stykk", "stykker"),
}
UNIT_PATTERN = "(?:" + "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True)) + ")"
ABBREVIATIONS = {
    "f.eks.": "for eksempel", "bl.a.": "blant annet", "jf.": "jamfør",
    "ca.": "cirka", "osv.": "og så videre", "m.m.": "med mer",
    "tlf.": "telefon", "nr.": "nummer", "kap.": "kapittel", "pkt.": "punkt",
    "art.": "artikkel", "bokst.": "bokstav", "pga.": "på grunn av", "dvs.": "det vil si",
}
ACRONYMS = {"NAV": "nav", "NRK": "enn err kå", "USA": "u ess a",
            "EU": "e u", "EØS": "e ø ess"}


@dataclass(frozen=True)
class Replacement:
    start: int
    end: int
    original: str
    spoken: str
    category: str


@dataclass(frozen=True)
class Issue:
    start: int
    end: int
    original: str
    reason: str


@dataclass(frozen=True)
class NormalizationResult:
    original: str
    text: str
    replacements: tuple[Replacement, ...]
    issues: tuple[Issue, ...]

    @property
    def needs_review(self) -> bool:
        return bool(self.issues)


def _integer(text: str) -> int:
    if text and text[0] in SIGN_CHARS:
        text = "-" + text[1:]
    return int(re.sub(r"[ \u00a0\u202f]", "", text))


def _number(text: str, *, neuter: bool = False) -> str:
    integer, comma, fraction = text.partition(",")
    result = cardinal(_integer(integer), neuter=neuter)
    if text[0] in SIGN_CHARS and _integer(integer) == 0:
        result = "minus " + result
    if comma:
        result += " komma " + " ".join(cardinal(int(d)) for d in fraction)
    return result


def _amount(match: re.Match) -> str:
    raw = match["amount"]
    integer, comma, fraction = raw.partition(",")
    if fraction == "-":
        fraction = ""
    if len(fraction) > 2:
        raise ValueError("NOK amount has more than two decimal places")
    n = _integer(integer.replace(".", ""))
    cents = int(fraction.ljust(2, "0")) if fraction else 0
    result = cardinal(abs(n)) + (" krone" if abs(n) == 1 else " kroner")
    if cents:
        result += " og " + cardinal(cents, neuter=True) + " øre"
    return ("minus " if raw[0] in SIGN_CHARS else "") + result


def _unit(match: re.Match) -> str:
    raw = match["number"]
    unit = match["unit"].lower()
    singular = _integer(raw.split(",")[0]) in (-1, 1) and "," not in raw
    return _number(raw, neuter=unit in ("min", "sek", "g", "mg", "µg", "μg", "stk", "stk.")) + " " + UNITS[unit][not singular]


def _clock(match: re.Match) -> str:
    hour, minute = int(match["hour"]), int(match["minute"] or 0)
    if hour > 24 or minute > 59 or hour == 24 and minute != 0:
        raise ValueError("invalid clock time")
    words = cardinal(hour)
    if minute:
        words += (" null " if minute < 10 else " ") + cardinal(minute)
    return ("klokka " if match.groupdict().get("prefix") else "") + words


def _date(match: re.Match, pivot: int = 50) -> str:
    return _date_fields(match.groupdict(), pivot)


def _date_fields(groups: Mapping[str, str], pivot: int = 50) -> str:
    day = int(groups["day"])
    month = groups["month"]
    month = MONTH_ALIASES[month.lower()] if not month.isdigit() else int(month)
    raw_year = groups.get("year")
    y = int(raw_year) if raw_year else None
    if raw_year and len(raw_year) == 2:
        y += 2000 if y < pivot else 1900
    date(y if y is not None else 2000, month, day)  # Allows 29 February without a year.
    return ordinal(day) + " " + MONTHS[month - 1] + (" " + year(y) if y else "")


def _numeric_date(text: str, pivot: int) -> str:
    parts = re.split(rf"[ \t]*(?:[./]+|{DASH})[ \t]*", text.strip())
    if len(parts) != 3:
        raise ValueError("unsupported numeric date")
    y, month, day = parts if len(parts[0]) == 4 else (parts[2], parts[1], parts[0])
    return _date_fields({"year": y, "month": month, "day": day}, pivot)


class NorwegianNormalizer:
    """Conservative Bokmaal normalizer. Offsets are Python Unicode code points.

    Unresolved spans are retained exactly and returned as issues. This is not a
    semantic confidence score: absence of issues does not certify pronunciation.
    """

    def __init__(self, *, acronyms: Mapping[str, str] | None = None,
                 two_digit_year_pivot: int = 50):
        if not 0 <= two_digit_year_pivot <= 100:
            raise ValueError("two_digit_year_pivot must be in 0..100")
        self.acronyms = dict(ACRONYMS if acronyms is None else acronyms)
        self.two_digit_year_pivot = two_digit_year_pivot

    def normalize(self, text: str) -> str:
        return self.analyze(text).text

    def analyze(self, text: str) -> NormalizationResult:
        occupied: list[tuple[int, int]] = []
        changes: list[Replacement] = []
        issues: list[Issue] = []

        def apply(pattern: str, category: str, convert: Callable[[re.Match], str],
                  *, flags: int = re.IGNORECASE) -> None:
            for match in re.finditer(pattern, text, flags):
                start, end = match.span()
                if any(start < b and a < end for a, b in occupied):
                    continue
                occupied.append((start, end))
                try:
                    spoken = convert(match)
                except ValueError as error:
                    issues.append(Issue(start, end, match[0], str(error)))
                else:
                    # An abbreviation's final dot also closes the sentence at EOF.
                    terminal = not text[end:].strip(' \t\r\n"”’»)]}')
                    next_sentence = category == "measure" and re.match(r"\s+[A-ZÆØÅ]", text[end:])
                    if match[0].endswith(".") and (terminal or next_sentence) and not spoken.endswith("."):
                        spoken += "."
                    if category == "abbreviation" and text[end:end + 1] == "§":
                        spoken += " "
                    changes.append(Replacement(start, end, match[0], spoken, category))

        def protect(pattern: str, reason: str, *, flags: int = re.IGNORECASE) -> None:
            def reject(match: re.Match) -> str:
                raise ValueError(reason)
            apply(pattern, "unresolved", reject, flags=flags)

        protect(r"(?:https?://|www\.)[^\s<>]+|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
                "URL/email needs an explicit reading policy")
        protect(r"\b\d{4}-\d{2}-\d{2}T\d[\w:.,+-]*", "machine timestamp")
        protect(r"\b\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?\b", "clock seconds need a reading policy")
        protect(r"\b\d+(?:[ \t]*[:∶][ \t]*\d+){2,}\b", "multi-component ratio or time needs a reading policy")
        protect(r"\b(?:org\.?\s*nr\.?|organisasjonsnummer|postnummer|postnr\.?|kontonummer|fødselsnummer)"
                r"\s*:?\s*\+?\d[\d \u00a0-]*\d\b", "identifier needs a digit-reading policy")

        # Explicit version/legal/clock context wins over date-like punctuation.
        version_body = (r"\d+(?:\.\d+)+(?:-[a-z0-9]+(?:[.-][a-z0-9]+)*)?"
                        r"(?:\+[a-z0-9]+(?:[.-][a-z0-9]+)*)?")
        apply(rf"\b(?P<label>versjon(?:en)?|version)[ \t]+(?P<version>v?{version_body})(?!\w|\.\d)",
              "version", lambda m: ("versjonen " if m["label"].lower() == "versjonen" else "versjon ")
              + version(m["version"]))
        apply(rf"\bv(?P<version>{version_body})(?!\w|\.\d)", "version",
              lambda m: version(m["version"], prefix=True))
        apply(LEGAL_PATTERN, "legal", legal_reference)

        def telephone(match: re.Match) -> str:
            number = match["phone"]
            count = sum(ch.isdecimal() for ch in number)
            if not 3 <= count <= 15:
                raise ValueError("telephone number must contain 3..15 digits")
            label = match["label"].rstrip(".").lower()
            label = "telefon" if label == "tlf" else label
            return label + " " + ("pluss " if number.startswith("+") else "") + digits(number)
        apply(rf"\b(?P<label>tlf\.?|telefonnummer|telefon|mobilnummer|mobil)[ \t]*:?[ \t]*"
              rf"(?P<phone>\+?\d+(?:[ \t.{re.escape(DASH_CHARS)}]+\d+)*)(?![\w:])",
              "telephone", telephone)

        def clock_range(match: re.Match) -> str:
            def endpoint(prefix: str) -> str:
                h, minute = int(match[prefix + "hour"]), int(match[prefix + "minute"])
                if h > 24 or minute > 59 or h == 24 and minute:
                    raise ValueError("invalid clock range")
                return cardinal(h) + ((" null " if minute < 10 else " ") + cardinal(minute) if minute else "")
            return ("klokka " if match["prefix"] else "") + endpoint("first_") + " til " + endpoint("last_")
        apply(rf"\b(?P<prefix>(?:kl\.|klokka|klokken)[ \t]*)?"
              rf"(?P<first_hour>\d{{1,2}})(?(prefix)[.:]|:)(?P<first_minute>\d{{2}})[ \t]*{DASH}[ \t]*"
              r"(?P<last_hour>\d{1,2})(?(prefix)[.:]|:)(?P<last_minute>\d{2})\b", "time_range", clock_range)
        apply(r"\b(?P<prefix>kl\.|klokka|klokken)\s*(?P<hour>\d{1,2})[.:](?P<minute>\d{2})\b",
              "time", _clock)
        apply(r"\b(?P<prefix>kl\.|klokka|klokken)[ \t]*(?P<hour>\d{2})(?P<minute>\d{2})\b",
              "time", _clock)
        apply(r"\b(?P<prefix>kl\.|klokka|klokken)\s*(?P<hour>\d{1,2})\b(?P<minute>)",
              "time", _clock)

        def ratio(match: re.Match) -> str:
            return (match.groupdict().get("label") or "") + _number(match["first"]) + " til " + _number(match["last"])
        ratio_body = rf"(?P<first>{NUMBER})[ \t]*[:∶][ \t]*(?P<last>{NUMBER})"
        apply(rf"\b(?P<label>(?:forhold(?:et)?|blandingsforhold(?:et)?|målestokk(?:en)?|"
              rf"sideforhold(?:et)?|format(?:et)?|skjermformat(?:et)?)(?:[ \t]+(?:er|på))?[ \t]*:?[ \t]*)"
              rf"{ratio_body}{RIGHT}", "ratio", ratio)
        apply(rf"{LEFT}(?P<first>{NUMBER})(?:[ \t]+[:∶][ \t]*|[:∶][ \t]+)(?P<last>{NUMBER}){RIGHT}",
              "ratio", ratio)
        apply(rf"{LEFT}{ratio_body}(?P<suffix>{DASH}(?:forhold|format))\b", "ratio",
              lambda m: ratio(m) + m["suffix"])
        apply(r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2})\b", "time", _clock)

        pivot = self.two_digit_year_pivot
        sep = rf"[ \t]*(?:[./]+|{DASH})[ \t]*"
        numeric_date = rf"(?:\d{{4}}{sep}\d{{1,2}}{sep}\d{{1,2}}|\d{{1,2}}{sep}\d{{1,2}}{sep}(?:\d{{4}}|\d{{2}}))"
        apply(rf"\b(?P<first>{numeric_date})[ \t]*{DASH}[ \t]*(?P<last>{numeric_date})(?!\w)",
              "date_range", lambda m: _numeric_date(m["first"], pivot) + " til " + _numeric_date(m["last"], pivot))

        def full_day_range(match: re.Match) -> str:
            fields = match.groupdict()
            first = {"day": fields["first_day"], "month": fields["first_month"], "year": fields.get("first_year")}
            last = {"day": fields["day"], "month": fields["month"], "year": fields.get("year")}
            _date_fields({**first, "year": first["year"] or last["year"]}, pivot)
            return _date_fields(first, pivot) + " til " + _date_fields(last, pivot)
        apply(rf"\b(?P<first_day>\d{{1,2}})[ \t]*\.+[ \t]*(?P<first_month>\d{{1,2}})\.?[ \t]*{DASH}[ \t]*"
              rf"(?P<day>\d{{1,2}})[ \t]*\.+[ \t]*(?P<month>\d{{1,2}})(?:{sep}(?P<year>\d{{4}}|\d{{2}}))?(?!\w)",
              "date_range", full_day_range)
        apply(rf"\b(?P<first_day>\d{{1,2}})\.*[ \t]*(?P<first_month>{MONTH_PATTERN})(?![a-zæøå])\.?"
              rf"(?:[ \t]*(?P<first_year>\d{{4}}|\d{{2}}))?[ \t]*{DASH}[ \t]*"
              rf"(?P<day>\d{{1,2}})\.*[ \t]*(?P<month>{MONTH_PATTERN})(?![a-zæøå])\.?"
              r"(?:[ \t]*(?P<year>\d{4}|\d{2}))?(?!\w)", "date_range", full_day_range)

        def day_range(match: re.Match) -> str:
            fields = match.groupdict()
            _date_fields({**fields, "day": fields["first"]}, pivot)
            return ordinal(int(fields["first"])) + " til " + _date_fields(fields, pivot)
        apply(rf"\b(?P<first>\d{{1,2}})\.+[ \t]*{DASH}[ \t]*(?P<day>\d{{1,2}}){sep}"
              rf"(?P<month>\d{{1,2}})(?:{sep}(?P<year>\d{{4}}|\d{{2}}))?(?!\w)",
              "date_range", day_range)
        apply(rf"\b{numeric_date}(?!\w)", "date", lambda m: _numeric_date(m[0], pivot))

        apply(rf"\b(?P<first>\d{{1,2}})\.*[ \t]*{DASH}[ \t]*(?P<day>\d{{1,2}})\.*[ \t]*"
              rf"(?P<month>{MONTH_PATTERN})(?![a-zæøå])\.?(?:[ \t]*(?P<year>\d{{4}}|\d{{2}}))?\b",
              "date_range", day_range)
        apply(rf"\b(?P<day>\d{{1,2}})\.*[ \t]*(?P<month>{MONTH_PATTERN})(?![a-zæøå])"
              r"\.?(?:[ \t]*(?P<year>\d{4}|\d{2})(?!\d))?", "date", lambda m: _date(m, pivot))

        # With no year, a slash is a fraction unless a date cue explicitly says otherwise.
        apply(r"\b(?P<label>(?:dato|datert|den|frist(?:en)?(?: er)?)[ \t]+)"
              r"(?P<day>\d{1,2})[ \t]*/[ \t]*(?P<month>\d{1,2})(?![\d/])",
              "date", lambda m: m["label"] + _date(m, pivot))
        apply(LEFT + r"(?P<day>\d{1,2})[ \t]*\.[ \t]*(?P<month>\d{1,2})(?!\d|\.\d)",
              "date", lambda m: _date(m, pivot))
        def compact_date(match: re.Match) -> str:
            raw = match["compact"]
            try:
                words = _date_fields({"year": raw[:4], "month": raw[4:6], "day": raw[6:]}, pivot)
            except ValueError:
                words = _date_fields({"year": raw[4:], "month": raw[2:4], "day": raw[:2]}, pivot)
            return match["label"] + words
        apply(r"\b(?P<label>(?:dato|datert)[ \t]+)(?P<compact>\d{8})(?!\d)", "date", compact_date)

        # Remaining multi-component dotted numerals are versions, not decimals.
        apply(rf"\b(?P<version>\d+(?:\.\d+){{2,}}(?:-[a-z0-9]+(?:[.-][a-z0-9]+)*)?"
              r"(?:\+[a-z0-9]+(?:[.-][a-z0-9]+)*)?)(?!\w|\.\d)", "version",
              lambda m: version(m["version"]))

        apply(rf"{LEFT}{ratio_body}{RIGHT}", "ratio", ratio)
        protect(r"\b\d+(?:[/⁄∕]\d+){2,}\b", "ambiguous multiple-slash expression")

        fraction_body = rf"{SIGN}?(?:(?:\d+[ \t]+)?\d+[ \t]*[/⁄∕][ \t]*\d+|\d*[ \t]*[{''.join(VULGAR_FRACTIONS)}])"
        def fraction_words(raw: str, *, unit: str | None = None) -> str:
            negative = raw[0] in SIGN_CHARS
            raw = raw[1:].strip() if negative else raw.strip()
            if raw[-1] in VULGAR_FRACTIONS:
                numerator, denominator = VULGAR_FRACTIONS[raw[-1]]
                whole = int(raw[:-1].strip()) if raw[:-1].strip() else None
            else:
                numerator_text, denominator = re.split(r"[/⁄∕]", raw)
                left = numerator_text.split()
                whole = int(left[0]) if len(left) == 2 else None
                numerator, denominator = int(left[-1]), int(denominator)
            neuter = unit in ("min", "sek", "g", "mg", "µg", "μg", "stk", "stk.")
            return fraction(numerator, denominator, whole=whole, negative=negative, neuter=neuter)

        def fractional_quantity(match: re.Match) -> str:
            unit = match["unit"].lower()
            name = {"kr": "krone", "nok": "krone", "%": "prosent", "‰": "promille"}.get(unit)
            if name is None:
                name = UNITS[unit][0]  # Sprakradet: singular unit after a fraction.
            return fraction_words(match["fraction"], unit=unit) + " " + name
        def fractional_range_quantity(match: re.Match) -> str:
            unit = match["unit"].lower()
            name = {"kr": "krone", "nok": "krone", "%": "prosent", "‰": "promille"}.get(unit)
            name = name if name is not None else UNITS[unit][0]
            return fraction_words(match["first"], unit=unit) + " til " + fraction_words(match["last"], unit=unit) + " " + name
        apply(rf"{LEFT}(?P<first>{fraction_body})[ \t]*{DASH}[ \t]*(?P<last>{fraction_body})"
              rf"[ \t]*(?P<unit>{UNIT_PATTERN}|kr|NOK|%|‰)(?!\w)", "fraction_range", fractional_range_quantity)
        apply(rf"{LEFT}(?P<first>{fraction_body})[ \t]*{DASH}[ \t]*(?P<last>{fraction_body}){RIGHT}",
              "fraction_range", lambda m: fraction_words(m["first"]) + " til " + fraction_words(m["last"]))
        apply(rf"{LEFT}(?P<fraction>{fraction_body})[ \t]*(?P<unit>{UNIT_PATTERN}|kr|NOK|%|‰)(?!\w)",
              "fraction", fractional_quantity)
        apply(rf"{LEFT}(?P<fraction>{fraction_body}){RIGHT}", "fraction",
              lambda m: fraction_words(m["fraction"]))

        def range_words(match: re.Match) -> str:
            first, last = match["first"], match["last"]
            result = _number(first) + " til " + _number(last)
            unit = match.groupdict().get("unit")
            if unit:
                result += " " + UNITS[unit.lower()][1]
            return result
        range_pattern = rf"(?P<first>{NUMBER})[ \t]*{DASH}[ \t]*(?P<last>{NUMBER})"
        apply(rf"{LEFT}{range_pattern}\s*(?:kr\.?|NOK)\b", "currency_range",
              lambda m: range_words(m) + " kroner")
        apply(rf"(?<!\w)(?:kr\.?|NOK)\s*{range_pattern}{RIGHT}", "currency_range",
              lambda m: range_words(m) + " kroner")
        apply(rf"{LEFT}{range_pattern}\s*%(?!\w)", "percentage_range",
              lambda m: range_words(m) + " prosent")

        def split_money(match: re.Match) -> str:
            kr, ore = _integer(match["kr"]), int(match["ore"])
            result = cardinal(abs(kr)) + (" krone" if abs(kr) == 1 else " kroner")
            prefix = "minus " if match["kr"][0] in SIGN_CHARS else ""
            return prefix + result + " og " + cardinal(ore, neuter=True) + " øre"
        apply(rf"{LEFT}(?P<kr>{SIGN}?{INTEGER})\s*(?:kr\.?|kroner?)\s+(?P<ore>\d{{1,2}})\s*øre\b",
              "currency", split_money)
        protect(rf"{LEFT}{SIGN}?{INTEGER}\s*kr\.?\s+\d+\b", "split currency amount without an ore label")
        apply(rf"(?<!\w)(?:kr\.?|NOK)\s*(?P<amount>{AMOUNT}){RIGHT}", "currency", _amount)
        apply(rf"{LEFT}(?P<amount>{AMOUNT})\s*(?:kr\.?|NOK)\b", "currency", _amount)
        protect(rf"(?:[€$£]\s*{NUMBER}|{NUMBER}\s*(?:EUR|USD|GBP|€|\$|£))",
                "currency other than NOK needs an explicit reading policy")

        apply(rf"{LEFT}{range_pattern}[ \t]*(?P<unit>{UNIT_PATTERN})(?!\w)",
              "range", range_words)
        apply(rf"{LEFT}{range_pattern}{RIGHT}", "range", range_words)
        protect(rf"(?<!\w)\d+(?:{DASH}\d+){{2,}}\b", "ambiguous multi-part hyphenated identifier")
        apply(rf"{LEFT}(?P<number>{NUMBER})\s*%(?!\w)", "percentage",
              lambda m: _number(m["number"]) + " prosent")
        apply(rf"{LEFT}(?P<number>{NUMBER})\s*‰(?!\w)", "percentage",
              lambda m: _number(m["number"]) + " promille")
        apply(rf"{LEFT}(?P<number>{NUMBER})\s*(?P<unit>{UNIT_PATTERN})(?!\w)", "measure", _unit)
        apply(r"\b(?P<n>\d{1,4})\.(?=\s*(?:plass|gang|etasje|kapittel|ledd|punktum)\b)",
              "ordinal", lambda m: ordinal(int(m["n"])) + (" " if text[m.end():m.end() + 1].isalpha() else ""))
        apply(r"\b(?P<label>bokstav)[ \t]+(?P<letter>[a-zæøå])(?!\w)", "legal",
              lambda m: m["label"] + " " + letter(m["letter"]))
        apply(r"(?<!\w)(?:m[23²³]|cm[23²³])(?!\w)", "measure", lambda m: UNITS[m[0].lower()][0])
        apply(r"\b(?P<prefix>år(?:et)?\s+)(?P<year>\d{4})\b", "year",
              lambda m: m["prefix"] + year(int(m["year"])))

        protect(rf"\b{INTEGER}\.\d+(?:,\d+)?\b", "unsupported dotted numeric expression")
        protect(rf"{LEFT}{NUMBER}\s*°[a-z]*\b", "unsupported temperature or angle unit")
        protect(r"\b(?:[a-zæøå_]+\d[\w-]*|\d+[a-zæøå_]\w*)\b", "alphanumeric identifier")
        def enumeration(match: re.Match) -> str:
            label = match["label"]
            if label.isdecimal():
                words = cardinal(int(label))
            elif len(label) > 1 or label in ("I", "V", "X"):
                words = cardinal(roman(label))
            else:
                words = letter(label)
            return match["indent"] + words + "."
        apply(r"(?P<indent>^[ \t]*|(?<=:)[ \t]+)(?P<label>\d+|[a-zæøå]|[ivxlcdm]{2,})[.)](?=[ \t]+\S)",
              "enumeration", enumeration, flags=re.I | re.M)
        apply(rf"(?P<indent>^[ \t]*)(?P<bullet>[•●▪◦*{re.escape(DASH_CHARS)}])(?=[ \t]+\S)",
              "enumeration", lambda m: m["indent"] + "punkt.", flags=re.M)
        protect(r"[+±]\s*\d+(?:[.,]\d+)?", "unsupported sign or uncertainty expression")

        for abbreviation, spoken in ABBREVIATIONS.items():
            apply(r"(?<!\w)" + re.escape(abbreviation) + r"(?!\w)", "abbreviation", lambda m, s=spoken: s)
        for acronym, spoken in self.acronyms.items():
            apply(r"(?<!\w)" + re.escape(acronym) + r"(?!\w)", "acronym", lambda m, s=spoken: s, flags=0)

        def generic(match: re.Match) -> str:
            raw = match[0]
            if len(re.sub(r"\D", "", raw.split(",")[0])) >= 7:
                raise ValueError("large bare number may be an identifier; provide context")
            if re.match(r"0\d", raw.lstrip(SIGN_CHARS)):
                raise ValueError("leading-zero number needs a digit-reading policy")
            return _number(raw)
        apply(rf"{LEFT}{NUMBER}{RIGHT}", "number", generic)

        # Make any remaining numeric/symbol tokens visible to callers, rather
        # than claiming that unchanged text has been normalized successfully.
        protect(r"\d+(?:[.,:/-]\d+)*|[%‰§€$£±²³°=×÷<>]", "unhandled numeric or symbol form")
        changes.sort(key=lambda c: c.start)
        parts: list[str] = []
        cursor = 0
        for change in changes:
            parts.extend((text[cursor:change.start], change.spoken))
            cursor = change.end
        parts.append(text[cursor:])
        return NormalizationResult(text, "".join(parts), tuple(changes),
                                   tuple(sorted(issues, key=lambda i: i.start)))
