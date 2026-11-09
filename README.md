# Norwegian TTS normalization: Bokmål frontend

[![Tests](https://github.com/NationalLibraryOfNorway/nb-tts-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/NationalLibraryOfNorway/nb-tts-normalizer/actions/workflows/tests.yml)

A dependency-free Python frontend for an already Norwegian-capable TTS model.
It expands recognized written forms into spoken Bokmål, records exact source
spans, and retains unresolved spans with review issues. This is an initial
ruleset, not a complete Norwegian normalizer or a pronunciation guarantee.

The VoxCPM2 adapter disables its bundled Chinese/English normalizer. Attaching
this frontend does not require retraining the acoustic model. It can also be used
with any TTS pipeline that accepts Norwegian words as text. It contains no model
weights, ASR pipeline, phonemizer, or speech data.

## Install and quick start

Requires **Python 3.10 or newer**. Install from GitHub:

```bash
python -m pip install 'git+https://github.com/NationalLibraryOfNorway/nb-tts-normalizer.git'
nb-tn 'Saken gjelder kr 150,- jf. § 2, med frist 1. mai (ca. 10–15 dager).'
```

Output:

```text
Saken gjelder hundre og femti kroner jamfør paragraf to, med frist første mai (cirka ti til femten dager).
```

For a local editable installation:

```bash
git clone https://github.com/NationalLibraryOfNorway/nb-tts-normalizer.git
cd nb-tts-normalizer
python -m pip install -e .
python -m nb_tn --json 'Åse betaler 50 % den 1. mai.'
python -m nb_tn --strict 'AB123'
```

There are no runtime dependencies beyond Python's standard library. Running
`python -m nb_tn` from the source checkout also works without installation.
Installation uses setuptools as a build dependency; VoxCPM is installed separately
in the environment where you synthesize audio.

## Command-line use and review

Omitting the text argument reads stdin. `--json` includes the original text,
normalized text, replacements, review issues, and `needs_review`. `--strict`
exits with status 2 if any review issue exists; it emits no plain text in that
case, but still emits JSON when combined with `--json`. Without `--strict`,
plain text output includes unchanged unresolved spans and warnings go to stderr.

`--currency-locale {nb-NO,en-US}` selects the **input number format for monetary
amounts only**. `--dollar-currency {USD,CAD,AUD}` and
`--yen-currency {JPY,CNY}` provide explicit assumptions for bare `$` and `¥`.
These options do not change the spoken language; see the currency section below.

## Python API

```python
from nb_tn import NorwegianNormalizer

normalizer = NorwegianNormalizer()
report = normalizer.analyze("kr 150,-, 3,14 og 1. mai")
assert report.text == "hundre og femti kroner, tre komma en fire og første mai"
assert not report.needs_review
```

Each replacement contains `start`, `end`, `original`, `spoken`, and `category`.
Offsets index the **original** Python string in Unicode code points, with an
exclusive end; they are not byte offsets or JavaScript UTF-16 offsets. Replacements
are non-overlapping and sorted. Apply them right-to-left if reconstructing the
result yourself. Unknown spans have issues with the same source-offset convention.
No uncalibrated numeric confidence scores are emitted.

Use `analyze()` whenever unresolved symbols matter. The convenience method
`normalizer.normalize(text)` returns only the normalized string and does not
raise on review issues. Input source text is never mutated.

For example:

```python
report = normalizer.analyze("Frist: 31. februar 2026. Referanse: AB123.")
assert report.needs_review
assert report.text == report.original
for issue in report.issues:
    print(issue.start, issue.end, issue.original, issue.reason)
```

The default acronym dictionary can be replaced explicitly:

```python
normalizer = NorwegianNormalizer(acronyms={"API": "a pe i", "NRK": "enn err kå"})
assert normalizer.normalize("API og NRK") == "a pe i og enn err kå"
```

This argument replaces the dictionary rather than merging with its defaults.

Channel readings have their own dictionary, independent of general acronyms:

```python
normalizer = NorwegianNormalizer(channels={"Min Radio 7": "min radio sju"})
assert normalizer.normalize("MinRadio7") == "min radio sju"

# Disable broadcast-name interpretation, e.g. for chemistry text containing P4.
normalizer = NorwegianNormalizer(channels={})
```

`channels=...` also replaces its defaults. The default channel dictionary accepts
optional spaces and case variants, such as `NRK1`/`NRK 1`, `TV2`/`TV 2`, and
`NRKP1 +`. These aliases do not change unit-symbol case rules.

## VoxCPM2 integration

Use the already loaded fine-tune or LoRA model from your existing inference code:

```python
from nb_tn.voxcpm import generate_norwegian

# model = your already loaded Norwegian VoxCPM2 model
audio, report = generate_norwegian(
    model,
    "Fristen er 1. mai, og beløpet er kr 150,-.",
    seed=7,
    # reference_wav_path="...",  # Existing generation options pass through.
)
```

This calls `model.generate(text=report.text, normalize=False, ...)`. The adapter
defaults to strict review: an issue raises `ValueError` **before** invoking the
model. `strict=False` explicitly permits synthesis of unchanged unresolved spans.
For custom review flows, call `analyze()` first, review the report, and call the
model yourself. `.normalize(text)` is a convenient string-only method; it does
not block or expose review issues.

Prompt transcripts are passed through as supplied; they should describe what
is actually spoken in the reference recording. Pass only speech text to this
adapter. If you use VoxCPM's `(control instruction)` prefixes, normalize the speech
body first and then attach the control prefix yourself. Streaming generation is
not wrapped in this initial adapter.

## Design choices

The pipeline applies ordered rules to the **original** string, claims matching
source spans, then reconstructs the spoken text. A span that has already been
claimed cannot be rewritten by a later rule. Invalid recognized forms also
claim their spans, so a failed date or amount is not partly converted by the
generic number rules.

Structured forms take precedence: protected URLs/identifiers, channel names, explicit versions,
legal citations, currency amounts and labeled phones, clocks and contextual ratios, dates, then
fractions, quantities/ranges, ordinals/list markers, dictionaries, and finally
bare numbers. For example, `§2-1` retains its chapter/section structure while
`10-15` is a range; `v1.2.26` is a version while `1.2.26` is a date.

The implementation deliberately uses deterministic rules and a compact arithmetic
number verbalizer. It needs no model download, LLM call, credentials, network,
GPU, or time-dependent inference at runtime. These choices make normalization
inspectable and allow a single faulty rule to be corrected without retraining
the speech model. They also mean that broad semantic disambiguation is outside
the package's capabilities.

The code is split into:

- `nb_tn/normalizer.py`: rule precedence, span ownership, date/quantity parsing,
  and reports.
- `nb_tn/numbers.py`: cardinal, ordinal and year readings.
- `nb_tn/readings.py`: fraction, version, letter, Roman numeral and digit readings.
- `nb_tn/legal.py`: chapter/section paths, lists, ranges and subdivisions.
- `nb_tn/units.py`: case-sensitive SI prefixes, unit names, powers, compound
  units, and detection of symbol-shaped unsupported expressions.
- `nb_tn/channels.py`: explicit Norwegian broadcasting names and historical aliases.
- `nb_tn/currencies.py`: supported currencies, minor-unit precision, explicit
  monetary number locales and currency-symbol assumptions.
- `nb_tn/voxcpm.py`: optional adapter for an already loaded model.
- `nb_tn/__main__.py`: CLI and strict-mode exit behavior.

To extend coverage, add a structured rule before the generic fallback, include
successful and rejected examples in the tests, and document any new ambiguity
policy. Do not silently discard unsupported numbers or symbols.

## Fixed reading policy and coverage

| Written form | Spoken form / policy |
| --- | --- |
| `150`, `-5`, `10 000` | `hundre og femti`, `minus fem`, `ti tusen` |
| `3,14` | `tre komma en fire`; fractional digits are read individually |
| `kr 150,-`, `150 kr`, `NOK 1,01` | NOK amounts; the last includes `en krone og ett øre` |
| `123.456,78 kr`, `5 kr 50 øre` | Dotted grouping in explicit NOK amounts; explicit kroner/øre fields |
| `100 USD`, `EUR 12,50`, `GBP 1,01` | Norwegian foreign-currency readings and named minor units |
| `USD 1,234.56`, `US$12.50` with `currency_locale="en-US"` | Explicit English-style monetary formatting; Norwegian speech |
| `1. mai`, `01.05.2026`, `2026-05-01` | Ordinal day, Norwegian month name, optional year; calendar validity checked |
| `1 . 5 . 2026`, `1/5/2026`, `1-5-26`, `1mai2026`, `1. sept. 2026` | Tolerate spacing, separators, abbreviated months, missing dots and two-digit years |
| `01.05`, `1.–3. mai`, `1.-3.5.2026` | Day/month dates and date ranges; Norwegian ordering |
| `året 1998`, date year `1998` | `nitten nittiåtte`; 1905 uses `nitten null fem`; 2005 uses `to tusen og fem` |
| `kl. 17:03`, `klokken 09.05`, `kl. 0905`, `12:30` | Digital clock reading; no colloquial `halv`/`kvart` forms |
| `kl. 09.00-10.30`, `09:00—10:30` | Clock ranges with `til` |
| `10–15`, `10-15 km`, `10—15 %`, `kr 10−15` | Numeric ranges with ASCII, Unicode hyphens/dashes, and minus-shaped separators |
| `%`, `‰` with a number | `prosent`, `promille` |
| `km/t`, `m/s`, `km`, `cm`, `mm`, `m`, `m²`, `m³` | Expanded measures, including attached `5km` |
| `m2`, `m3`, `cm2`, `cm3` | Equivalent to the corresponding superscript forms; attached `75m2` also works |
| `kg`, `g`, `mg`, `µg`, `ml`, `dl`, `l`, `min`, `sek`, `°C`, `stk.` | Selected measures and singular/plural forms |
| `W`, `kW`, `MW`, `mW`, `J`, `kWh`, `MWh` | Power and energy, including `kilowattime`/`kilowattimer` |
| `V`, `mA`, `Ω`, `MΩ`, `nF`, `S`, `MHz`, `hPa` | Electrical quantities, frequency and pressure |
| `K`, `°F`, `ha`, `daa`, `Bq`, `mSv`, `lx`, `mol` | More temperature, area, activity, dose, light and amount units |
| `m/s²`, `m/s2`, `m/s^2`, `kg/m³`, `N·m`, `s⁻¹` | Compound units, products and powers |
| `NRK1`, `TV2`, `TVNorge`, `NRK P1+`, `NRK mP3` | Explicit channel-name readings before generic identifier detection |
| `NRK P3 Musikk`, `NRK P13`, `P4`, `P5 Hits`, `P12 Hitmix` | Current and historical names; no automatic rebranding |
| `§ 2`, `§§ 3–5` | `paragraf to`, `paragrafene tre til fem` |
| `§2-1`, `§2.1`, `§2-1a`, `§2(1)(b)` | Compound sections, suffixes, tolerated dots, parenthesized ledd/bokstav notation |
| `§§ 3-4 til 3-7`, `§§ 2-1 og 2-2` | Preserve chapter/section structure inside compound lists and ranges |
| `1. plass`, `2.ledd`, `bokstav b` | Selected ordinals (1–9999), missing-space repair, and spoken letter names |
| `1.`, `a)`, `II.`, `•` at a list-item start | `en.`, `a.`, `to.`, `punkt.`; always a full stop after the spoken marker |
| `tlf. 01234567`, `tlf. +47 12345678` | `telefon` plus individual digits, including leading zeros and `pluss` |
| `4:3`, `1 : 50 000`, `forholdet er 16:10` | `fire til tre`, `en til femti tusen`, contextual ratio instead of clock |
| `1/2`, `2/3`, `8/13`, `2 1/2`, `½`, `⅔` | `en halv`, `to tredeler`, `åtte trettendeler`, mixed and Unicode fractions |
| `1/2 min`, `2/3 min` | Singular unit after a fraction: `ett halvt minutt`, `to tredeler minutt` |
| `v1.2.3`, `versjon 1.2`, `1.2.3` | Version components separated by `punkt`; `v` becomes `versjon` |
| `v1.2.3-beta.2`, `v1.2.3-rc.1+build.42` | Release labels, numbered prereleases, and build metadata |
| `jf.`, `f.eks.`, `bl.a.`, `ca.`, `osv.`, `m.m.`, `nr.`, `kap.`, `pkt.` | Explicit abbreviation dictionary |
| `NAV`, `NRK`, `USA`, `EU`, `EØS` | Exact-case pronunciation dictionary; caller can replace it |

Modern forms `tjue`, `tretti`, `sju` are used. Bokmål `en`/`ett` are selected in
known contexts; number words are emitted without stress accents. This does not
offer Nynorsk or dialect selection.

The arithmetic converter supports signed integers with absolute value below
one trillion (`10**12`), including millions and milliards. **Bare numbers of
seven or more digits are nevertheless flagged**, because they may be phone or
other identifiers. Explicit supported amount/measure contexts can use the larger
range. A plain four-digit integer uses the cardinal reading unless it occurs in
a recognized date or is introduced by `år`/`året`.

## Foreign currencies, input locale and code-switching

All supported amounts are verbalized **in Norwegian Bokmål**, regardless of
the currency's country. Supported codes are **NOK, EUR, USD, GBP, SEK, DKK, CAD,
AUD, CHF, CNY, JPY and KWD**. Prefix and suffix codes, supported symbols,
selected written currency names, matching paired markers, negative amounts and
numeric monetary ranges are recognized.

| Input, default `currency_locale="nb-NO"` | Output |
| --- | --- |
| `100 USD` | `hundre amerikanske dollar` |
| `EUR 12,50` | `tolv euro og femti cent` |
| `GBP 1,01` | `ett britisk pund og en penny` |
| `SEK 1,01` | `en svensk krone og ett øre` |
| `CAD 10` | `ti kanadiske dollar` |
| `JPY 100` | `hundre japanske yen` |
| `KWD 1,005` | `en kuwaitisk dinar og fem fils` |
| `CHF 1,20` | `en komma to null sveitsiske franc` |
| `10–15 EUR` | `ti til femten euro` |

Minor-unit precision is stored per currency: JPY uses 0 digits, KWD uses 3,
and the other supported currencies use 2. There is **no rounding**. Amounts
with excess precision are retained with a review issue; this is an application
policy based on ISO 4217 minor units, not a claim that fractional market quotes
can never exist. Named subunits include øre, cent, penny/pence and fils.
For CHF and CNY, nonzero fractional amounts use a decimal reading of the major
unit instead of selecting a language-specific subunit name. Zero minor units
are omitted. All parsing uses integers and digit strings, not floating point.

The input convention is **not inferred from the currency**. A US-dollar price
inside Norwegian text may be written `USD 1.234,56`; its counterpart in US-style
formatting is `USD 1,234.56`. Choose the convention explicitly:

```python
from nb_tn import NorwegianNormalizer

norwegian = NorwegianNormalizer()  # currency_locale="nb-NO"
assert norwegian.normalize("EUR 12,50") == "tolv euro og femti cent"

us_format = NorwegianNormalizer(
    currency_locale="en-US",
    symbol_currencies={"$": "USD", "¥": "JPY"},
)
assert us_format.normalize("$12.50") == "tolv amerikanske dollar og femti cent"
assert us_format.normalize("¥100") == "hundre japanske yen"
```

```bash
nb-tn --strict --currency-locale en-US --dollar-currency USD '$12.50'
nb-tn --json '100 USD og EUR 12,50'
```

The default accepts decimal comma, space/NBSP/narrow-NBSP grouping, and dotted
three-digit grouping. `en-US` accepts decimal point and comma grouping (also
space grouping). Mixed grouping characters, malformed groups, and excess
fractional precision are flagged. For example, `USD 1,234` means 1234 dollars
under `en-US`, but is flagged under `nb-NO` because three fractional digits
exceed USD's configured precision. There is no automatic locale or language
detection. The locale setting does not alter dates, units or other bare numbers.

Symbol disambiguation is also explicit:

- Bare `$` and `¥` are ambiguous and trigger review by default. Only these two
  symbols can be configured through `symbol_currencies`; accepted mappings are
  `$` -> USD/CAD/AUD and `¥` -> JPY/CNY. Settings are local to each normalizer.
- `US$`, `C$`/`CA$`, `A$`/`AU$`, `JP¥` and `CN¥` are qualified aliases. Compatible
  paired codes also disambiguate: `$10 CAD` uses CAD even if the configured
  default for `$` is USD. Conflicting markers such as `€10 USD` are rejected.
- The local shorthand `kr`/`kr.` continues to mean NOK; use SEK/DKK explicitly
  for the other supported Nordic currencies. `€` means EUR and `£` means GBP
  by application policy. Use explicit codes for other currencies using similar
  names or symbols. Codes are uppercase; selected written-name aliases are
  case-insensitive, including `euros`, `US dollars` and `British pounds`.
- Unqualified `dollar`/`dollars` amounts are flagged. Bare `pounds` is not
  treated as currency because it may denote weight. Unknown uppercase
  three-letter markers and selected unsupported symbols are flagged; this is
  not a complete recognizer for every currency name or script.

**This is not multilingual normalization.** In an English sentence, only the
recognized amount receives a Norwegian reading; the package does not rewrite
the sentence into English spoken form or switch the voice's language. For text
with mixed number conventions or languages, the application should separate
spans with known locale/language metadata and call the appropriate normalizer
for each. Source offsets in each report remain relative to that input span.
An English normalizer and an English-capable TTS voice are separate requirements.

Currency coverage is finite. Scientific-notation amounts, accounting-negative
parentheses, unsupported codes and subunits, historical denomination changes,
and arbitrary fractional amounts such as `1/2 EUR` are not comprehensively
handled. Parentheses are not interpreted as a negative sign. Exchange rates and
currency conversion are never used or inferred.

## Physical quantities and broadcast names

Unit symbols are **case-sensitive**. For example:

| Input | Output |
| --- | --- |
| `5 MW` | `fem megawatt` |
| `5 mW` | `fem milliwatt` |
| `2 S` | `to siemens` |
| `2 s` | `to sekunder` |
| `12 kWh` | `tolv kilowattimer` |
| `100 MHz` | `hundre megahertz` |
| `9,81 m/s²` | `ni komma åtte en meter per sekund i kvadrat` |
| `5 kg/m³` | `fem kilo per kubikkmeter` |

The parser resolves an exact unit or an SI prefix plus a unit, then reads
products (`·`, `⋅`, `∙`, `*`, `×`), division (`/`), and powers. Powers can be written
with superscripts, caret notation, or the `m2`/`m3` aliases. Absolute powers 1–9
are supported; negative powers become denominator readings. Square/cubic length
units use `kvadrat-`/`kubikk-`; other squared units use `i kvadrat`. No values are
converted, rounded, or rescaled. The familiar existing `kg` -> `kilo` and
`km/t` -> `kilometer i timen` readings are retained.

`l` and `L` both mean liter; `µ`, `μ` and ASCII `u` are accepted micro-prefix
aliases, and `Ω` is accepted as an ohm-sign alias for `Ω`. Incorrect casing such
as `mhz` or `mw` is **flagged**, not guessed as MHz/MW/mW. The existing lowercase
`°c` input alias is retained explicitly. In ordinary spaced text, `1 dag` means
`en dag`; the parser does not mistake the Norwegian day noun for dekagram.

Unsupported symbol-shaped quantity expressions are retained as whole spans
with review issues, including `5 XYZ`, `5 mhz`, `5 m//s`, and `5 W/(m²·K)`. The
detector considers known symbols with wrong casing, uppercase/mixed-case tokens,
attached unit-like strings, and explicit unit operators. It does not label every
ordinary count noun as a unit: `5 personer` becomes `fem personer`. Consequently,
an unknown separated lowercase word such as `5 frobnitz` is not guaranteed to
be flagged. Uppercase prose can conversely trigger conservative review.
Parenthesized unit groups and implicit products such as `kg m-3` are not yet
parsed; use explicit forms such as `kg/m3` for supported compound readings.

Broadcast names are a finite dictionary, matched longest-first. `NRK P1+` is
read as `enn err kå pe en pluss`, rather than matching `P1` and losing `+`.
Names include the common NRK TV/radio forms, TV 2 and several named services,
TVNorge, TV3, and the P4-group names through P12 Hitmix. Plain natural-word names
such as `Radio Norge` already pass through unchanged. This is not a complete
catalog of Norwegian, local, international or discontinued channels.

Historical names retain their historical reading: `NRK P13` is still
`enn err kå pe tretten`, while `NRK P3 Musikk` is `enn err kå pe tre musikk`.
The dictionary does not assert that a service is currently broadcasting, nor
substitute new names into old text. Channel readings are curated application
choices, not broadcaster-certified phonetic transcriptions. Names such as
bare `P4` may also mean something else in scientific text; use `channels={}` or
a domain-specific dictionary where necessary.

## Review and limitations

Impossible dates/times, zero-denominator fractions, ambiguous multi-slash forms,
clock seconds, machine timestamps, URLs/emails, alphanumeric IDs, leading-zero
bare numbers, and labeled postal/account/organization identifiers are retained
and flagged. Unsupported currencies and numbers outside the converter's range
also remain unchanged. Malformed **formatting** is tolerated; invalid calendar
values such as `31. februar` are not invented or corrected to another date.

Disambiguation policies are explicit and deterministic:

- Full numeric dates use day–month–year, or year–month–day when the first field
  has four digits. Dot-separated day/month forms without a year are dates, even
  if the final month dot is missing. They are not English decimal numbers.
- Two-digit years use a fixed cutoff: `00`–`49` mean 2000–2049; `50`–`99` mean
  1950–1999. Change `NorwegianNormalizer(two_digit_year_pivot=...)` if needed.
  No current date or moving century window is consulted. Compact dates require
  an explicit `dato`/`datert` cue; valid YYYYMMDD is tried before DDMMYYYY.
- A two-field slash expression is a fraction. An explicit date cue such as
  `dato 1/5` selects a date; a full three-field slash date includes a year.
- Bare `HH:MM` is a clock. A ratio cue (`forholdet`, `format`, `målestokk`, etc.),
  colon spaces, a ratio sign, or a `-format`/`-forhold` suffix selects a ratio.
  Dotted clock ranges require `kl.`/`klokka`/`klokken` to avoid stealing dates.
- Any supported hyphen/dash between numeric range endpoints means `til`,
  including ASCII `-` and Unicode minus `−`. This user-requested tolerance means
  bare subtraction or scores written that way will also be read as ranges.
  Dates, labeled phones, versions, and legal references are parsed first.
- In a single section reference, `§2-1` is a chapter/section path, not an interval.
  Plural `§§3-5` is a range; `§§3-4 til 3-7` and `§§2-1 og 2-2` contain paths.
  Ambiguous flattened compound ranges such as `§§3-4-3-7` still need review.
- Enumeration starts are line starts (with indentation) or the first marker
  after a colon. Numeric labels use cardinal numbers. Single letters use letter
  names; uppercase I/V/X and multi-letter Roman labels use their numeric values.
  Bullets use `punkt.`. Nested dotted list numbers remain ambiguous with dates.
- Explicit `v` or `versjon` context wins over dates. Without context, a valid
  three-field date wins over a version: `1.2.26` is a date, `v1.2.26` is a version,
  and `1.2.3` is a version. Numeric version components with leading zeros are
  read digit by digit. Unknown release labels are spelled out; the small known
  set includes alfa, beta, RC and build. Version-reading details are application
  policy, not a claim that Språkrådet prescribes SemVer pronunciation.

Detection is finite: an empty issue list does **not** mean every possible symbol,
abbreviation, acronym, unit, or contextual ambiguity was recognized. Bare
forms can have other meanings in a particular domain. Corpus-specific rules and
a listening evaluation are still needed. The reasoning and sources for reading
choices are recorded in [SOURCES.md](SOURCES.md).

Ordinary sentence punctuation and whitespace outside replacement spans are
preserved. Abbreviation dots are removed during expansion; final sentence dots
are retained at end of input (including before closing quotes), and `stk.` also
retains its dot before a following capitalized sentence. General sentence
boundary disambiguation around abbreviations remains incomplete.

Tests cover supported and rejected cases, source offsets, repeated spans,
punctuation, CLI exit behavior, and the adapter using a fake model. **Actual
Norwegian VoxCPM2 audio has not been evaluated.** The next validation is a fixed
listening set comparing raw text, manually expanded text, and this frontend with
the same fine-tune, speaker reference, and seed.

## Development and tests

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

CI runs the suite on Python 3.10, 3.12 and 3.13. Tests include exact spoken-text
expectations, malformed inputs, ambiguity priorities, Unicode dash variants,
reconstruction from original offsets, idempotence of representative outputs,
CLI behavior, and a mocked VoxCPM adapter. They do not measure perceptual audio
quality or establish corpus-wide normalization accuracy.

Other limitations include English decimal-point conventions, unknown acronym
pronunciations, currencies outside the listed codes and forms, scientific
notation and arbitrary unit algebra, pronunciation changes across Norwegian dialects, and normalization
across chunk boundaries. Match whole sentences or complete list items where
possible; slicing a token between chunks can remove the context a rule needs.

## Credits and provenance

Developed for the [National Library of Norway](https://github.com/NationalLibraryOfNorway)
under the Språkmodeller team, with implementation assistance from OpenAI Codex.

The initial investigation drew on the `cardinal_numbers.py` and evaluation
normalization scripts accompanying the **NbAiLab Norwegian Wav2Vec2 Bokmål
300M/1B models**, including their v2 releases. Their converter credits
[peresolb/number-conversion](https://github.com/peresolb/number-conversion/).
Those projects supplied useful starting examples and motivation; this repository
uses a new compact arithmetic implementation and span engine, rather than
vendoring the upstream bidirectional converter or its ASR cleanup pipeline.

Reading conventions were checked against **Språkrådet** guidance on dates,
fractions, ratios, legal references, abbreviations, and list markers.
**OpenBMB's VoxCPM project** provides the inference interface used by the optional
adapter. These acknowledgements do not imply upstream review or endorsement.

See [SOURCES.md](SOURCES.md) for the exact inspected model revisions, links to
language guidance, and the distinction between source conventions and application
policies such as the year cutoff, tolerant separators and software-version readings.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). This license covers
the implementation and documentation in this repository. The external models and
projects credited above retain their own licenses and are not bundled here.
