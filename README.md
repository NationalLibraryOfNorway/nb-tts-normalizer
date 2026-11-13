# Norwegian TTS normalization: Bokmål and Nynorsk frontend

[![Tests](https://github.com/NationalLibraryOfNorway/nb-tts-normalizer/actions/workflows/tests.yml/badge.svg)](https://github.com/NationalLibraryOfNorway/nb-tts-normalizer/actions/workflows/tests.yml)

A dependency-free Python frontend for an already Norwegian-capable TTS model.
It expands recognized written forms into spoken Bokmål (default) or Nynorsk, records exact source
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

`--language {nb,nn}` selects the language of generated readings. Bokmål (`nb`)
remains the default. Nynorsk (`nn`) is explicit; this is not language detection
or translation of surrounding prose. See the Nynorsk examples below.

`--year-style {pairs,traditional}` defaults to `pairs`: contextual four-digit
years are read as two groups (`2026` → `tjue tjueseks`), except 2000–2009,
which use `to tusen` / `to tusen og …`. Use `traditional` for
the previous mixed policy (paired 1100–1999, cardinal otherwise).

`--scientific-units` is **enabled by default**. `--no-scientific-units` spells
ambiguous single-letter symbols as letters after numbers (`2 V` → `to ve`).
It does not disable scientific-number notation, explicit compound units,
temperature symbols `°C`/`°F`, or everyday units `m`, `g`, `kg`, `mg`, `l`, `s`, `h`.
The uppercase litre alias `L` is also retained. `K` follows the scientific switch.

`--english-unit-aliases` opts into `mins`, `hr`/`hrs`, and `sec`/`secs` after
quantities. It is **off by default**, independently of `--scientific-units`.
In Python, use `NorwegianNormalizer(english_unit_aliases=True)`.

`--decimal-style {natural,digits}` selects decimal speech. The default `natural`
reads `3,14` as `tre komma fjorten`; `digits` gives `tre komma en fire` for
technical or instructional use. See the decimal policy below for leading zeros
and longer fractional parts.

`--currency-locale {nb-NO,en-US}` selects the **input number format for monetary
amounts only**. `--dollar-currency {USD,CAD,AUD}` and
`--yen-currency {JPY,CNY}` override the defaults `$` -> USD and `¥` -> CNY.
These options do not change the spoken language; see the currency section below.

## Python API

```python
from nb_tn import NorwegianNormalizer

normalizer = NorwegianNormalizer()
report = normalizer.analyze("kr 150,-, 3,14 og 1. mai")
assert report.text == "hundre og femti kroner, tre komma fjorten og første mai"
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

## Nynorsk

Available since version 0.6.0. Select the language explicitly:

```python
from nb_tn import NorwegianNormalizer

nn = NorwegianNormalizer(language="nn")
assert nn.normalize("NOK 1,01 og 2 kWh") == "ei krone og eitt øre og to kilowattimar"
assert nn.normalize("8. mai 2026") == "åttande mai tjue tjueseks"
assert nn.normalize("§§ 1–3") == "paragrafane ein til tre"
assert nn.normalize("t.d. 1 kg") == "til dømes ein kilo"

technical_nn = NorwegianNormalizer(language="nn", decimal_style="digits")
assert technical_nn.normalize("3,21") == "tre komma to ein"
assert nn.normalize("3,21") == "tre komma tjueein"

# Input separators are independent of the language used for speech.
nn_us = NorwegianNormalizer(language="nn", currency_locale="en-US")
assert nn_us.normalize("$1.01") == "ein dollar og ein cent"
```

```bash
nb-tn --language nn --strict 'NOK 1,01 og 2 kWh'
nb-tn --language nn --decimal-style digits --strict '3,21'
nb-tn --language nn --json '31. februar 2026'
```

Full-sentence examples (exact default Nynorsk output, also covered by tests):

Input:

```text
Etter § 2-1 skal 1,75 m kabel koste kr 150,50 ved levering 8. mai 2026.
```

Output:

```text
Etter paragraf to ein skal ein komma syttifem meter kabel koste hundre og femti kroner og femti øre ved levering åttande mai tjue tjueseks.
```

Input:

```text
Den 8 . 5 . 2026 vart 75 m2 leigde ut for $125,75, med eit tillegg på 3,14 % etter §§ 3–5.
```

Output:

```text
Den åttande mai tjue tjueseks vart syttifem kvadratmeter leigde ut for hundre og tjuefem dollar og syttifem cent, med eit tillegg på tre komma fjorten prosent etter paragrafane tre til fem.
```

Input:

```text
Etter § 7 skal prisen 8. juni 2026 vere ¥1,21 per 1,75 kWh, medan toleransen er 0,05 %.
```

Output:

```text
Etter paragraf sju skal prisen åttande juni tjue tjueseks vere ein komma tjueein yuan per ein komma syttifem kilowattimar, medan toleransen er null komma null fem prosent.
```

Both languages use the same span engine and validation rules. Nynorsk covers
numbers, dates/times, units and powers, currencies, fractions, ratios/ranges,
legal references, enumeration, phone digits, software versions and channel
numbers. Profiles and dictionaries are instance-local, so different languages
can be used concurrently. Custom acronym/channel mappings retain their supplied
values and replace the corresponding defaults as before.

The fixed Nynorsk policy chooses unaccented `ein`/`ei`/`eitt`, `første`, `sju`,
`tjue`, `sjuande`, `millionar` and `milliardar`. Known currency/unit metadata
selects gender; there is no general grammatical analysis of surrounding nouns.
An unqualified `1` therefore reads `ein`, even before an unknown prose noun.
`sekund` and `minutt` use invariant plurals; time-based compounds use `timar`.
`t.d.`, `m.a.`, `osb.` and `d.e.` are recognized alongside shared abbreviations.
Existing ordinary words, already spelled-out numbers and official channel
brands are **not translated**: `TV Norge` stays `te ve Norge`, and
`NRK Nyheter` retains `nyheter`. Generated channel numbers use `ein` in Nynorsk.
Letter spellings and version-reading conventions remain application policies,
not phonetic transcriptions or dialect selection.

Number forms were checked against [Nynorsksenteret's grammar, p. 36](https://nynorsksenteret.no/uploads/documents/Heile_grammatikken_1.pdf);
abbreviations follow [Språkrådet](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/forkortelser/).
Gender/inflection references and the pinned Unicode CLDR unit metadata are
listed in [SOURCES.md](SOURCES.md#nynorsk-support-2026-11-12) and the shipped
[provenance manifest](nb_tn/provenance.json). Tests check written outputs; no
native-speaker review, corpus-wide accuracy claim or Nynorsk audio evaluation
is implied. The acoustic model must itself support the requested speech.

## Decimal reading policy

Since version 0.5.0, `decimal_style="natural"` is the default. Exactly two
fractional digits are read as a whole number when they represent 10..99.
Leading zeros are never dropped, and other lengths remain digit-by-digit:

| Input | Default `natural` | Technical `digits` |
| --- | --- | --- |
| `3,14` | `tre komma fjorten` | `tre komma en fire` |
| `1,75` | `en komma syttifem` | `en komma sju fem` |
| `3,10` | `tre komma ti` | `tre komma en null` |
| `3,05` | `tre komma null fem` | `tre komma null fem` |
| `3,00` | `tre komma null null` | `tre komma null null` |
| `3,14159` | `tre komma en fire en fem ni` | `tre komma en fire en fem ni` |

```python
technical = NorwegianNormalizer(decimal_style="digits")
assert technical.normalize("3,14 kg") == "tre komma en fire kilo"
```

```bash
nb-tn --strict '3,14 kg'
nb-tn --strict --decimal-style digits '3,14 kg'
```

The policy applies consistently to bare decimals, quantities, percentages,
promille, ratio endpoints, ranges, and CHF/CNY amounts spoken as decimals.
It does not change named currency subunits (`EUR 12,50` still uses `femti cent`),
software-version components, phone digits, dates, clocks, or written fractions.
It is independent of `currency_locale`, which controls monetary input parsing.
No digits are rounded or silently truncated.

This everyday-speech default is an application choice, not a universal rule
for Norwegian mathematics. [Matematikksenteret](https://www.matematikksenteret.no/nn/node/6558)
describes whole-number fractional readings in everyday speech while recommending
digit-by-digit readings for mathematical teaching. Select `digits` when that
distinction matters; older releases used digit-by-digit decimal speech by default.

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

The adapter uses natural decimal speech by default. For technical speech, pass
`normalizer=NorwegianNormalizer(decimal_style="digits")` to
`generate_norwegian(...)` (import `NorwegianNormalizer` from `nb_tn`).

For Nynorsk, pass `normalizer=NorwegianNormalizer(language="nn")`; combine
`language="nn"` with `decimal_style="digits"` if needed. The same adapter and
strict review behavior are used, and `normalize=False` is still passed to VoxCPM.

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
- `nb_tn/profiles.py`: immutable Bokmål/Nynorsk number forms, vocabulary,
  abbreviation policies and language-specific contextual cues.
- `nb_tn/readings.py`: fraction, version, letter, Roman numeral and digit readings.
- `nb_tn/legal.py`: chapter/section paths, lists, ranges and subdivisions.
- `nb_tn/units.py`: case-sensitive SI prefixes, unit names, powers, compound
  units, and detection of symbol-shaped unsupported expressions.
- `nb_tn/channels.py`: explicit Norwegian broadcasting names and historical aliases.
- `nb_tn/currencies.py`: supported currencies, minor-unit precision, explicit
  monetary number locales and currency-symbol assumptions.
- `nb_tn/voxcpm.py`: optional adapter for an already loaded model.
- `nb_tn/__main__.py`: CLI and strict-mode exit behavior.
- `nb_tn/provenance.json` / `provenance.py`: source/derivation records and an
  offline artifact-integrity audit, with optional upstream verification.

To extend coverage, add a structured rule before the generic fallback, include
successful and rejected examples in the tests, and document any new ambiguity
policy. Do not silently discard unsupported numbers or symbols.

## Fixed reading policy and coverage

The examples in this table use the default Bokmål profile. The same notation
categories are supported by the Nynorsk profile with localized generated words.

| Written form | Spoken form / policy |
| --- | --- |
| `150`, `-5`, `10 000` | `hundre og femti`, `minus fem`, `ti tusen` |
| `3,14`, `1,75` | `tre komma fjorten`, `en komma syttifem`; configurable decimal reading |
| `kr 150,-`, `150 kr`, `NOK 1,01` | NOK amounts; the last includes `en krone og ett øre` |
| `123.456,78 kr`, `5 kr 50 øre` | Dotted grouping in explicit NOK amounts; explicit kroner/øre fields |
| `100 USD`, `EUR 12,50`, `GBP 1,01` | Norwegian foreign-currency readings and named minor units |
| `USD 1,234.56`, `US$12.50` with `currency_locale="en-US"` | Explicit English-style monetary formatting; Norwegian speech |
| `1. mai`, `01.05.2026`, `2026-05-01` | Ordinal day, Norwegian month name, optional year; calendar validity checked |
| `1 . 5 . 2026`, `1/5/2026`, `1-5-26`, `1mai2026`, `1. sept. 2026` | Tolerate spacing, separators, abbreviated months, missing dots and two-digit years |
| `01.05`, `1.–3. mai`, `1.-3.5.2026` | Day/month dates and date ranges; Norwegian ordering |
| `året 1998`, date year `1998` | `nitten nittiåtte`; 1905 uses `nitten null fem`; 2005 uses `to tusen og fem`; 2010 uses `tjue ti` |
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
known contexts; Nynorsk uses `ein`/`ei`/`eitt`. Number words are emitted without
stress accents. Language selection is explicit; dialect selection is not offered.

The arithmetic converter supports signed integers with absolute value below
one trillion (`10**12`), including millions and milliards. **Bare numbers of
seven or more digits are nevertheless flagged**, because they may be phone or
other identifiers. Explicit supported amount/measure contexts can use the larger
range. A plain four-digit integer uses the cardinal reading unless it occurs in
a recognized date or is introduced by `år`/`året`.

### Contextual year readings

The paired-year default applies to recognized dates and `år`/`året` contexts,
not arbitrary four-digit numbers, quantities, identifiers or version components.
Years 1000–9999 generally use two groups; exact centuries end in `hundre`, and
final groups 01–09 include `null`. **2000–2009 are an explicit exception:**
`2000` → `to tusen`, `2006` → `to tusen og seks`. Paired readings resume at
2010 (`tjue ti`, `tjue seksten`, `tjue tjueseks`). Years below 1000 keep their
cardinal reading. This change applies to both Bokmål and Nynorsk.

| Year | Bokmål | Nynorsk |
|---|---|---|
| 1000 | ti hundre | same |
| 1001 | ti null en | ti null ein |
| 1984 | nitten åttifire | same |
| 2000 | to tusen | same |
| 2001 | to tusen og en | to tusen og ein |
| 2005 | to tusen og fem | same |
| 2006 | to tusen og seks | same |
| 2009 | to tusen og ni | same |
| 2010 | tjue ti | same |
| 2016 | tjue seksten | same |
| 2026 | tjue tjueseks | same |
| 2101 | tjueen null en | tjueein null ein |
| 9999 | nittini nittini | same |

This is the project's requested reading preference, not a claim that every
paired form is universally preferred. `year_style="traditional"` restores the
previous behavior. Calendar validation and the two-digit-year pivot are unchanged.

[NRK's year-pronunciation guidance](https://sprak.nrk.no/rettleiing/arstal/)
recommends the short form, referring to the acceptance of both forms for 2014.
It does not mandate our exact 2010 cutoff, which is a project consistency choice.
The TTS representation retains spaces (`tjue tjueseks`), corresponding to the
short reading written `tjuetjueseks`; this is spoken-text preparation, not a
general orthographic formatter. We do not claim that the longer reading has
disappeared from use. `year_style="traditional"` still allows it after 2010.

```python
plain_letters = NorwegianNormalizer(scientific_units=False, year_style="pairs")
assert plain_letters.normalize("året 2026 og 2 V") == "året tjue tjueseks og to ve"
assert NorwegianNormalizer(year_style="traditional").normalize("året 2026") == "året to tusen og tjueseks"
```

### Tolerated abbreviation aliases

Selected abbreviations may omit their final dot: `f.eks`, `bl.a`, `osv`, `dvs`,
`pga`, and, in Nynorsk, `t.d`, `m.a`, `osb`. Existing dotted spellings still work;
this is input tolerance, not a recommendation to omit punctuation in prose.
Word boundaries prevent substitutions inside longer words.

English-style `mins`, `hr`/`hrs`, and `sec`/`secs` are **not standard Norwegian
abbreviations**. Numeric quantities using them remain unchanged and flagged by
default, including fractions, ranges, scientific notation and compound units.
Enable `english_unit_aliases=True` (CLI `--english-unit-aliases`) to accept them.
With that option, the aliases use Norwegian names and singular/plural agreement:
`2 mins, 1 hr og 2 secs` → Bokmål `to minutter, en time og to sekunder`,
Nynorsk `to minutt, ein time og to sekund`. The option is independent of the
scientific-unit setting. Bare aliases without a quantity remain prose; enabling
them does not enable general English-language normalization.

Standard Norwegian forms `min`, `s`, `sek`, and the international hour symbol
`h` remain enabled. They have no plural suffix: `5 min`, not `5 mins`.
The Norwegian abbreviation `t` can mean either *time* or *tonn*, as recorded by
[Språkrådet](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/forkortelser/).
Therefore `2 t`, `1/2 t`, `2–3 t`, `1.2e-3 t` and compounds containing a `t`
factor (such as `t/h`, `t/min`, `m/t`) remain unchanged and flagged, in every mode.
Use `h` for hours or write `tonn` for tonnes. The established speed alias `km/t`
remains supported. This is explicit syntax policy, not inference from prose.
Bare `t` without a quantity remains a letter; `T` (tesla) and prefixed `mt`
(millitonn) retain their separate, case-sensitive meanings.

```python
assert NorwegianNormalizer().analyze("2 hrs").needs_review
assert NorwegianNormalizer(english_unit_aliases=True).normalize("2 hrs") == "to timer"
assert NorwegianNormalizer(language="nn", english_unit_aliases=True).normalize("2 hrs") == "to timar"
assert NorwegianNormalizer().analyze("2 t").needs_review
```

## Foreign currencies, input locale and code-switching

Bare `$` and `¥` retain USD/CNY defaults but use plain `dollar`/`yuan` in both
languages, including ranges and decimals. Explicit codes or qualified markers
retain qualified names: `USD`, `US$` → `amerikanske dollar`; `CNY`, `CN¥` →
`kinesiske yuan`. An explicit alternate mapping (for example `$` → CAD or `¥` →
JPY) retains `kanadiske dollar` or `japanske yen`, rather than misnaming the currency.

All supported amounts are verbalized **in the selected Norwegian language**
(Bokmål by default, or Nynorsk), regardless of
the currency's country. Supported codes are **NOK, EUR, USD, GBP, SEK, DKK, CAD,
AUD, CHF, CNY, JPY and KWD**. Prefix and suffix codes, supported symbols,
selected written currency names, matching paired markers, negative amounts and
numeric monetary ranges are recognized.

| Input, default `currency_locale="nb-NO"` | Output |
| --- | --- |
| `100 USD` | `hundre amerikanske dollar` |
| `$10` | `ti dollar` |
| `¥100` | `hundre yuan` |
| `EUR 12,50` | `tolv euro og femti cent` |
| `GBP 1,01` | `ett britisk pund og en penny` |
| `SEK 1,01` | `en svensk krone og ett øre` |
| `CAD 10` | `ti kanadiske dollar` |
| `JPY 100` | `hundre japanske yen` |
| `KWD 1,005` | `en kuwaitisk dinar og fem fils` |
| `CHF 1,20` | `en komma tjue sveitsiske franc` |
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
    symbol_currencies={"¥": "JPY"},  # Override yuan; $ already defaults to USD.
)
assert us_format.normalize("$12.50") == "tolv dollar og femti cent"
assert us_format.normalize("¥100") == "hundre japanske yen"
```

```bash
nb-tn --strict --currency-locale en-US '$12.50'
nb-tn --strict --yen-currency JPY '¥100'
nb-tn --json '100 USD og EUR 12,50'
```

The default accepts decimal comma, space/NBSP/narrow-NBSP grouping, and dotted
three-digit grouping. `en-US` accepts decimal point and comma grouping (also
space grouping). Mixed grouping characters, malformed groups, and excess
fractional precision are flagged. For example, `USD 1,234` means 1234 dollars
under `en-US`, but is flagged under `nb-NO` because three fractional digits
exceed USD's configured precision. There is no automatic locale or language
detection. The locale setting does not alter dates, units or other bare numbers.

Symbol defaults and overrides:

- Bare `$` defaults to **USD (US dollar)** and bare `¥` defaults to **CNY
  (Chinese yuan)**. These are application defaults, not claims that the symbols
  uniquely identify those currencies. Only these two symbols can be configured
  through `symbol_currencies`; accepted mappings are `$` -> USD/CAD/AUD and
  `¥` -> JPY/CNY. Omitted keys retain their defaults; settings are local to each
  normalizer. Explicit `None`, e.g. `symbol_currencies={"$": None, "¥": None}`,
  requires review for those bare symbols instead of assuming a currency.
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
| `9,81 m/s²` | `ni komma åttien meter per sekund i annen` |
| `5 kg/m³` | `fem kilo per kubikkmeter` |

The parser resolves an exact unit or an SI prefix plus a unit, then reads
products (`·`, `⋅`, `∙`, `*`, `×`, whitespace), division (`/`), and powers. Powers can be written
with superscripts, caret notation, or the `m2`/`m3` aliases. Absolute powers 1–9
are supported; negative powers become denominator readings. Square/cubic length
units use `kvadrat-`/`kubikk-`; other squared units use `i annen` in Bokmål and
`i andre` in Nynorsk. Higher powers retain their ordinal `potens` readings.
No values are converted, rounded, or rescaled. The familiar existing `kg` -> `kilo` and
`km/t` -> `kilometer i timen` readings are retained.

Since 0.6.1, the squared-unit default follows the unit wording in table 3 of
the supplied [government draft, Forskrift om målenheter og måling](https://www.regjeringen.no/link/8610546553aa40b1acb67b6f3ed0385a.aspx?id=2221947):

| Symbol | Bokmål | Nynorsk |
| --- | --- | --- |
| `m/s²`, `m/s2`, `m/s^2`, `m·s⁻²` | `meter per sekund i annen` | `meter per sekund i andre` |
| `s²`, `s^2` | `sekund i annen` | `sekund i andre` |
| `ms²` | `millisekund i annen` | `millisekund i andre` |
| `A²` | `ampere i annen` | `ampere i andre` |
| `m²`, `m2` | `kvadratmeter` | `kvadratmeter` |
| `m³`, `m3` | `kubikkmeter` | `kubikkmeter` |

Bokmål also permits `andre`; this project chooses `annen` for squared physical
units to match the supplied table. Nynorsk uses `andre`, following
[Språkrådet's ordinal guidance](https://sprakradet.no/godt-og-korrekt-sprak/rettskriving-og-grammatikk/tall-tid-dato/).
This is a generated-reading policy, not a claim that mathematical `i kvadrat`
is invalid. Already written-out phrases are left unchanged. Ordinary dates
and other ordinal contexts still use `andre` in both languages.

The draft itself varies between `kvadratmeter` for area and `meter i annen`
in `m²/s`. We retain `kvadratmeter per sekund` for `m²/s`, and
`kubikkmeter` for cubic length factors, to preserve the existing consistent
geometric names across equivalent spellings and contexts. Applying the
squared-unit reading to other unit factors is an explicit project extension.
The PDF has a `[dato] 2007` placeholder and old SI definitions; it is cited for
unit wording only, not as a statement of current law. Its apparent `Sr`, `Kat`
and `Ohm` symbol spellings are not imported; case-sensitive SI symbols remain
`sr`, `kat` and `Ω`. This 0.6.1 reading change did not alter definitions,
conversions, CLI names or the default language. The 0.7.0 coverage extension
below additionally supports grouped and implicit unit products. See
[SOURCES.md](SOURCES.md#physical-unit-power-readings-2026-11-12).

### PDF unit coverage (0.7.0)

The packaged [PDF unit inventory](nb_tn/pdf_unit_inventory.json) contains **67
hand-audited rows** covering every named quantity/unit in tables 1–5 and 7–9,
the hectare/decare definitions, and the later flow-rate expressions. Table 6's
prefixes are tested separately. Each row has independently written Bokmål and
Nynorsk expectations; CI exercises the complete inventory in both languages.
The low-level SI unit parser retains the PDF's tonne readings for `t`, `t/h`
and `t/min`, but the free-text normalizer now flags these three inventory forms
for review because Norwegian `t` also means hours. Tests verify both the
underlying unit inventory and this conservative free-text behavior.

| PDF coverage | Supported notation / examples |
| --- | --- |
| Base quantities and Celsius | `m`, `kg`, `s`, `A`, `K`, `mol`, `cd`, `°C` |
| Area, volume, speed, acceleration, angular speed | `m²`, `m³`, `m/s`, `m/s²`, `rad/s` |
| Density, viscosity, concentration, luminance | `kg/m³`, `m²/s`, `Pa s`, `mol/m³`, `cd/m²` |
| All named derived units | `rad`, `sr`, `Hz`, `N`, `Pa`, `J`, `W`, `C`, `V`, `F`, `Ω`, `S`, `Wb`, `T`, `H`, `lm`, `lx`, `Bq`, `Gy`, `Sv`, `kat` |
| Heat capacity, specific heat, field strength, permittivity, molar entropy | `J/K`, `J/(kg·K)`, `V/m`, `F/m`, `J/(mol·K)` |
| Other multiples and angles | `l`/`L`, `t`, `bar`, `a`/`ar`, `ha`, `daa`, `deg`, `gon` |
| Maritime, mercury pressure, gemstones | `nautisk mil`/`nautiske mil`, `kn`, `mmHg`, `karat` |
| Later flow quantities | `m³/h`, `t/h`, `t/min` |

Balanced parentheses and implicit products now work, including `J/(kg K)`,
`kg m-3`, and base-unit forms such as `m-2 kg-1 s4 A2`. Only registered symbols
extend a unit candidate across whitespace, so `5 m kabel` remains `fem meter
kabel`. An ASCII product dot is accepted as `kg.s` or `kg . s`, not across a
sentence boundary such as `kg. S`. Division is left-associative: `m/s kg`
means `(m/s)·kg`; use parentheses for a whole denominator. No unit cancellation,
dimensional inference or numerical conversion is performed. Expressions are
limited to 512 characters, 64 factors and nesting depth 8; group powers such
as `(m/s)^2`, equations and general symbolic algebra remain unsupported.

Angular minutes/seconds use explicit `arcmin`/`arcsec` aliases, a degree-led
chain, or an explicit `vinkel` cue:

| Input | Bokmål | Nynorsk |
| --- | --- | --- |
| `30°15′20″` | `tretti grader femten bueminutter tjue buesekunder` | `tretti grader femten bogeminutt tjue bogesekund` |
| `vinkelen er 5′` | `vinkelen er fem bueminutter` | `vinkelen er fem bogeminutt` |
| `120 mmHg` | `hundre og tjue millimeter kvikksølv` | same |
| `1 nautisk mil` | `en nautisk mil` | `ei nautisk mil` |

ASCII `'`/`"` also work in degree-led or explicitly cued angles. Bare Unicode
prime quantities (`5′`, `5″`) require review because they might mean feet/inches;
unqualified ASCII quote marks remain punctuation, not an assumed angle unit.
Arcminute/arcsecond components in a degree-led chain must be nonnegative and
below 60. Fractional minutes cannot also have a following seconds component.
These ambiguity rules and the explicit `arcmin`/`arcsec` spellings are application
policies, not new symbols claimed from the PDF.

This is complete coverage of the document's **unit inventory**, not a promise
to interpret every possible physical equation or infer a magnitude from a bare
number. Equation evaluation and chemical identifiers remain outside this unit
extension; bounded scientific-number support is described below. The historical PDF's direct
download is now hash-recorded; its old SI definitions and legal restrictions
are still not imported. See [SOURCES.md](SOURCES.md#pdf-unit-inventory-and-compound-notation-2026-11-12).

### Temperature and C/F/K ambiguity

Temperature units require a numeric quantity: `°C` means degrees Celsius,
`°F` degrees Fahrenheit, and `K` kelvin (without “degrees”). Bare `C`, `F`,
and `K` are never expanded into unit names. Crucially, a number followed by `C`
means coulombs and `F` means farads, **not** Celsius or Fahrenheit; even a nearby
word such as “temperaturen” does not silently change the symbol's meaning.
Write the degree sign for Celsius/Fahrenheit. `°K` is unsupported and flagged.

Actual tested readings:

| Input | Bokmål | Nynorsk |
|---|---|---|
| `20 °C` | tjue grader celsius | same |
| `−5 °C` | minus fem grader celsius | same |
| `1 °C` | en grad celsius | ein grad celsius |
| `-1 °F` | minus en grad fahrenheit | minus ein grad fahrenheit |
| `68 °F` | sekstiåtte grader fahrenheit | same |
| `273,15 K` | to hundre og syttitre komma femten kelvin | same |
| `−0,25 °C` | minus null komma tjuefem grader celsius | same |
| `1,21 °F` | en komma tjueen grader fahrenheit | ein komma tjueein grader fahrenheit |
| `20 C` / `20 F` | tjue coulomb / tjue farad | same |
| `20°` | tjue grader | same |

Bare degree quantities keep the neutral word `grader`: the normalizer does not
infer whether they describe an angle or a temperature, nor invent a scale.
ASCII hyphen and mathematical minus signs work for negative values; attached
forms such as `20°C` work too. Decimal readings respect `decimal_style`, including
`digits`. These rules read the supplied notation, not its physical validity:
they do not convert temperatures or reject negative kelvin values. Standalone
`°C`/`°F` without a number remain unchanged and flagged for review. Initial-like
forms such as `2 C. Dahl` are also preserved and flagged.

### Scientific numbers

These examples use `scientific_units=True`, the default. With
`scientific_units=False`, a standalone ASCII single-letter symbol after a
quantity is spelled as a letter unless it is an everyday unit (`m`, `g`, `l`,
`L`, `s`, `h`). `kg` and `mg` are unchanged too. This applies to decimals,
fractions, ranges and scientific numbers, without changing numeric speech.
Explicit compound/powered/prefixed forms such as `V/m`, `A²`, `m/s²` and `kW`
continue to expand. Bare letters without quantities and ambiguous personal-name
contexts retain their existing treatment. This is a reading preference, not
automatic scientific-topic detection.

Single-letter unit symbols (`N`, `C`, `J`, `W`, and others) are expanded only in
a numeric quantity, never as bare letters or personal initials. A preceding
number is necessary but not always sufficient: `2 N. Hansen` remains unchanged
and flagged because it could be a numbered name. A sentence boundary such as
`2 N. Neste ...` has the same ambiguity and also requires review. Initials at
the start of a line can still be spelled as letters by the existing enumeration
rule; they do not become unit names. Compound unit expressions inherit their
numeric context. The existing bare `m²`/`cm³` area/volume aliases are a separate,
explicit exception, not a rule for bare single letters.

Both languages read the notation explicitly, without expanding it into a long
decimal or rounding it. Bokmål remains the default.

```python
from nb_tn import NorwegianNormalizer

NorwegianNormalizer().normalize("1,2 × 10⁻³")
# en komma to ganger ti opphøyd i minus tre
NorwegianNormalizer(language="nn").normalize("1.2e-3")
# ein komma to gonger ti opphøgd i minus tre
NorwegianNormalizer(decimal_style="digits").normalize("1.25e-3")
# en komma to fem ganger ti opphøyd i minus tre
```

Supported forms: `1,2 × 10⁻³`, `1,2·10^-3`, `1,2 ⋅ 10^−3`, `1,2*10^-3`,
`1.2e-3`, `1,2E−3`, and standalone `10⁻³` / `10^-3`. Multiplication and caret
notation allow horizontal whitespace, including nonbreaking spaces; machine
`e`/`E` notation does not. Explicit positive signs are spoken as `pluss`.
The coefficient may be signed, zero, or outside the canonical standard-form
interval: `12,0 × 10^3` is read as written, not changed into `1,2 × 10^4`.

Decimal commas are required in displayed multiplication. A decimal point is
accepted **only inside explicit machine notation**, independently of the
currency locale; it is always spoken as `komma`. The existing `natural` decimal
mode remains the default (`1.25e-3` starts `en komma tjuefem` / `ein komma tjuefem`).
`digits` remains available. Trailing zeros are preserved in speech.

Coefficients have at most 18 digits, without grouping or leading integer zeros
except `0`; exponents are integers from −999 to 999, without leading zeros.
Space-separated physical units, including `m/s²` and `J/(kg K)`, use the existing
unit parser. Exact decimal representation is used only to select singular at
absolute value one and plural otherwise; the scientific value is not expanded.
Coefficient and exponent numerals keep their standalone grammatical forms.

Conservative review policy (`analyze(...).needs_review`):

- Integer mantissa + unsigned `e`/`E` exponent (`1e3`, `1E3`): identifier ambiguity.
  Use `1e+3` or `1 × 10^3` when scientific notation is intended.
- ASCII `x`, missing exponent markers, mixed decimal separators, grouped
  coefficients, spaced machine notation, malformed/fractional/symbolic exponents,
  and out-of-bounds values remain unchanged and flagged.
- Parenthesized/braced exponents, signed standalone powers (`-10³`), scientific
  ranges, attached units (`1.2e-3kg`), currency amounts and percentages require
  review. Use whitespace before units. General equations are not interpreted.

These are bounded recognition rules, not universal identifier detection: even
`1e-3` can be an identifier in a domain-specific corpus. Review source context.
Unrecognized ordinary words after a quantity remain prose; unit-shaped errors
are flagged. Inspect issues before sending text to TTS.

Actual full-sentence outputs, covered by exact tests:

```text
Bokmål input:
Den 8. mai 2026 målte vi 1,2 × 10⁻³ m/s² etter § 2-1; prisen var kr 150,50.
Output:
Den åttende mai tjue tjueseks målte vi en komma to ganger ti opphøyd i minus tre meter per sekund i annen etter paragraf to en; prisen var hundre og femti kroner og femti øre.

Nynorsk input:
Den 8. mai 2026 målte vi 1.2e-3 m/s² etter § 2-1; prisen var kr 150,50.
Output:
Den åttande mai tjue tjueseks målte vi ein komma to gonger ti opphøgd i minus tre meter per sekund i andre etter paragraf to ein; prisen var hundre og femti kroner og femti øre.
```

The mathematical basis is [NDLA](https://ndla.no/r/matematikk-1p/tierpotenser-og-tall-pa-standardform/34909c868c)
and [Matematikk.org](https://www.matematikk.org/artikkel.html?tid=188004);
the precise spoken wording and ambiguity rules are project policy, not a
prescribed TTS standard. All supplied references, supplementary investigation,
and provenance boundaries are recorded in
[SOURCES.md](SOURCES.md#scientific-number-proposal-2026-11-13).

### Mixed full-sentence examples

Actual default outputs, also tested as exact strings:

```text
Bokmål input:
Den 8. mai 2026 målte vi 9,81 m/s² og 2 A², og kontrollen kostet kr 150,50 etter § 2-1.

Bokmål output:
Den åttende mai tjue tjueseks målte vi ni komma åttien meter per sekund i annen og to ampere i annen, og kontrollen kostet hundre og femti kroner og femti øre etter paragraf to en.

Nynorsk input:
Den 8. mai 2026 målte vi 9,81 m/s² og 2 A², og kontrollen kosta kr 150,50 etter § 2-1.

Nynorsk output:
Den åttande mai tjue tjueseks målte vi ni komma åttiein meter per sekund i andre og to ampere i andre, og kontrollen kosta hundre og femti kroner og femti øre etter paragraf to ein.
```

`l` and `L` both mean liter; `µ`, `μ` and ASCII `u` are accepted micro-prefix
aliases, and `Ω` is accepted as an ohm-sign alias for `Ω`. Incorrect casing such
as `mhz` or `mw` is **flagged**, not guessed as MHz/MW/mW. The existing lowercase
`°c` input alias is retained explicitly. In ordinary spaced text, `1 dag` means
`en dag`; the parser does not mistake the Norwegian day noun for dekagram.

Unsupported symbol-shaped quantity expressions are retained as whole spans
with review issues, including `5 XYZ`, `5 mhz`, `5 m//s`, and `5 W/(m²·XYZ)`. The
detector considers known symbols with wrong casing, uppercase/mixed-case tokens,
attached unit-like strings, and explicit unit operators. It does not label every
ordinary count noun as a unit: `5 personer` becomes `fem personer`. Consequently,
an unknown separated lowercase word such as `5 frobnitz` is not guaranteed to
be flagged. Uppercase prose can conversely trigger conservative review.
Balanced known-unit groups and implicit products are supported as above;
malformed grouping or an unknown factor keeps the quantity for review.

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

### Full-sentence policy comparisons (0.10.1)

These exact outputs are regression-tested in `tests/test_full_sentence_policies.py`.
Unless noted, the settings are `year_style="pairs"`, `scientific_units=True`,
`english_unit_aliases=False`, and `decimal_style="natural"`.

**Bokmål input:**

```text
Den 8. mai 2026 målte vi 1,2 × 10⁻³ A, 230 V og 60 W ved −5 °C; kontrollen kostet $20 og ¥1,25 etter § 2-1.
```

Scientific units on (default), no review issues:

```text
Den åttende mai tjue tjueseks målte vi en komma to ganger ti opphøyd i minus tre ampere, to hundre og tretti volt og seksti watt ved minus fem grader celsius; kontrollen kostet tjue dollar og en komma tjuefem yuan etter paragraf to en.
```

Scientific units off (`scientific_units=False`), no review issues:

```text
Den åttende mai tjue tjueseks målte vi en komma to ganger ti opphøyd i minus tre a, to hundre og tretti ve og seksti dobbeltve ved minus fem grader celsius; kontrollen kostet tjue dollar og en komma tjuefem yuan etter paragraf to en.
```

**Nynorsk input:**

```text
Den 8. mai 2026 målte vi 1,2 × 10⁻³ A, 230 V og 60 W ved −5 °C; kontrollen kosta $20 og ¥1,25 etter § 2-1.
```

Scientific units on (default), no review issues:

```text
Den åttande mai tjue tjueseks målte vi ein komma to gonger ti opphøgd i minus tre ampere, to hundre og tretti volt og seksti watt ved minus fem grader celsius; kontrollen kosta tjue dollar og ein komma tjuefem yuan etter paragraf to ein.
```

Scientific units off, no review issues:

```text
Den åttande mai tjue tjueseks målte vi ein komma to gonger ti opphøgd i minus tre a, to hundre og tretti ve og seksti dobbeltve ved minus fem grader celsius; kontrollen kosta tjue dollar og ein komma tjuefem yuan etter paragraf to ein.
```

**Everyday units and the revised 2000s reading**, with either scientific setting:

```text
Input (both languages):
I året 2005 målte vi 2 m, 3 kg og 5 mg i løpet av 10 s og 2 h.
Bokmål:
I året to tusen og fem målte vi to meter, tre kilo og fem milligram i løpet av ti sekunder og to timer.
Nynorsk:
I året to tusen og fem målte vi to meter, tre kilo og fem milligram i løpet av ti sekund og to timar.
```

**Default review flags:** only unresolved spans are preserved; recognized
currency amounts in the same sentence still normalize. All rows below have
`needs_review=True`, with either scientific-unit setting.

| Language | Input | Actual output | Flagged spans |
|---|---|---|---|
| Bokmål | `Turen tok 2 t og kostet $20.` | `Turen tok 2 t og kostet tjue dollar.` | `2 t`: time/tonn ambiguity |
| Nynorsk | `Turen tok 2 t og kosta $20.` | `Turen tok 2 t og kosta tjue dollar.` | `2 t`: time/tonn ambiguity |
| Bokmål | `Turen tok 2 hrs og kostet ¥20.` | `Turen tok 2 hrs og kostet tjue yuan.` | `2 hrs`: English alias disabled |
| Nynorsk | `Turen tok 2 hrs og kosta ¥20.` | `Turen tok 2 hrs og kosta tjue yuan.` | `2 hrs`: English alias disabled |
| Both | `Pausen varte 5 mins og 30 secs.` | `Pausen varte 5 mins og 30 secs.` | `5 mins`, `30 secs`: English aliases disabled |

Enabling `english_unit_aliases=True` removes the English-alias issues, but does
not resolve ambiguous `t`. Actual enabled outputs:

```text
Bokmål:
Turen tok to timer og kostet tjue yuan.
Pausen varte fem minutter og tretti sekunder.
Nynorsk:
Turen tok to timar og kosta tjue yuan.
Pausen varte fem minutt og tretti sekund.
```

Standard time forms need no opt-in and produce no review issues:

```text
Input (both languages):
Turen tok 2 h, og pausen varte 5 min og 30 sek.
Bokmål:
Turen tok to timer, og pausen varte fem minutter og tretti sekunder.
Nynorsk:
Turen tok to timar, og pausen varte fem minutt og tretti sekund.
```

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

The Nynorsk suite adds independent expected outputs, full sentences,
gender/inflection cases, shared-syntax span parity, concurrent language isolation,
both decimal modes, rejection behavior and installed provenance checks.

Other limitations include English decimal-point conventions outside explicit
scientific/currency input, unknown acronym pronunciations, currencies outside
the listed codes and forms, scientific forms outside the bounded support above,
arbitrary unit algebra, pronunciation changes across Norwegian dialects, and normalization
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

Nynorsk number/inflection references additionally include **Nynorsksenteret**,
**Nynorskordboka** (Språkrådet and the University of Bergen), and selected
**Unicode CLDR 49** metadata. Their roles and application-specific adaptations
are documented separately; no upstream normalizer implementation, dictionary
database, grammar document or model is bundled for this extension. The small
CLDR-derived metadata selection is attributed in NOTICE and distributed under
the included [Unicode License V3](LICENSES/Unicode-3.0.txt).

The versioned [Nynorsk provenance manifest](nb_tn/provenance.json) ships in the
Python package. It maps implementation artifacts to references and derivation,
records artifact SHA-256 hashes, pins CLDR to an exact revision, and records the
inspected grammar PDF digest. CI checks the artifact hashes and references:

```bash
python -m nb_tn.provenance          # Offline; also works after installation.
python -m nb_tn.provenance --fetch  # Optional verification of hash-recorded sources.
```

There are no network calls during normalization or ordinary tests. Reference-only
web pages are cited with an access date, not claimed to be immutable snapshots;
`--fetch` verifies only sources with recorded hashes. Upstream changes or missing
URLs cause verification to fail rather than refreshing provenance silently.
Hashes provide byte-level traceability and detect unrecorded artifact changes;
they do not prove authorship or linguistic correctness. Existing Bokmål
investigation provenance remains in SOURCES.md rather than being retroactively
claimed as fully hash-pinned by the new Nynorsk record.

When changing a tracked module, review its source/derivation record and update
its artifact digest deliberately. New borrowed metadata needs an appropriate
reference and license notice; changing hashes merely to silence CI is not a
provenance review. The checker never rewrites the manifest.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). This license covers
the first-party implementation and documentation in this repository. Selected
CLDR-derived metadata retains Unicode-3.0 terms as described above. The external models and
projects credited above retain their own licenses and are not bundled here.
