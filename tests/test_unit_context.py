"""Bare symbols and personal initials must never acquire physical unit names."""

import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.units import BASE_UNITS


class UnitContextTests(unittest.TestCase):
    def test_bare_single_letters_are_not_units(self):
        for language in ("nb", "nn"):
            normalizer = NorwegianNormalizer(language=language)
            for symbol in BASE_UNITS:
                if len(symbol) != 1:
                    continue
                for source in (symbol, f"Symbolet {symbol} står her.",
                               f"Vi møtte {symbol}. Hansen."):
                    with self.subTest(language=language, source=source):
                        result = normalizer.analyze(source)
                        self.assertEqual(result.text, source)
                        self.assertFalse(result.replacements)

    def test_initials_at_start_may_be_letters_but_never_units(self):
        for language in ("nb", "nn"):
            for source in ("N. Hansen møtte C. Dahl og J. Olsen.", "J. Olsen", "N. C. J. Olsen"):
                result = NorwegianNormalizer(language=language).analyze(source)
                # Existing letter-list/initial reading may spell a letter aloud.
                self.assertFalse(any(r.category in ("measure", "scientific") for r in result.replacements))
                self.assertFalse(any(word in result.text for word in ("newton", "coulomb", "joule")))

    def test_numeric_context_and_name_ambiguity(self):
        for language in ("nb", "nn"):
            normalizer = NorwegianNormalizer(language=language)
            self.assertEqual(normalizer.normalize("2 N, 3 C og 4 J."),
                             "to newton, tre coulomb og fire joule.")
            for source in ("2 N. Hansen", "3 C. Dahl", "4 J. Olsen", "1.2e-3 N. Hansen"):
                result = normalizer.analyze(source)
                self.assertEqual(result.text, source)
                self.assertTrue(result.needs_review)
            result = normalizer.analyze("1.2e-3 N")
            self.assertTrue(result.text.endswith(" newton"))
            self.assertFalse(result.issues)
