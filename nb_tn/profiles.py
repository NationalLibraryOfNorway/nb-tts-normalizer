"""Explicit written-language policies, not translation or dialect detection.

Hand-authored number forms follow Nynorsksenteret's grammar (p. 36);
abbreviations follow Sprakradet; noun forms follow Nynorskordboka and selected
CLDR 49 unit metadata. See SOURCES.md and nb_tn/provenance.json for exact
references, inspected-content hashes, attribution, and application choices.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    ones: tuple[str, ...]
    ordinals: tuple[str, ...]
    ordinal_ending: str
    million_plural: str
    billion_plural: str
    fraction_plural: str
    paragraphs: str
    squared_unit_ordinal: str
    abbreviations: Mapping[str, str]
    unit_forms: Mapping[str, tuple[str, str, str]]
    ratio_labels: str
    ordinal_cues: str


_ONES = ("null", "en", "to", "tre", "fire", "fem", "seks", "sju", "åtte", "ni",
         "ti", "elleve", "tolv", "tretten", "fjorten", "femten", "seksten", "sytten",
         "atten", "nitten")
_ORDINALS = ("", "første", "andre", "tredje", "fjerde", "femte", "sjette", "sjuende",
             "åttende", "niende", "tiende", "ellevte", "tolvte", "trettende",
             "fjortende", "femtende", "sekstende", "syttende", "attende", "nittende",
             "tjuende", "tjueførste", "tjueandre", "tjuetredje", "tjuefjerde",
             "tjuefemte", "tjuesjette", "tjuesjuende", "tjueåttende", "tjueniende",
             "trettiende", "trettiførste")
_ABBREVIATIONS = {
    "f.eks.": "for eksempel", "bl.a.": "blant annet", "jf.": "jamfør",
    "ca.": "cirka", "osv.": "og så videre", "m.m.": "med mer",
    "tlf.": "telefon", "nr.": "nummer", "kap.": "kapittel", "pkt.": "punkt",
    "art.": "artikkel", "bokst.": "bokstav", "pga.": "på grunn av", "dvs.": "det vil si",
}
_RATIO_LABELS = (r"forhold(?:et)?|blandingsforhold(?:et)?|målestokk(?:en)?|"
                 r"sideforhold(?:et)?|format(?:et)?|skjermformat(?:et)?")
_ORDINAL_CUES = r"plass|gang|etasje|kapittel|ledd|punktum"

NB = LanguageProfile(
    "nb", _ONES, _ORDINALS, "ende", "millioner", "milliarder", "deler", "paragrafene", "annen",
    MappingProxyType(_ABBREVIATIONS), MappingProxyType({}), _RATIO_LABELS, _ORDINAL_CUES,
)
NN = LanguageProfile(
    "nn", ("null", "ein") + _ONES[2:],
    ("", "første", "andre", "tredje", "fjerde", "femte", "sjette", "sjuande",
     "åttande", "niande", "tiande", "ellevte", "tolvte", "trettande", "fjortande",
     "femtande", "sekstande", "syttande", "attande", "nittande", "tjuande",
     "tjueførste", "tjueandre", "tjuetredje", "tjuefjerde", "tjuefemte", "tjuesjette",
     "tjuesjuande", "tjueåttande", "tjueniande", "trettiande", "trettiførste"),
    "ande", "millionar", "milliardar", "delar", "paragrafane", "andre",
    MappingProxyType({
        **_ABBREVIATIONS, "t.d.": "til dømes", "m.a.": "mellom anna",
        "osb.": "og så bortetter", "d.e.": "det er",
        "f.eks.": "for eksempel", "bl.a.": "blant anna", "osv.": "og så vidare",
        "m.m.": "med meir", "dvs.": "det vil seie",
    }),
    # Only differences from shared SI names are listed. Prefixes inherit these
    # base forms; no CLDR parser or upstream data file is needed at runtime.
    MappingProxyType({
        "s": ("sekund", "sekund", "n"), "sek": ("sekund", "sekund", "n"),
        "min": ("minutt", "minutt", "n"), "h": ("time", "timar", "m"),
        "Wh": ("wattime", "wattimar", "m"), "Ah": ("amperetime", "amperetimar", "m"),
        "rad": ("radian", "radianar", "m"), "sr": ("steradian", "steradianar", "m"),
        "stk": ("stykk", "stykk", "n"), "stk.": ("stykk", "stykk", "n"),
    }),
    _RATIO_LABELS + r"|tilhøve(?:t)?|blandingstilhøve(?:t)?|sidetilhøve(?:t)?",
    _ORDINAL_CUES + r"|gong",
)
PROFILES = MappingProxyType({"nb": NB, "nn": NN})


def get_profile(language: str = "nb") -> LanguageProfile:
    if not isinstance(language, str) or language not in PROFILES:
        raise ValueError("language must be nb or nn")
    return PROFILES[language]
