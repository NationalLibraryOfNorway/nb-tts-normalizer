import json
import subprocess
import sys
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.currencies import CurrencyPolicy
from nb_tn.numbers import cardinal
from nb_tn.voxcpm import generate_norwegian


class DecimalStyleTests(unittest.TestCase):
    def check_cases(self, cases, **options):
        normalizer = NorwegianNormalizer(**options)
        for original, expected in cases.items():
            with self.subTest(original=original, options=options):
                report = normalizer.analyze(original)
                self.assertEqual(report.text, expected)
                self.assertFalse(report.issues, report.issues)
                self.assertEqual(normalizer.normalize(expected), expected)
                rebuilt = original
                for change in reversed(report.replacements):
                    self.assertEqual(original[change.start:change.end], change.original)
                    rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
                self.assertEqual(rebuilt, expected)

    def test_natural_default_and_preserved_precision(self):
        self.check_cases({
            "3,14": "tre komma fjorten", "1,75": "en komma syttifem",
            "3,10": "tre komma ti", "3,20": "tre komma tjue",
            "3,05": "tre komma null fem", "3,00": "tre komma null null",
            "3,01": "tre komma null en", "3,09": "tre komma null ni",
            "3,1": "tre komma en", "3,0": "tre komma null",
            "3,100": "tre komma en null null",
            "3,14159": "tre komma en fire en fem ni",
            "−0,75": "minus null komma syttifem",
            "-0,05": "minus null komma null fem",
            "Åse: 3,14; 3,14!": "Åse: tre komma fjorten; tre komma fjorten!",
        })

    def test_every_two_digit_fraction_in_both_modes(self):
        natural = NorwegianNormalizer()
        digits = NorwegianNormalizer(decimal_style="digits")
        for value in range(100):
            fraction = f"{value:02d}"
            digit_words = " ".join(cardinal(int(d)) for d in fraction)
            with self.subTest(fraction=fraction):
                self.assertEqual(natural.normalize("3," + fraction),
                                 "tre komma " + (cardinal(value) if value >= 10 else digit_words))
                self.assertEqual(digits.normalize("3," + fraction), "tre komma " + digit_words)

    def test_structured_decimal_readings(self):
        self.check_cases({
            "9,81m/s2": "ni komma åttien meter per sekund i annen",
            "1,75 min": "ett komma syttifem minutter",
            "3,14–3,75 kg": "tre komma fjorten til tre komma syttifem kilo",
            "3,14—3,75": "tre komma fjorten til tre komma syttifem",
            "3,14–3,75 %": "tre komma fjorten til tre komma syttifem prosent",
            "3,14 %": "tre komma fjorten prosent",
            "3,14‰": "tre komma fjorten promille",
            "forhold 1,75:3,14": "forhold en komma syttifem til tre komma fjorten",
        })

    def test_technical_mode_reaches_all_decimal_paths(self):
        self.check_cases({
            "3,14": "tre komma en fire", "1,75": "en komma sju fem",
            "3,10": "tre komma en null", "3,05": "tre komma null fem",
            "3,00": "tre komma null null", "−0,75": "minus null komma sju fem",
            "3,14159": "tre komma en fire en fem ni",
            "9,81m/s2": "ni komma åtte en meter per sekund i annen",
            "1,75 min": "ett komma sju fem minutter",
            "3,14–3,75 kg": "tre komma en fire til tre komma sju fem kilo",
            "3,14–3,75": "tre komma en fire til tre komma sju fem",
            "3,14–3,75 %": "tre komma en fire til tre komma sju fem prosent",
            "3,14 %": "tre komma en fire prosent",
            "3,14‰": "tre komma en fire promille",
            "forhold 1,75:3,14": "forhold en komma sju fem til tre komma en fire",
            "CHF 1,20": "en komma to null sveitsiske franc",
            "¥1,25": "en komma to fem yuan",
            "CHF 1,20–1,75": "en komma to null sveitsiske franc til en komma sju fem sveitsiske franc",
        }, decimal_style="digits")

    def test_currency_decimal_policy_and_input_locale(self):
        self.check_cases({
            "CHF 1,20–1,75": "en komma tjue sveitsiske franc til en komma syttifem sveitsiske franc",
            "CNY 1,05": "en komma null fem kinesiske yuan",
            "CHF 1,00": "en sveitsisk franc",
        })
        for style, expected in (("natural", "tjue"), ("digits", "to null")):
            with self.subTest(style=style):
                self.check_cases({"CHF 1.20": "en komma " + expected + " sveitsiske franc"},
                                 currency_locale="en-US", decimal_style=style)
                policy = CurrencyPolicy(decimal_style=style)
                self.assertEqual(policy.amount_words(policy.parse("1,20", "CHF"), "CHF"),
                                 "en komma " + expected + " sveitsiske franc")

    def test_non_decimal_readings_do_not_change(self):
        for style in ("natural", "digits"):
            self.check_cases({
                "EUR 12,50": "tolv euro og femti cent",
                "NOK 1,01": "en krone og ett øre",
                "KWD 1,005": "en kuwaitisk dinar og fem fils",
                "v1.14.75": "versjon en punkt fjorten punkt syttifem",
                "3/4": "tre firedeler", "12:30": "tolv tretti",
            }, decimal_style=style)

    def test_invalid_styles_fail_at_configuration(self):
        for invalid in ("auto", "digit", "", None):
            for factory in (NorwegianNormalizer, CurrencyPolicy):
                with self.subTest(factory=factory, invalid=invalid):
                    with self.assertRaisesRegex(ValueError, "decimal_style"):
                        factory(decimal_style=invalid)

    def test_cli_default_and_technical_json(self):
        for args, expected in (([], "tre komma fjorten"),
                               (["--decimal-style", "natural"], "tre komma fjorten"),
                               (["--decimal-style", "digits"], "tre komma en fire")):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, "-m", "nb_tn", "--strict", "--json",
                                         *args, "3,14"], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["text"], expected)
                self.assertFalse(report["needs_review"])
        invalid = subprocess.run([sys.executable, "-m", "nb_tn", "--decimal-style", "auto", "3,14"],
                                 text=True, capture_output=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(invalid.stdout, "")

    def test_voxcpm_accepts_configured_decimal_style(self):
        class FakeModel:
            def generate(self, **kwargs):
                return kwargs

        for style, expected in (("natural", "tre komma fjorten"), ("digits", "tre komma en fire")):
            audio, report = generate_norwegian(FakeModel(), "3,14",
                                               normalizer=NorwegianNormalizer(decimal_style=style))
            self.assertEqual(report.text, expected)
            self.assertEqual(audio, {"text": expected, "normalize": False})
