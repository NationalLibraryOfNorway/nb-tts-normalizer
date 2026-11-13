"""Temperature readings and case-sensitive C/F/K disambiguation."""

import unittest

from nb_tn import NorwegianNormalizer


class TemperatureTests(unittest.TestCase):
    def check(self, source, expected, language, **options):
        normalizer = NorwegianNormalizer(language=language, **options)
        result = normalizer.analyze(source)
        self.assertEqual(result.text, expected)
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(normalizer.normalize(expected), expected)
        rebuilt = source
        for change in reversed(result.replacements):
            self.assertEqual(source[change.start:change.end], change.original)
            rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
        self.assertEqual(rebuilt, expected)

    def test_values_signs_and_singular_plural(self):
        for language, one in (("nb", "en"), ("nn", "ein")):
            for source, expected in {
                "20 °C": "tjue grader celsius",
                "68 °F": "sekstiåtte grader fahrenheit",
                "20 K": "tjue kelvin",
                "1 °C": f"{one} grad celsius",
                "1 °F": f"{one} grad fahrenheit",
                "1 K": f"{one} kelvin",
                "0 °C": "null grader celsius",
                "0 °F": "null grader fahrenheit",
                "0 K": "null kelvin",
                "−5 °C": "minus fem grader celsius",
                "-5 °F": "minus fem grader fahrenheit",
                "−1 °C": f"minus {one} grad celsius",
                "-1 °F": f"minus {one} grad fahrenheit",
                "−1 K": f"minus {one} kelvin",
                "20°C": "tjue grader celsius",
                "68°F": "sekstiåtte grader fahrenheit",
                "20K": "tjue kelvin",
            }.items():
                with self.subTest(language=language, source=source):
                    self.check(source, expected, language)

    def test_decimals_and_digit_option(self):
        for language, one, twenty_one in (("nb", "en", "tjueen"), ("nn", "ein", "tjueein")):
            for source, expected in {
                "273,15 K": "to hundre og syttitre komma femten kelvin",
                "−0,25 °C": "minus null komma tjuefem grader celsius",
                "-0,25 °F": "minus null komma tjuefem grader fahrenheit",
                "1,21 °F": f"{one} komma {twenty_one} grader fahrenheit",
                "1,00 °C": f"{one} komma null null grader celsius",
                "1,00 K": f"{one} komma null null kelvin",
            }.items():
                with self.subTest(language=language, source=source):
                    self.check(source, expected, language)
            for symbol, words in (("°C", "grader celsius"), ("°F", "grader fahrenheit"), ("K", "kelvin")):
                self.check(f"−1,25 {symbol}", f"minus {one} komma to fem {words}", language,
                           decimal_style="digits")

    def test_c_f_k_and_degree_ambiguity(self):
        for language in ("nb", "nn"):
            for source, expected in {
                "20 C": "tjue coulomb", "20 F": "tjue farad", "20 K": "tjue kelvin",
                "−5 C": "minus fem coulomb", "1,25 F": "en komma tjuefem farad" if language == "nb" else "ein komma tjuefem farad",
                "20°": "tjue grader", "−5°": "minus fem grader",
                "20,25°": "tjue komma tjuefem grader",
                "Temperaturen er 20 C.": "Temperaturen er tjue coulomb.",
                "C F K": "C F K", "Vi møtte C. Dahl, F. Olsen og K. Hansen.": "Vi møtte C. Dahl, F. Olsen og K. Hansen.",
            }.items():
                with self.subTest(language=language, source=source):
                    self.check(source, expected, language)
            for source in ("°C", "°F", "20 °K", "2 C. Dahl", "2 F. Olsen", "2 K. Hansen"):
                result = NorwegianNormalizer(language=language).analyze(source)
                self.assertEqual(result.text, source)
                self.assertTrue(result.needs_review)

    def test_scientific_temperature_and_sentences(self):
        for language, one, times, raised in (("nb", "en", "ganger", "opphøyd"), ("nn", "ein", "gonger", "opphøgd")):
            self.check("1.2e-3 K", f"{one} komma to {times} ti {raised} i minus tre kelvin", language)
            self.check("1,2 × 10⁻³ °C", f"{one} komma to {times} ti {raised} i minus tre grader celsius", language)
            self.check("Ute er det −5 °C, inne 20,25 °C, og sensoren viser 273,15 K.",
                       "Ute er det minus fem grader celsius, inne tjue komma tjuefem grader celsius, og sensoren viser to hundre og syttitre komma femten kelvin.", language)
