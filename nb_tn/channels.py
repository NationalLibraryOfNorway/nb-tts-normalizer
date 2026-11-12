"""Explicit Norwegian broadcast names, including useful historical aliases.

Names are not migrated to newer brands. Dictionary readings are application
policy; see broadcaster references and disambiguation limits in SOURCES.md.
"""

import re

from .numbers import cardinal
from .profiles import get_profile

def channel_readings(language: str = "nb") -> dict[str, str]:
    """Localize generated numbers, never translate an official brand name."""
    get_profile(language)
    channels = {
        "TV Norge": "te ve Norge", "NRK Super": "enn err kå super",
        "NRK Tegnspråk": "enn err kå tegnspråk", "NRK TV": "enn err kå te ve",
        "NRK Radio": "enn err kå radio", "TV": "te ve",
    }
    for n in (1, 2, 3):
        channels[f"NRK {n}"] = "enn err kå " + cardinal(n, language=language)
    for n in (1, 2, 3, 13):
        channels[f"P{n}"] = "pe " + cardinal(n, language=language)
        channels[f"NRK P{n}"] = "enn err kå pe " + cardinal(n, language=language)
    for prefix, spoken in (("", ""), ("NRK ", "enn err kå ")):
        channels[prefix + "P1+"] = spoken + "pe " + cardinal(1, language=language) + " pluss"
        channels[prefix + "mP3"] = spoken + "emm pe tre"
        channels[prefix + "P3 Musikk"] = spoken + "pe tre musikk"
    for name in ("Nyheter", "Alltid Nyheter", "Klassisk", "Alltid Klassisk", "Jazz", "Sport",
                 "Radio Super", "Folkemusikk", "Sámi Radio", "Sami Radio"):
        channels["NRK " + name] = "enn err kå " + name.lower()
    for n in (2, 3):
        channels[f"TV {n}"] = "te ve " + cardinal(n, language=language)
    for suffix in ("Direkte", "Nyheter", "Nyhetskanalen", "Play", "Zebra", "Livsstil",
                   "Sport Premium 2", "Sport Premium", "Sport 1", "Sport 2", "Sport"):
        spoken = suffix.lower().replace("1", cardinal(1, language=language)).replace("2", "to")
        channels["TV 2 " + suffix] = "te ve to " + spoken
    for n, name in ((4, "Lyden av Norge"), (5, "Hits"), (6, "Rock"), (7, "Klem"), (8, "Pop"),
                    (9, "Retro"), (10, "Country"), (11, "Dance"), (12, "Hitmix")):
        channels[f"P{n}"] = "pe " + cardinal(n, language=language)
        channels[f"P{n} {name}"] = "pe " + cardinal(n, language=language) + " " + name
    return channels


CHANNELS = channel_readings()

# Optional spaces between canonical tokens also handle NRK1, TV2, TVNorge, and
# NRKP1+. A plus is permitted to have surrounding spaces, but never discarded.
def channel_pattern(name: str) -> str:
    return re.escape(name).replace(r"\ ", r"[ \t]*").replace(r"\+", r"[ \t]*\+")
