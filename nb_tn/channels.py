"""Explicit Norwegian broadcast names, including useful historical aliases.

Names are not migrated to newer brands. Dictionary readings are application
policy; see broadcaster references and disambiguation limits in SOURCES.md.
"""

import re

from .numbers import cardinal

CHANNELS = {
    "TV Norge": "te ve Norge",
    "NRK Super": "enn err kå super",
    "NRK Tegnspråk": "enn err kå tegnspråk",
    "NRK TV": "enn err kå te ve",
    "NRK Radio": "enn err kå radio",
    "TV": "te ve",
}
for n in (1, 2, 3):
    CHANNELS[f"NRK {n}"] = "enn err kå " + cardinal(n)
for n in (1, 2, 3, 13):
    CHANNELS[f"P{n}"] = "pe " + cardinal(n)
    CHANNELS[f"NRK P{n}"] = "enn err kå pe " + cardinal(n)
for prefix, spoken in (("", ""), ("NRK ", "enn err kå ")):
    CHANNELS[prefix + "P1+"] = spoken + "pe en pluss"
    CHANNELS[prefix + "mP3"] = spoken + "emm pe tre"
    CHANNELS[prefix + "P3 Musikk"] = spoken + "pe tre musikk"
for name in ("Nyheter", "Alltid Nyheter", "Klassisk", "Alltid Klassisk", "Jazz", "Sport",
             "Radio Super", "Folkemusikk", "Sámi Radio", "Sami Radio"):
    CHANNELS["NRK " + name] = "enn err kå " + name.lower()
for n in (2, 3):
    CHANNELS[f"TV {n}"] = "te ve " + cardinal(n)
for suffix in ("Direkte", "Nyheter", "Nyhetskanalen", "Play", "Zebra", "Livsstil",
               "Sport Premium 2", "Sport Premium", "Sport 1", "Sport 2", "Sport"):
    spoken = suffix.lower().replace("1", "en").replace("2", "to")
    CHANNELS["TV 2 " + suffix] = "te ve to " + spoken
for n, name in ((4, "Lyden av Norge"), (5, "Hits"), (6, "Rock"), (7, "Klem"), (8, "Pop"),
                (9, "Retro"), (10, "Country"), (11, "Dance"), (12, "Hitmix")):
    CHANNELS[f"P{n}"] = "pe " + cardinal(n)
    CHANNELS[f"P{n} {name}"] = "pe " + cardinal(n) + " " + name

# Optional spaces between canonical tokens also handle NRK1, TV2, TVNorge, and
# NRKP1+. A plus is permitted to have surrounding spaces, but never discarded.
def channel_pattern(name: str) -> str:
    return re.escape(name).replace(r"\ ", r"[ \t]*").replace(r"\+", r"[ \t]*\+")
