"""Exact full-sentence examples: language, policy switches and review spans."""

import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.numbers import year


class FullSentencePolicyTests(unittest.TestCase):
    def check(self, source, expected, *, flagged=(), **options):
        n = NorwegianNormalizer(**options)
        r = n.analyze(source)
        self.assertEqual(r.text, expected)
        self.assertEqual(tuple(i.original for i in r.issues), flagged)
        self.assertEqual(r.needs_review, bool(flagged))
        rebuilt = source
        for change in reversed(r.replacements):
            self.assertEqual(source[change.start:change.end], change.original)
            rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
        self.assertEqual(rebuilt, expected)
        for issue in r.issues:
            self.assertEqual(source[issue.start:issue.end], issue.original)
        self.assertEqual(n.normalize(expected), expected)

    def test_mixed_scientific_sentences_both_modes(self):
        cases = (
            ("nb", "Den 8. mai 2026 målte vi 1,2 × 10⁻³ A, 230 V og 60 W ved −5 °C; kontrollen kostet $20 og ¥1,25 etter § 2-1.",
             "Den åttende mai tjue tjueseks målte vi en komma to ganger ti opphøyd i minus tre ampere, to hundre og tretti volt og seksti watt ved minus fem grader celsius; kontrollen kostet tjue dollar og en komma tjuefem yuan etter paragraf to en.",
             "Den åttende mai tjue tjueseks målte vi en komma to ganger ti opphøyd i minus tre a, to hundre og tretti ve og seksti dobbeltve ved minus fem grader celsius; kontrollen kostet tjue dollar og en komma tjuefem yuan etter paragraf to en."),
            ("nn", "Den 8. mai 2026 målte vi 1,2 × 10⁻³ A, 230 V og 60 W ved −5 °C; kontrollen kosta $20 og ¥1,25 etter § 2-1.",
             "Den åttande mai tjue tjueseks målte vi ein komma to gonger ti opphøgd i minus tre ampere, to hundre og tretti volt og seksti watt ved minus fem grader celsius; kontrollen kosta tjue dollar og ein komma tjuefem yuan etter paragraf to ein.",
             "Den åttande mai tjue tjueseks målte vi ein komma to gonger ti opphøgd i minus tre a, to hundre og tretti ve og seksti dobbeltve ved minus fem grader celsius; kontrollen kosta tjue dollar og ein komma tjuefem yuan etter paragraf to ein."),
        )
        for language, source, enabled, disabled in cases:
            self.check(source, enabled, language=language)
            self.check(source, enabled, language=language, scientific_units=True)
            self.check(source, disabled, language=language, scientific_units=False)

    def test_everyday_units_and_standard_time_forms(self):
        for language, seconds, hours, minutes in (("nb", "sekunder", "timer", "minutter"),
                                                 ("nn", "sekund", "timar", "minutt")):
            for scientific in (True, False):
                self.check("I året 2005 målte vi 2 m, 3 kg og 5 mg i løpet av 10 s og 2 h.",
                           f"I året to tusen og fem målte vi to meter, tre kilo og fem milligram i løpet av ti {seconds} og to {hours}.",
                           language=language, scientific_units=scientific)
                self.check("Turen tok 2 h, og pausen varte 5 min og 30 sek.",
                           f"Turen tok to {hours}, og pausen varte fem {minutes} og tretti {seconds}.",
                           language=language, scientific_units=scientific)

    def test_review_sentences_and_explicit_alias_opt_in(self):
        for language, cost, hours, minutes, seconds in (("nb", "kostet", "timer", "minutter", "sekunder"),
                                                       ("nn", "kosta", "timar", "minutt", "sekund")):
            for scientific in (True, False):
                options = dict(language=language, scientific_units=scientific)
                self.check(f"Turen tok 2 t og {cost} $20.", f"Turen tok 2 t og {cost} tjue dollar.",
                           flagged=("2 t",), **options)
                self.check(f"Turen tok 2 hrs og {cost} ¥20.", f"Turen tok 2 hrs og {cost} tjue yuan.",
                           flagged=("2 hrs",), **options)
                self.check("Pausen varte 5 mins og 30 secs.", "Pausen varte 5 mins og 30 secs.",
                           flagged=("5 mins", "30 secs"), **options)
                self.check(f"Turen tok 2 hrs og {cost} ¥20.", f"Turen tok to {hours} og {cost} tjue yuan.",
                           english_unit_aliases=True, **options)
                self.check("Pausen varte 5 mins og 30 secs.", f"Pausen varte fem {minutes} og tretti {seconds}.",
                           english_unit_aliases=True, **options)

    def test_year_cutoff_all_2000s_and_date_paths(self):
        for language in ("nb", "nn"):
            expected = ("to tusen", "to tusen og en" if language == "nb" else "to tusen og ein",
                        "to tusen og to", "to tusen og tre", "to tusen og fire", "to tusen og fem",
                        "to tusen og seks", "to tusen og sju", "to tusen og åtte", "to tusen og ni")
            for value, words in enumerate(expected, 2000):
                self.assertEqual(year(value, language=language), words)
                self.check(f"Vi kom i året {value}.", f"Vi kom i året {words}.", language=language)
                self.check(f"01.05.{value}", "første mai " + words, language=language)
            for value, words in ((1999, "nitten nittini"), (2010, "tjue ti"), (2016, "tjue seksten"), (2026, "tjue tjueseks")):
                self.assertEqual(year(value, language=language), words)
            for source in ("1.5.09", "2009-05-01", "dato 20090501"):
                self.assertIn("to tusen og ni", NorwegianNormalizer(language=language).normalize(source))
            self.check("1.5.09–1.5.10", "første mai to tusen og ni til første mai tjue ti", language=language)
            self.check("1.5.10", "første mai to tusen og ti", language=language, year_style="traditional")
            self.check("2010 m", "to tusen og ti meter", language=language)
