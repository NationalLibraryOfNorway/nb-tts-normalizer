"""English aliases are opt-in; ambiguous Norwegian t is not guessed."""

from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.units import parse_unit


class TimeAliasPolicyTests(unittest.TestCase):
    def test_aliases_default_to_review_across_quantity_paths(self):
        for language in ("nb", "nn"):
            for scientific_units in (False, True):
                n = NorwegianNormalizer(language=language, scientific_units=scientific_units)
                for alias in ("mins", "hr", "hrs", "sec", "secs"):
                    for source in (f"2 {alias}", f"2{alias}", f"−1,25 {alias}",
                                   f"1/2 {alias}", f"2–3 {alias}", f"1.2e-3 {alias}",
                                   f"2 m/{alias}", f"2 {alias}²", f"2 J/({alias} K)"):
                        with self.subTest(language=language, source=source, scientific=scientific_units):
                            r = n.analyze(source)
                            self.assertEqual(r.text, source)
                            self.assertTrue(r.needs_review)
                            self.assertEqual(len(r.issues), 1)
                            self.assertIn("english_unit_aliases", r.issues[0].reason)
                            self.assertEqual(source[r.issues[0].start:r.issues[0].end], r.issues[0].original)

    def test_opt_in_language_forms_and_normal_forms(self):
        for language, one, neuter, minutes, hours, seconds in (
            ("nb", "en", "ett", "minutter", "timer", "sekunder"),
            ("nn", "ein", "eitt", "minutt", "timar", "sekund"),
        ):
            for enabled in (False, True):
                n = NorwegianNormalizer(language=language, english_unit_aliases=enabled)
                for source, expected in {
                    "2 min": f"to {minutes}", "2 h": f"to {hours}",
                    "2 s": f"to {seconds}", "2 sek": f"to {seconds}",
                    "1 h": f"{one} time", "1 min": f"{neuter} minutt",
                    "2 tonn": "to tonn", "2 km/t": "to kilometer i timen",
                    "2 km/h": "to kilometer i timen", "2 mt": "to millitonn",
                    "2 T": "to tesla", "mins hrs secs": "mins hrs secs",
                    "f.eks kaffi": "for eksempel kaffi",
                }.items():
                    r = n.analyze(source)
                    self.assertEqual(r.text, expected)
                    self.assertFalse(r.issues, r.issues)
                if enabled:
                    for source, expected in {
                        "2 mins": f"to {minutes}", "2 hrs": f"to {hours}",
                        "1 hr": f"{one} time", "1 sec": f"{neuter} sekund",
                        "2 secs": f"to {seconds}", "2 m/sec": "to meter per sekund",
                    }.items():
                        r = n.analyze(source)
                        self.assertEqual(r.text, expected)
                        self.assertFalse(r.issues, r.issues)

    def test_ambiguous_t_is_preserved_in_every_mode(self):
        cases = ("2 t", "2t", "−1,25 t", "1/2 t", "2–3 t", "1.2e-3 t",
                 "2 t/h", "2 t/min", "2 t²", "2 m/t", "2 kg t", "2 J/(t K)")
        for language in ("nb", "nn"):
            for scientific in (False, True):
                for english in (False, True):
                    n = NorwegianNormalizer(language=language, scientific_units=scientific,
                                            english_unit_aliases=english)
                    for source in cases:
                        with self.subTest(source=source, language=language, scientific=scientific, english=english):
                            r = n.analyze(source)
                            self.assertEqual(r.text, source)
                            self.assertEqual(len(r.issues), 1)
                            self.assertIn("ambiguous t", r.issues[0].reason)

    def test_low_level_alias_policy_validation_and_isolation(self):
        with self.assertRaisesRegex(ValueError, "english_unit_aliases"):
            parse_unit("hrs")
        self.assertEqual(parse_unit("hrs", english_unit_aliases=True).plural, "timer")
        for invalid in ("true", 1, None):
            with self.assertRaises(ValueError):
                NorwegianNormalizer(english_unit_aliases=invalid)
        default = NorwegianNormalizer()
        enabled = NorwegianNormalizer(english_unit_aliases=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(n.analyze, "2 hrs") for n in (default, enabled) * 5]
            for i, job in enumerate(jobs):
                r = job.result()
                self.assertEqual(r.text, "to timer" if i % 2 else "2 hrs")
                self.assertEqual(r.needs_review, not bool(i % 2))

    def test_cli_opt_in_and_strict_review(self):
        for args, source, code, output in (
            ([], "2 hrs", 2, ""),
            (["--english-unit-aliases"], "2 hrs", 0, "to timer"),
            (["--language", "nn", "--english-unit-aliases"], "2 hrs", 0, "to timar"),
            (["--english-unit-aliases", "--no-english-unit-aliases"], "2 hrs", 2, ""),
            (["--english-unit-aliases", "--no-scientific-units"], "2 t", 2, ""),
        ):
            p = subprocess.run([sys.executable, "-m", "nb_tn", "--strict", *args, source],
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, code, p.stderr)
            self.assertEqual(p.stdout.strip(), output)
