# Sources and implementation provenance

The following repositories were inspected on 2026-11-08, without downloading
model weights:

| Hugging Face repository | Inspected revision |
| --- | --- |
| `NbAiLab/nb-wav2vec2-300m-bokmaal` | `4783f50808c12aa3d8f31b5da3c1b74a18e1a386` |
| `NbAiLab/nb-wav2vec2-300m-bokmaal-v2` | `640997a0253512e054d4ce15b8599a511d0cf001` |
| `NbAiLab/nb-wav2vec2-1b-bokmaal` | `85f517a6bd3e07529fafe45546158d6c96ef1420` |
| `NbAiLab/nb-wav2vec2-1b-bokmaal-v2` | `58a6eb5d7927c378f5d2785bc865756c9ae273ae` |

All four contain byte-identical `cardinal_numbers.py` files, SHA-256
`e06245cf2f9280c97339079bf57eb2373b07ea29abb70a753aeaa155d1733ae6`.
That source credits [peresolb/number-conversion](https://github.com/peresolb/number-conversion/).

Relevant pinned sources:

- [NbAiLab cardinal converter](https://huggingface.co/NbAiLab/nb-wav2vec2-300m-bokmaal/blob/4783f50808c12aa3d8f31b5da3c1b74a18e1a386/cardinal_numbers.py)
- [300M-v2 evaluation normalizer](https://huggingface.co/NbAiLab/nb-wav2vec2-300m-bokmaal-v2/blob/640997a0253512e054d4ce15b8599a511d0cf001/eval.py)
- [1B-v2 evaluation normalizer](https://huggingface.co/NbAiLab/nb-wav2vec2-1b-bokmaal-v2/blob/58a6eb5d7927c378f5d2785bc865756c9ae273ae/eval.py)
- [VoxCPM inference wrapper](https://github.com/OpenBMB/VoxCPM/blob/main/src/voxcpm/core.py)
- [VoxCPM bundled Chinese/English normalizer](https://github.com/OpenBMB/VoxCPM/blob/main/src/voxcpm/utils/text_normalize.py)

NbAiLab's evaluation rules provided starting examples for units, times, ranges,
years, and abbreviations. Their destructive ASR cleanup and unconditional
Nynorsk conversion were not carried over. The arithmetic converter here is a
new compact group-based implementation rather than a vendored copy of the
approximately 650-line bidirectional converter. It adds signed numbers, larger
scales, and explicit error handling; reverse conversion is not implemented.
The span-based replacement engine and VoxCPM adapter are new implementations.

No model-loading, NLTK, Transformers, WeText, or GPU dependencies are needed to
run the normalizer or its tests. A real Norwegian VoxCPM2 listening evaluation
has not yet been performed; adapter tests use a fake model and do not download
or evaluate a checkpoint.

## Expanded reading policy (2026-11-08)

Official language sources inspected for the expanded rules:

- [Språkrådet: tall, tid og dato](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/tall-tid-dato/)
  describes Norwegian date ordering, clocks, and fraction names. The implementation
  consistently chooses cardinal denominator names such as `tredeler` and
  `trettendeler`, with the familiar `en halv` special case, and a singular unit
  after fractions. It does not simplify fractions or round them to decimals.
- [Språkrådet: forholdet 1 : 1](https://sprakradet.no/spraksporsmal-og-svar/forholdet-1-1-tall-eller-bokstaver/)
  supports the `til` reading of numerical ratios.
- [Språkrådet: lovhenvisninger](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/lovhenvisninger/)
  distinguishes chapter/section hyphens from ranges and distinguishes ledd,
  punktum and bokstav references. The application preserves this distinction
  when verbalizing references. It also accepts nonstandard missing spaces,
  dotted compound sections, and parenthesized subdivisions as input tolerances.
- [Språkrådet: punktlister i regelverk](https://sprakradet.no/klarsprak/sprak-i-lover-og-forskrifter/skriverad/struktur-i-lover-og-forskrifter/punktlister/)
  discusses numeric and alphabetic list markers and their terminating dots.
  The spoken marker plus a full stop is an explicit user requirement here;
  bullet-to-`punkt.` and Roman-label readings are application choices.
- [Språkrådet: forkortelser](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/forkortelser/)
  supplies expansions including `tlf.` -> `telefon`, `nr.` -> `nummer`, and
  `pkt.` -> `punkt`. Digit-by-digit phone reading is an application policy that
  preserves the number exactly rather than guessing a grouping convention.

Separator tolerance, m2/m3 aliases, two-digit-year century cutoff, ambiguity
precedence, and software-version readings are application policies, not new
Norwegian orthography rules. In particular, version `punkt`, release-label
readings and the all-hyphens-as-ranges behavior are documented choices. These
changes normalize speech input; they do not rewrite the user's source strings,
and reports continue to refer to exact original character offsets.

## Physical quantities and Norwegian broadcast names (2026-11-09)

- [SSB: standardtegn i tabeller](https://www.ssb.no/eksempler/standardtegn-i-tabeller)
  supplies Norwegian unit names and examples for area, volume, power, energy,
  electric current and decimal prefixes.
- [BIPM: SI Brochure](https://www.bipm.org/en/publications/si-brochure)
  supplies the international SI symbols and prefix system. Matching preserves
  the distinction between mega `M` and milli `m`, and between symbols such as
  siemens `S` and second `s`. The package is a speech verbalizer, not a
  standards-conformance checker or a dimensional-analysis/conversion library.
- [NRK: radio help and information](https://info.nrk.no/radio/) and
  [NRK's P3 Musikk announcement](https://kommunikasjon.ntb.no/pressemelding/18636532/nrk-p13-blir-til-nrk-p3-musikk?lang=no&publisherId=89389)
  supply channel names and the historical P13/P3 Musikk distinction. The
  dictionary preserves both names rather than rewriting historical text.
- [Norges televisjon: kanaltilbud](https://ntv.no/)
  supplies common NRK TV-name variants. Its listings may contain historical
  radio branding; dictionary inclusion is not a claim of current availability.
- [P4-gruppen: information about the radio channels](https://www.lydenavradio.no/p4/om/informasjon-om-p4-gruppen/artikkel/472039)
  supplies the P4 through P12 channel brands and names.
- [Medietilsynet: TV 2's public-service report](https://www.medietilsynet.no/fakta/rapporter/kringkasting/2026/allmennkringkastingsrapporten-tv-2/)
  supports TV 2's Direkte and Nyheter naming. Other TV 2 service names and
  familiar historical brands are retained as explicit pronunciation aliases.

Channel letter/digit readings, accepted spacing aliases and longest-first name
matching are application policies, not phonetic transcriptions verified by the
broadcasters. The channel dictionary can be replaced or disabled independently
of the acronym dictionary. Unit aliases and unsupported-unit review heuristics
are documented in README.md. No third-party implementation or model weights
were copied or added for these extensions.
