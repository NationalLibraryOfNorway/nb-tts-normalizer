# Sources and implementation provenance

## Nynorsk support (2026-11-12)

The Nynorsk extension and shared-renderer refactor are first-party implementations
for this repository, written with OpenAI Codex assistance. No external normalizer
code, dictionary database, grammar document or model was copied into the package.
This is text normalization, not a Bokmål-to-Nynorsk translator or dialect engine.

Linguistic references inspected:

- [Nynorsksenteret: Nynorsk grammatikk, Ordklasser og setningar](https://nynorsksenteret.no/uploads/documents/Heile_grammatikken_1.pdf),
  printed p. 36, supplies the cardinal/ordinal forms, including `sjuande`,
  `trettande`, `tjuande`, `tjueein`, `hundrede` and `tusende`. The inspected PDF
  is 1,940,417 bytes, SHA-256
  `92e02fc19edb8c3163190885d7348745b5fa84e91af0f040365564a9d103522b`.
  The document is a linguistic reference, not vendored code or data. The
  arithmetic composition algorithm remains our own existing implementation.
- [Språkrådet: forkortelser](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/forkortelser/)
  supplies `t.d.` → `til dømes`, `m.a.` → `mellom anna`, `osb.` →
  `og så bortetter`, `d.e.` → `det er`, `m.m.` → `med meir`, and shared
  abbreviations. This mutable reference was read through the web interface;
  no stable content hash or redistributed page snapshot is claimed.
- **Nynorskordboka**, published by Språkrådet and the University of Bergen:
  [krone](https://ordbokene.no/nn/krone) establishes feminine currency agreement;
  [sekund](https://ordbokene.no/nn/sekund) supports the selected neuter time-unit
  reading and invariant plural; [stykk](https://ordbokene.no/nn/stykk) is
  uninflected; [del](https://ordbokene.no/nno/nn/11243) supports `delar`;
  [paragraf](https://ordbokene.no/nn/paragraf) supplies the noun;
  [halv](https://ordbokene.no/nn/halv) supports gendered half-quantity forms;
  [hundrede](https://ordbokene.no/nn/hundrede) and
  [tusende](https://ordbokene.no/nob/nn/82574) cross-check higher ordinals.
  These are cited linguistic facts, not an imported dictionary dataset.
- [Unicode CLDR 49, Nynorsk locale XML](https://github.com/unicode-org/cldr/blob/96e54b273d2da4ec6fbad350ba19ff23fa24a588/common/main/nn.xml),
  revision `96e54b273d2da4ec6fbad350ba19ff23fa24a588` (release-49), provides
  selected unit/currency metadata: `sekund`, `minutt`, `timar`, `kilowattimar`,
  `radianar`, `steradianar`, and `kuwaitiske dinarar`. Its 490,146 inspected
  bytes have SHA-256
  `30cac90c46840c8c8d98375b4d301fc871e4e4181f53206225ad8b8ee3f63dfd`.
  Only a small, manually selected/adapted metadata subset is used; inheritance
  markers, formatting patterns and the full XML are not copied into runtime
  data. Copyright 2001–2026 Unicode, Inc.; these data are under **Unicode-3.0**,
  not the separate restrictions on the LDML specification. The applicable
  notice is reproduced in [LICENSES/Unicode-3.0.txt](LICENSES/Unicode-3.0.txt)
  and NOTICE; the upstream license is also pinned in the manifest.

Application choices, rather than rules attributed to these sources:

- Use `language="nb"` by default, with explicit `language="nn"`; never change
  unclaimed prose or infer language from the input. Unknown language settings
  are rejected. Custom dictionary readings are retained exactly as supplied.
- Select unaccented `ein`/`ei`/`eitt`, `første` rather than `fyrste`, and a single
  deterministic set of accepted numeral variants. No dialect selection is made.
- Preserve the existing group-based number algorithm, supported numeric bounds,
  date validity, year cutoff, span precedence and review behavior. Number gender
  comes from known currency/unit metadata, not a general syntax analyzer.
- Apply the same natural/digit-by-digit decimal choices in both languages.
  Unit powers, composed SI prefixes (including watt-/ampere-hour compounds),
  fractions, legal subdivisions and number ranges use the chosen profile.
- Keep proper broadcaster brands such as `TV Norge` and `NRK Nyheter` intact;
  generated channel numbers use Nynorsk forms. Letter spellings, version
  readings and supported contextual aliases are project conventions.

The packaged [nb_tn/provenance.json](nb_tn/provenance.json) records source roles,
derivation and artifact hashes for the Nynorsk extension. Run
`python -m nb_tn.provenance` for the offline integrity check, or add `--fetch`
to verify hash-recorded upstream bytes. No hash is asserted for the mutable
Språkrådet/dictionary reference pages; links and inspection dates are recorded.
Hashes detect content changes, not authorship or linguistic validity. They do
not guarantee continued upstream availability. First-party source and its
provenance record are versioned together; the checker never updates either.
Earlier Bokmål investigation provenance is documented below and is not
retroactively represented as fully hash-pinned. Source-owner or native-speaker
review, corpus-wide accuracy, and acoustic evaluation have not been performed.

## Decimal speech policy (2026-11-12)

[Matematikksenteret: Desimaltall som par av hele tall](https://www.matematikksenteret.no/nn/node/6558)
describes whole-number fractional readings in everyday speech, including 3,14
and 1,83, but recommends digit-by-digit readings for teaching place value.
The default groups exactly two fractional digits representing 10..99; leading
zeros and other lengths stay digit-by-digit. The configurable `digits` mode
reads every fractional digit separately. This boundary and its consistent use
across quantities, ranges and decimal-style currency amounts are application
choices, not a claim of one mandatory spoken Norwegian decimal standard.

## Initial implementation sources

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

## Foreign-currency amounts read in Norwegian (2026-11-09)

- [ISO 4217 overview](https://www.iso.org/iso-4217-currency-codes.html) explains
  currency codes and their relationship to minor units.
- [SIX ISO 4217 List One](https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml),
  the maintenance agency's XML, was inspected with publication date 2026-09-17.
  Its downloaded SHA-256 was
  `33139b438657d1cee116ba737807ea71d19d6de4b90f799a09c56f0cc6a1b0ff`.
  Of the twelve shipped codes, JPY has exponent 0, KWD 3, and the others 2.
  Only the selected metadata is recorded in code; the XML is not vendored or
  fetched at runtime. Future monetary changes may require a registry update.
- [Norges Bank: currency names and codes](https://www.norges-bank.no/tema/Statistikk/Valutakurser/)
  supplies Norwegian major-unit terminology. No exchange-rate data is used.
- [Bokmålsordboka: cent](https://ordbokene.no/bm/8769),
  [pund](https://ordbokene.no/bm/pund), and
  [euro](https://ordbokene.no/bm%2Cnn/euro) establish relevant gender and forms.
  The chosen readings use masculine `en cent`, neuter `ett britisk pund`, and
  masculine `en euro` with the customary invariant plural in amounts.
- [Central Bank of Kuwait: unit of currency](https://www.cbk.gov.kw/en/legislation-and-regulation/cbk-law/chapter-one)
  specifies the relationship between the dinar and fils.

Norwegian/US monetary separator settings, symbol defaults and country-qualified
aliases, supported word forms, precision rejection rather than rounding, CHF/CNY
decimal readings, and Norwegian-only output are explicit application choices.
The ISO minor-unit metadata is a parsing policy, rather than a restriction on
every possible quoted price. The implementation neither performs
language identification nor claims to handle arbitrary code-switching. Existing
NOK forms and strict review behavior are retained.

The application defaults for bare symbols are USD for `$` and CNY for `¥`, as
explicitly requested for this project. Per-normalizer overrides, explicit
`None` to require review, qualified aliases and paired ISO codes still take
precedence. These defaults are user-selected conventions rather than ISO rules.
