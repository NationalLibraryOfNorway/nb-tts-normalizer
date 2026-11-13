"""Hand-authored scientific readings and conservative ambiguity fixtures."""

import unittest

from nb_tn import NorwegianNormalizer


class ScientificTests(unittest.TestCase):
    def check(self, source, expected, language="nb", **options):
        n = NorwegianNormalizer(language=language, **options)
        result = n.analyze(source)
        self.assertEqual(result.text, expected)
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(n.normalize(expected), expected)
        rebuilt = source
        for change in reversed(result.replacements):
            self.assertEqual(source[change.start:change.end], change.original)
            rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
        self.assertEqual(rebuilt, expected)

    def test_equivalent_notations_and_languages(self):
        for language, one, times, raised in (("nb", "en", "ganger", "opphøyd"),
                                             ("nn", "ein", "gonger", "opphøgd")):
            for source in ("1,2 × 10⁻³", "1.2e-3", "1,2E−3", "1,2·10^-3",
                           "1,2 ⋅ 10 ^ −3", "1,2*10⁻³", "1,2\u00a0×\u202f10⁻³"):
                with self.subTest(language=language, source=source):
                    self.check(source, f"{one} komma to {times} ti {raised} i minus tre", language)

    def test_signs_zero_and_noncanonical_coefficients(self):
        for source, expected in {
            "-0,2 × 10^3": "minus null komma to ganger ti opphøyd i tre",
            "+1.2e+3": "pluss en komma to ganger ti opphøyd i pluss tre",
            "12,0 × 10^0": "tolv komma null ganger ti opphøyd i null",
            "0e+3": "null ganger ti opphøyd i pluss tre",
            "10⁻³": "ti opphøyd i minus tre", "10^0": "ti opphøyd i null",
            "10⁺²¹": "ti opphøyd i pluss tjueen",
            "2E-999": "to ganger ti opphøyd i minus ni hundre og nittini",
        }.items():
            self.check(source, expected)
        self.check("10^21", "ti opphøgd i tjueein", "nn")

    def test_decimal_options_preserve_trailing_zeros(self):
        for language, one, times, raised in (("nb", "en", "ganger", "opphøyd"),
                                             ("nn", "ein", "gonger", "opphøgd")):
            for style, fractional in (("natural", "tjuefem"), ("digits", f"to fem")):
                self.check("1.25e-3", f"{one} komma {fractional} {times} ti {raised} i minus tre",
                           language, decimal_style=style)
            for mantissa, spoken in (("1.05", "null fem"), ("1.00", "null null"),
                                     ("1.200", "to null null")):
                self.check(mantissa + "e-3", f"{one} komma {spoken} {times} ti {raised} i minus tre", language)

    def test_full_sentences_units_and_offsets(self):
        self.check("Den 8. mai 2026 målte vi 1,2 × 10⁻³ m/s² etter § 2-1; prisen var kr 150,50.",
                   "Den åttende mai to tusen og tjueseks målte vi en komma to ganger ti opphøyd i minus tre meter per sekund i annen etter paragraf to en; prisen var hundre og femti kroner og femti øre.")
        self.check("Den 8. mai 2026 målte vi 1.2e-3 m/s² etter § 2-1; prisen var kr 150,50.",
                   "Den åttande mai to tusen og tjueseks målte vi ein komma to gonger ti opphøgd i minus tre meter per sekund i andre etter paragraf to ein; prisen var hundre og femti kroner og femti øre.", "nn")
        self.check("Verdien er 1.2e-3.", "Verdien er en komma to ganger ti opphøyd i minus tre.")
        self.check("1.2e-3 J/(kg K)", "en komma to ganger ti opphøyd i minus tre joule per kilo kelvin")
        self.check("1.2e-3 og 2 m", "en komma to ganger ti opphøyd i minus tre og to meter")
        self.check("1e-3 s", "en ganger ti opphøyd i minus tre sekunder")
        self.check("10e-1 s", "ti ganger ti opphøyd i minus en sekund")
        self.check("1e-3 s", "ein gonger ti opphøgd i minus tre sekund", "nn")

    def test_ambiguous_and_malformed_are_preserved(self):
        cases = ("1E3", "1e3", "1.234 × 10^3", "1,234.5e-3", "1,2 x 10^-3",
                 "1,2 × 10-3", "1 e -3", "1.2e", "1e-", "1.2e-3.5",
                 "10^n", "10^", "10^(-3)", "10^{-3}", "1,2 × 10⁻³⁺²",
                 "-10⁻³", "01.2e-3", "1.2e-03", "1.2e-1000",
                 "1234567890123456789e+3", "1.2e-3kg", "1.2e-3_abc",
                 "1e-3–2e-3", "1e-3-2e-3", "1e-3–2", "2–1e-3",
                 "1.2e-3 m//s", "1.2e-3 m^", "EUR 1.2e-3", "1.2e-3 EUR",
                 "1.2e-3 %", "1 234e-3", "1 234,5 × 10^3")
        for language in ("nb", "nn"):
            for source in cases:
                with self.subTest(language=language, source=source):
                    result = NorwegianNormalizer(language=language).analyze(source)
                    self.assertEqual(result.text, source)
                    self.assertTrue(result.needs_review)
                    for issue in result.issues:
                        self.assertEqual(source[issue.start:issue.end], issue.original)

    def test_existing_domains_do_not_collide(self):
        for source, expected in {
            "10-15 km": "ti til femten kilometer", "2 eV": "to elektronvolt",
            "1 euro og 2 euros": "en euro og to euro",
            "v1.2.3": "versjon en punkt to punkt tre",
            "3,14": "tre komma fjorten",
        }.items():
            self.check(source, expected)
