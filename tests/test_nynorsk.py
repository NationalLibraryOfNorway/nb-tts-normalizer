"""Hand-authored Nynorsk expectations; references are recorded in SOURCES.md.

These are text regression tests, not native-speaker or acoustic evaluations.
Expected outputs are not produced by translating the Bokmaal implementation.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.channels import channel_readings
from nb_tn.currencies import CurrencyPolicy
from nb_tn.numbers import cardinal, decimal_fraction, ordinal, year
from nb_tn.profiles import get_profile
from nb_tn.readings import DASH_CHARS, fraction, version
from nb_tn.units import parse_unit
from nb_tn.voxcpm import generate_norwegian


class NynorskTests(unittest.TestCase):
    def check_cases(self, cases, **options):
        normalizer = NorwegianNormalizer(language="nn", **options)
        for original, expected in cases.items():
            with self.subTest(original=original, options=options):
                report = normalizer.analyze(original)
                self.assertEqual(report.text, expected)
                self.assertFalse(report.issues, report.issues)
                self.assertEqual(normalizer.normalize(expected), expected)
                rebuilt = original
                last_end = 0
                for change in report.replacements:
                    self.assertGreaterEqual(change.start, last_end)
                    self.assertEqual(original[change.start:change.end], change.original)
                    last_end = change.end
                for change in reversed(report.replacements):
                    rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
                self.assertEqual(rebuilt, expected)

    def test_cardinals_scales_and_gender(self):
        for number, expected in {
            0: "null", 1: "ein", 21: "tjueein", 31: "trettiein", 99: "nittini",
            100: "hundre", 101: "hundre og ein", 201: "to hundre og ein",
            1000: "eitt tusen", 1001: "eitt tusen og ein", 1101: "eitt tusen hundre og ein",
            1000000: "ein million", 2000000: "to millionar",
            1000000000: "ein milliard", 2000000000: "to milliardar",
            -21: "minus tjueein",
            999999999999: "ni hundre og nittini milliardar ni hundre og nittini millionar ni hundre og nittini tusen ni hundre og nittini",
        }.items():
            with self.subTest(number=number):
                self.assertEqual(cardinal(number, language="nn"), expected)
        for gender, expected in (("m", "ein"), ("f", "ei"), ("n", "eitt")):
            self.assertEqual(cardinal(1, gender=gender, language="nn"), expected)
            self.assertEqual(cardinal(101, gender=gender, language="nn"), "hundre og " + expected)
        self.assertEqual(cardinal(1, neuter=True, language="nn"), "eitt")
        for number in (10**12, -10**12, 1.0, True):
            with self.assertRaises(ValueError):
                cardinal(number, language="nn")
        with self.assertRaises(ValueError):
            cardinal(1, gender="unknown", language="nn")

    def test_ordinals_dates_and_years(self):
        expected = ("første", "andre", "tredje", "fjerde", "femte", "sjette", "sjuande",
                    "åttande", "niande", "tiande", "ellevte", "tolvte", "trettande",
                    "fjortande", "femtande", "sekstande", "syttande", "attande", "nittande",
                    "tjuande", "tjueførste", "tjueandre", "tjuetredje", "tjuefjerde",
                    "tjuefemte", "tjuesjette", "tjuesjuande", "tjueåttande", "tjueniande",
                    "trettiande", "trettiførste")
        for number, words in enumerate(expected, 1):
            self.assertEqual(ordinal(number, language="nn"), words)
        for number, words in {40: "førtiande", 47: "førtisjuande", 100: "hundrede",
                              101: "hundre og første", 1000: "tusende",
                              1007: "tusen og sjuande"}.items():
            self.assertEqual(ordinal(number, language="nn"), words)
        self.assertEqual(year(1901, language="nn"), "nitten null ein")
        self.assertEqual(year(2001, language="nn"), "tjue null ein")
        self.check_cases({
            "8. mai 2026": "åttande mai tjue tjueseks",
            "8 . 5 . 26": "åttande mai tjue tjueseks",
            "2026-05-08": "åttande mai tjue tjueseks",
            "8/5/2026": "åttande mai tjue tjueseks",
            "8mai2026": "åttande mai tjue tjueseks",
            "8. sept. 2026": "åttande september tjue tjueseks",
            "dato 08052026": "dato åttande mai tjue tjueseks",
            "dato 20260508": "dato åttande mai tjue tjueseks",
            "den 8/5": "den åttande mai",
            "29. februar 2024": "tjueniande februar tjue tjuefire",
            "8.–9. mai 2026": "åttande til niande mai tjue tjueseks",
            "8. mai–9. juni 2026": "åttande mai til niande juni tjue tjueseks",
            "08.05.2026–09.05.2026": "åttande mai tjue tjueseks til niande mai tjue tjueseks",
            "året 1901": "året nitten null ein",
            "8. gong": "åttande gong",
        })
        self.check_cases({"8.5.49": "åttande mai nitten førtini"}, two_digit_year_pivot=40)

    def test_both_decimal_styles_and_precision(self):
        self.check_cases({
            "1,75": "ein komma syttifem", "3,21": "tre komma tjueein",
            "3,10": "tre komma ti", "3,01": "tre komma null ein",
            "3,00": "tre komma null null", "3,141": "tre komma ein fire ein",
            "−0,21 %": "minus null komma tjueein prosent",
            "1,21‰": "ein komma tjueein promille",
        })
        self.check_cases({
            "1,75": "ein komma sju fem", "3,21": "tre komma to ein",
            "3,01": "tre komma null ein", "3,141": "tre komma ein fire ein",
            "1,21 kWh": "ein komma to ein kilowattimar",
            "1,21–2,21 %": "ein komma to ein til to komma to ein prosent",
            "CHF 1,21": "ein komma to ein sveitsiske franc",
            "tilhøvet er 1,21:2,21": "tilhøvet er ein komma to ein til to komma to ein",
        }, decimal_style="digits")
        self.assertEqual(decimal_fraction("21", language="nn"), "tjueein")
        self.assertEqual(decimal_fraction("01", language="nn"), "null ein")

    def test_currencies_and_split_fields(self):
        self.check_cases({
            "NOK 1,01": "ei krone og eitt øre", "1 kr 1 øre": "ei krone og eitt øre",
            "-1 kr 1 øre": "minus ei krone og eitt øre",
            "kr 150,-": "hundre og femti kroner",
            "$1,01": "ein dollar og ein cent", "¥1,21": "ein komma tjueein yuan",
            "EUR 1,01": "ein euro og ein cent", "GBP 1,01": "eitt britisk pund og ein penny",
            "SEK 1,01": "ei svensk krone og eitt øre", "DKK 1": "ei dansk krone",
            "CAD 1": "ein kanadisk dollar", "AUD 1": "ein australsk dollar",
            "CHF 1,01": "ein komma null ein sveitsiske franc", "JPY 1": "ein japansk yen",
            "KWD 2,001": "to kuwaitiske dinarar og ein fils",
            "2 kuwaitiske dinarar": "to kuwaitiske dinarar",
            "NOK 1–2": "ei til to kroner",
            "CHF 1,21–2,21": "ein komma tjueein sveitsiske franc til to komma tjueein sveitsiske franc",
            "$1 CAD": "ein kanadisk dollar", "¥1 JPY": "ein japansk yen",
            "2 000 000 kr": "to millionar kroner",
        })
        self.check_cases({"$1.01": "ein dollar og ein cent",
                          "CHF 1.21": "ein komma tjueein sveitsiske franc"}, currency_locale="en-US")
        self.check_cases({"$1": "ein australsk dollar", "¥1": "ein japansk yen"},
                         symbol_currencies={"$": "AUD", "¥": "JPY"})

    def test_units_gender_prefixes_and_powers(self):
        self.check_cases({
            "1 min og 2 min": "eitt minutt og to minutt", "1 s og 2 s": "eitt sekund og to sekund",
            "2 ms": "to millisekund", "1 h og 2 h": "ein time og to timar",
            "1 kWh og 2 kWh": "ein kilowattime og to kilowattimar",
            "2 MWh og 2 mAh": "to megawattimar og to milliamperetimar",
            "2 rad og 2 sr": "to radianar og to steradianar",
            "1 stk. og 2 stk.": "eitt stykk og to stykk.",
            "9,81 m/s²": "ni komma åttiein meter per sekund i andre",
            "3,05m3 og 75m2": "tre komma null fem kubikkmeter og syttifem kvadratmeter",
            "2 kg/m³": "to kilo per kubikkmeter", "2 s^7": "to sekund i sjuande potens",
            "1,21 min": "eitt komma tjueein minutt", "1–2 min": "eitt til to minutt",
            "1,21–2,21 kWh": "ein komma tjueein til to komma tjueein kilowattimar",
            "-1 °C og 2 °C": "minus ein grad celsius og to grader celsius",
        })
        self.assertEqual(parse_unit("kWh", language="nn").plural, "kilowattimar")
        self.assertEqual(parse_unit("min", language="nn").number_gender, "n")

    def test_fractions_ratios_and_unicode_ranges(self):
        self.check_cases({
            "1/2": "ein halv", "3/4": "tre firedelar", "2/13": "to trettendelar",
            "1/1": "ein over ein", "1½ kr": "ei og ei halv krone",
            "1/2 min": "eitt halvt minutt", "1 1/2 min": "eitt og eitt halvt minutt",
            "1/3 min": "ein tredel minutt", "1/2–3/4 kr": "ei halv til tre firedelar krone",
            "tilhøvet er 1:10": "tilhøvet er ein til ti",
            "blandingstilhøvet på 1:100": "blandingstilhøvet på ein til hundre",
            "1 : 10": "ein til ti", "format 16:9": "format seksten til ni",
        })
        for dash in DASH_CHARS:
            self.check_cases({"1,21" + dash + "2,21 kWh": "ein komma tjueein til to komma tjueein kilowattimar"})
        self.assertEqual(fraction(1, 2, gender="f", language="nn"), "ei halv")

    def test_legal_enumeration_phones_versions_and_brands(self):
        self.check_cases({
            "jf. § 2-1 (8) (b)": "jamfør paragraf to ein åttande ledd bokstav be",
            "§§ 1–3": "paragrafane ein til tre",
            "§§ 2-1 til 2-3": "paragrafane to ein til to tre",
            "8. ledd og bokstav b": "åttande ledd og bokstav be",
            "1. Svar\na. Les\nVIII. Send": "ein. Svar\na. Les\nåtte. Send",
            "• Svar": "punkt. Svar",
            "tlf. +47 123 45 678": "telefon pluss fire sju ein to tre fire fem seks sju åtte",
            "kl. 01.01": "klokka ein null ein", "01:01–02:01": "ein null ein til to null ein",
            "v1.21.08": "versjon ein punkt tjueein punkt null åtte",
            "versjonen 1.1.1": "versjonen ein punkt ein punkt ein",
            "NRK P1+ og TV 2 Sport 1": "enn err kå pe ein pluss og te ve to sport ein",
            "TV Norge og NRK Nyheter": "te ve Norge og enn err kå nyheter",
        })
        self.assertEqual(version("1.21.08", language="nn"), "ein punkt tjueein punkt null åtte")
        self.assertEqual(channel_readings("nn")["P1"], "pe ein")

    def test_abbreviations_and_untouched_prose(self):
        self.check_cases({
            "t.d. 1 kg, m.a. 2 kg, osb.": "til dømes ein kilo, mellom anna to kilo, og så bortetter.",
            "m.m. og osv.": "med meir og og så vidare.",
            "bl.a. 1 kg, dvs. 1 kg": "blant anna ein kilo, det vil seie ein kilo",
            "d.e. 1 kg": "det er ein kilo",
            "Eg kjøper 1 kg. Ho betaler 1 kr.": "Eg kjøper ein kilo. Ho betaler ei krone.",
            # Neither input prose nor custom dictionary values are translated.
            "Hun kjøper 1 kg.": "Hun kjøper ein kilo.",
            "Hei, Åse!\n  Dette er teksten min.": "Hei, Åse!\n  Dette er teksten min.",
        })
        self.check_cases({"API og Min Radio 1": "mitt a pe i og min kanal"},
                         acronyms={"API": "mitt a pe i"}, channels={"Min Radio 1": "min kanal"})

    def test_full_sentences(self):
        self.check_cases({
            "Etter § 2-1 skal 1,75 m kabel koste kr 150,50 ved levering 8. mai 2026.":
                "Etter paragraf to ein skal ein komma syttifem meter kabel koste hundre og femti kroner og femti øre ved levering åttande mai tjue tjueseks.",
            "Den 8 . 5 . 2026 vart 75 m2 leigde ut for $125,75, med eit tillegg på 3,14 % etter §§ 3–5.":
                "Den åttande mai tjue tjueseks vart syttifem kvadratmeter leigde ut for hundre og tjuefem dollar og syttifem cent, med eit tillegg på tre komma fjorten prosent etter paragrafane tre til fem.",
            "Etter § 7 skal prisen 8. juni 2026 vere ¥1,21 per 1,75 kWh, medan toleransen er 0,05 %.":
                "Etter paragraf sju skal prisen åttande juni tjue tjueseks vere ein komma tjueein yuan per ein komma syttifem kilowattimar, medan toleransen er null komma null fem prosent.",
        })

    def test_invalid_and_ambiguous_forms_remain_whole_in_both_languages(self):
        samples = ("31. februar 2026", "29. februar 2025", "2026-02-30", "25:99", "AB123",
                   "3.14", "0012", "1000000", "5 m//s", "5 kwh", "kr 1,234", "JPY 1,5",
                   "1000000000000 kr", "§§ 2-1-3", "1/0", "https://example.no/1.2.3")
        for text in samples:
            with self.subTest(text=text):
                nb = NorwegianNormalizer().analyze(text)
                nn = NorwegianNormalizer(language="nn").analyze(text)
                self.assertEqual(nn.text, text)
                self.assertEqual(nn.issues, nb.issues)
                self.assertTrue(nn.needs_review)
        for style in ("natural", "digits"):
            report = NorwegianNormalizer(language="nn", decimal_style=style,
                                          symbol_currencies={"$": None}).analyze("$1,21")
            self.assertEqual(report.text, "$1,21")
            self.assertTrue(report.needs_review)

    def test_shared_syntax_has_same_source_spans(self):
        for text in ("Åse: 1,21; 1,21.", "NOK 1,01; 8. mai 2026; 2 kWh; §§ 1–3.",
                     "tlf. +47 12345678 og v1.21.01", "1/2 min; kl. 01.01; 3,21 %"):
            nb = NorwegianNormalizer().analyze(text)
            nn = NorwegianNormalizer(language="nn").analyze(text)
            self.assertEqual([(r.start, r.end, r.original, r.category) for r in nb.replacements],
                             [(r.start, r.end, r.original, r.category) for r in nn.replacements])
            self.assertEqual(nb.issues, nn.issues)

    def test_language_is_explicit_validated_and_instance_local(self):
        for invalid in ("no", "auto", "nn-NO", "en", "", None, []):
            for factory in (NorwegianNormalizer, CurrencyPolicy, get_profile):
                with self.subTest(invalid=invalid, factory=factory):
                    with self.assertRaisesRegex(ValueError, "language"):
                        factory(language=invalid)
        nb, explicit_nb, nn = NorwegianNormalizer(), NorwegianNormalizer(language="nb"), NorwegianNormalizer(language="nn")
        samples = ("1,21", "NOK 1,01", "2 kWh", "8. mai 2026", "§§ 1–3", "v1.21.1", "P1+")
        for text in samples:
            self.assertEqual(nb.analyze(text), explicit_nb.analyze(text))
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(n.normalize, "NOK 1,01; 2 kWh") for n in (nb, nn) * 10]
            for i, job in enumerate(jobs):
                self.assertEqual(job.result(), "ei krone og eitt øre; to kilowattimar" if i % 2
                                 else "en krone og ett øre; to kilowattimer")
        with self.assertRaises(TypeError):
            nn.profile.abbreviations["t.d."] = "changed"

    def test_cli_language_choices_and_json_review(self):
        for args, text, expected, code in (
            ([], "NOK 1,01", "en krone og ett øre", 0),
            (["--language", "nb"], "NOK 1,01", "en krone og ett øre", 0),
            (["--language", "nn"], "NOK 1,01", "ei krone og eitt øre", 0),
            (["--language", "nn", "--decimal-style", "digits"], "1,21", "ein komma to ein", 0),
            (["--language", "nn", "--currency-locale", "en-US"], "$1.01", "ein dollar og ein cent", 0),
            (["--language", "nn"], "31. februar 2026", "31. februar 2026", 2),
        ):
            result = subprocess.run([sys.executable, "-m", "nb_tn", "--strict", "--json", *args],
                                    input=text, text=True, capture_output=True)
            self.assertEqual(result.returncode, code, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["text"], expected)
            self.assertEqual(report["needs_review"], bool(code))
        invalid = subprocess.run([sys.executable, "-m", "nb_tn", "--language", "auto", "1"],
                                 text=True, capture_output=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(invalid.stdout, "")

    def test_voxcpm_adapter_and_strict_review(self):
        class FakeModel:
            def __init__(self):
                self.calls = []

            def generate(self, **kwargs):
                self.calls.append(kwargs)
                return "audio"

        model = FakeModel()
        nn = NorwegianNormalizer(language="nn")
        audio, report = generate_norwegian(model, "NOK 1,01 og 2 kWh", normalizer=nn, seed=7)
        self.assertEqual(audio, "audio")
        self.assertEqual(report.text, "ei krone og eitt øre og to kilowattimar")
        self.assertEqual(model.calls, [{"text": report.text, "normalize": False, "seed": 7}])
        with self.assertRaises(ValueError):
            generate_norwegian(model, "31. februar 2026", normalizer=nn)
        self.assertEqual(len(model.calls), 1)
