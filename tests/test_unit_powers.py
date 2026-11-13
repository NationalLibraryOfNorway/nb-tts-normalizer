"""Physical power readings: government draft table 3 + explicit language policy."""

import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.units import parse_unit


class UnitPowerTests(unittest.TestCase):
    def check_reading(self, text, expected, language="nb", **options):
        normalizer = NorwegianNormalizer(language=language, **options)
        report = normalizer.analyze(text)
        self.assertEqual(report.text, expected)
        self.assertFalse(report.issues, report.issues)
        self.assertEqual(normalizer.normalize(expected), expected)
        rebuilt = text
        for change in reversed(report.replacements):
            self.assertEqual(text[change.start:change.end], change.original)
            rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
        self.assertEqual(rebuilt, expected)

    def test_acceleration_notations_and_both_languages(self):
        for language, power, decimal in (("nb", "annen", "åttien"), ("nn", "andre", "åttiein")):
            for symbol in ("m/s²", "m/s2", "m/s^2", "m·s⁻²", "m*s^-2", "m/s^+2"):
                with self.subTest(language=language, symbol=symbol):
                    self.check_reading("9,81 " + symbol,
                                       "ni komma " + decimal + " meter per sekund i " + power,
                                       language=language)
            self.check_reading("9,81m/s2", "ni komma åtte " + ("en" if language == "nb" else "ein")
                               + " meter per sekund i " + power, language=language, decimal_style="digits")

    def test_other_squared_units_and_prefixes(self):
        for language, power, one in (("nb", "annen", "en"), ("nn", "andre", "ein")):
            for symbol, name in (("s²", "sekund"), ("ms2", "millisekund"), ("A^2", "ampere"),
                                 ("K²", "kelvin"), ("Pa²", "pascal"), ("V²", "volt"), ("g²", "gram")):
                with self.subTest(language=language, symbol=symbol):
                    self.check_reading("2 " + symbol, "to " + name + " i " + power, language=language)
            self.check_reading("1,21–2,21 m/s²", one + " komma tjue" + one
                               + " til to komma tjue" + one + " meter per sekund i " + power,
                               language=language)
            self.assertEqual(parse_unit("s⁻²", language=language).singular, "per sekund i " + power)

    def test_geometric_names_and_other_powers_are_preserved(self):
        for language in ("nb", "nn"):
            for symbol in ("m²", "m2", "m^2"):
                self.check_reading("2 " + symbol, "to kvadratmeter", language=language)
            for symbol in ("m³", "m3", "m^3"):
                self.check_reading("2 " + symbol, "to kubikkmeter", language=language)
            for text, expected in {
                "2 cm²": "to kvadratcentimeter", "2 cm³": "to kubikkcentimeter",
                "2 kg/m³": "to kilo per kubikkmeter", "2 m²/s": "to kvadratmeter per sekund",
                "2 m^4": "to meter i fjerde potens", "2 s^3": "to sekund i tredje potens",
                "2 s⁻¹": "to per sekund", "2 S": "to siemens", "2 sr": "to steradian" + ("er" if language == "nb" else "ar"),
            }.items():
                with self.subTest(language=language, text=text):
                    self.check_reading(text, expected, language=language)
            # Unit wording must not globally replace the ordinary ordinal 2.
            self.check_reading("2. mai 2026", "andre mai tjue tjueseks", language=language)

    def test_full_sentences_and_unchanged_written_readings(self):
        for language, input_text, expected in (
            ("nb", "Den 8. mai 2026 var akselerasjonen 9,81 m/s², jf. § 2-1.",
             "Den åttende mai tjue tjueseks var akselerasjonen ni komma åttien meter per sekund i annen, jamfør paragraf to en."),
            ("nn", "Den 8. mai 2026 var akselerasjonen 9,81 m/s², jf. § 2-1.",
             "Den åttande mai tjue tjueseks var akselerasjonen ni komma åttiein meter per sekund i andre, jamfør paragraf to ein."),
        ):
            self.check_reading(input_text, expected, language=language)
        for phrase in ("sekund i annen", "sekund i andre", "sekund i kvadrat"):
            for language in ("nb", "nn"):
                self.check_reading(phrase, phrase, language=language)

    def test_rejected_units_still_keep_original_spans(self):
        for language in ("nb", "nn"):
            for text in ("2 s^0", "2 s^10", "2 m//s²", "2 W/(m²·XYZ)", "2 s^", "2 mhz"):
                report = NorwegianNormalizer(language=language).analyze(text)
                self.assertEqual(report.text, text)
                self.assertTrue(report.needs_review)
