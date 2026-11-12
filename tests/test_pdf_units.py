"""Auditable unit inventory from the supplied PDF, plus notation/ambiguity tests."""

from importlib.resources import files
import json
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.units import parse_unit


class PdfUnitTests(unittest.TestCase):
    def check(self, text, expected, language="nb"):
        n = NorwegianNormalizer(language=language)
        r = n.analyze(text)
        self.assertEqual(r.text, expected)
        self.assertFalse(r.issues, r.issues)
        self.assertEqual(n.normalize(expected), expected)
        rebuilt = text
        for change in reversed(r.replacements):
            self.assertEqual(text[change.start:change.end], change.original)
            rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
        self.assertEqual(rebuilt, expected)

    def test_every_inventory_row_in_both_languages(self):
        inventory = json.loads(files("nb_tn").joinpath("pdf_unit_inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(len(inventory["rows"]), 67)
        self.assertEqual({row["table"] for row in inventory["rows"] if "table" in row}, {1, 2, 3, 4, 5, 7, 8, 9})
        self.assertEqual({row["section"] for row in inventory["rows"] if "section" in row}, {"6-7", "6-9", "6-10"})
        for row in inventory["rows"]:
            for language in ("nb", "nn"):
                with self.subTest(quantity=row["quantity"], language=language):
                    self.check("2 " + row["unit"], "to " + row[language], language)

    def test_all_pdf_prefixes_and_special_named_multiples(self):
        prefixes = {
            "Y": "yotta", "Z": "zetta", "E": "exa", "P": "peta", "T": "tera", "G": "giga",
            "M": "mega", "k": "kilo", "h": "hekto", "da": "deka", "d": "desi", "c": "centi",
            "m": "milli", "µ": "mikro", "u": "mikro", "n": "nano", "p": "piko", "f": "femto",
            "a": "atto", "z": "zepto", "y": "yokto",
        }
        for language in ("nb", "nn"):
            for prefix, words in prefixes.items():
                self.check("2 " + prefix + "m", "to " + words + "meter", language)
            for text, expected in {
                "2 ka": "to kiloar", "2 mt": "to millitonn", "2 kbar": "to kilobar",
                "2 L": "to liter", "2 μg": "to mikrogram", "2 keV": "to kiloelektronvolt",
                "1 a": "ett ar" if language == "nb" else "eitt ar",
                "1 nautisk mil": "en nautisk mil" if language == "nb" else "ei nautisk mil",
                "1 karat": "en karat" if language == "nb" else "ein karat",
            }.items():
                self.check(text, expected, language)

    def test_grouped_denominators_and_implicit_products(self):
        for language in ("nb", "nn"):
            second = "annen" if language == "nb" else "andre"
            for text, expected in {
                "2 J/(kg·K)": "to joule per kilo kelvin",
                "2 J / ( kg K )": "to joule per kilo kelvin",
                "2 J/(mol K)": "to joule per mol kelvin",
                "2 Pa s": "to pascal sekund",
                "2 kg m-3": "to kilo per kubikkmeter",
                "2 m-1 kg s-2": "to kilo per meter sekund i " + second,
                "2 m² kg . s⁻³": "to kvadratmeter kilo per sekund i tredje potens",
                "2 m^-2 kg^-1 s4 A2": "to sekund i fjerde potens ampere i " + second + " per kvadratmeter kilo",
                "2 m/(s/kg)": "to meter kilo per sekund",
                "2 (kg m)/(s²)": "to kilo meter per sekund i " + second,
                "2 W/(m²·K)": "to watt per kvadratmeter kelvin",
                "2 kg/(m s²)": "to kilo per meter sekund i " + second,
                "2 m/s kg": "to meter kilo per sekund",  # Left-associative division.
            }.items():
                with self.subTest(text=text, language=language):
                    self.check(text, expected, language)

    def test_other_base_unit_expressions_from_tables_four_and_five(self):
        for language in ("nb", "nn"):
            for unit in (
                "m·m-1", "m2·m-2", "s-1", "m·kg·s-2", "m-1 kg s-2", "m2 kg s-2",
                "m2 kg s-3", "A s", "m2 kg s-3 A-1", "m-2 kg-1 s4 A2",
                "m2 kg s-3 A-2", "m-2 kg-1 s3 A2", "m2 kg s-2 A-1", "kg s-2 A-1",
                "m2 kg s-2 A-2", "cd sr", "m-2 cd sr", "m2 s-2", "s-1 mol",
                "m-1 kg s-1", "m2 kg s-2 K-1", "m2 s-2 K-1", "m kg s-3 A-1",
                "m-3 kg-1 s4 A-2", "m2 kg s-2 K-1 mol-1",
            ):
                with self.subTest(unit=unit, language=language):
                    r = NorwegianNormalizer(language=language).analyze("2 " + unit)
                    self.assertFalse(r.issues, r.issues)
                    self.assertEqual(len(r.replacements), 1)
                    self.assertEqual(r.replacements[0].original, "2 " + unit)
                    self.assertEqual(r.replacements[0].category, "measure")

    def test_angle_chains_cues_and_explicit_unit_aliases(self):
        for language in ("nb", "nn"):
            minute = "bueminutter" if language == "nb" else "bogeminutt"
            second = "buesekunder" if language == "nb" else "bogesekund"
            for text in ("30°15′20″", '30 deg 15\'20"', "30°15'20''"):
                self.check(text, "tretti grader femten " + minute + " tjue " + second, language)
            self.check("vinkelen er 5′", "vinkelen er fem " + minute, language)
            self.check('vinkel: 1"', "vinkel: " + ("ett buesekund" if language == "nb" else "eitt bogesekund"), language)
            self.check("30°20″", "tretti grader tjue " + second, language)
            self.check("5 arcmin", "fem " + minute, language)
            self.check("5 arcsec", "fem " + second, language)
            self.check('Han sa "5".', 'Han sa "fem".', language)

    def test_ambiguous_or_invalid_angles_require_review(self):
        for language in ("nb", "nn"):
            for text in ("5′", "5″", "30°60′20″", "30°15′60″", "30°15,5′20″", "30°15′20", "30°15′ 20", "30°-15′"):
                with self.subTest(text=text, language=language):
                    r = NorwegianNormalizer(language=language).analyze(text)
                    self.assertEqual(r.text, text)
                    self.assertTrue(r.needs_review)

    def test_notation_errors_are_not_partially_normalized(self):
        for language in ("nb", "nn"):
            for text in ("2 J/(kg X)", "2 J/(kg K", "2 J/()", "2 m//s", "2 (m/s)^2",
                         "2 Sr", "2 Kat", "2 mmhg", "2 m^10", "2 m^0"):
                r = NorwegianNormalizer(language=language).analyze(text)
                self.assertEqual(r.text, text, (text, r))
                self.assertTrue(r.needs_review)
        for unit in ("(" * 10 + "m" + ")" * 10, "m " * 65, "m" * 513):
            with self.assertRaises(ValueError):
                parse_unit(unit)
        self.check("2 " + "(" * 8 + "m/s" + ")" * 8, "to meter per sekund")
        for unit in ("(" * 9 + "m/s" + ")" * 9, "m " * 65, "m " * 257):
            original = "2 " + unit.rstrip()
            report = NorwegianNormalizer().analyze(original)
            self.assertEqual(report.text, original)
            self.assertTrue(report.needs_review)

    def test_ordinary_prose_and_sentence_boundaries_are_not_unit_products(self):
        for language in ("nb", "nn"):
            one = "en" if language == "nb" else "ein"
            for text, expected in {
                "5 m kabel": "fem meter kabel", "5 kg. Ho betaler 1 kr.":
                    "fem kilo. Ho betaler " + ("en krone." if language == "nb" else "ei krone."),
                "1 dag": one + " dag", "5 m (en lengde)": "fem meter (en lengde)",
                "5 personer og 3 hus": "fem personer og tre hus",
                "5 kg. S er en bokstav.": "fem kilo. S er en bokstav.",
            }.items():
                self.check(text, expected, language)

    def test_full_sentence_examples_are_exact(self):
        for language, original, expected in (
            ("nb", "Den 8. mai 2026 målte vi 9,81 m/s² og 2 A², og kontrollen kostet kr 150,50 etter § 2-1.",
             "Den åttende mai to tusen og tjueseks målte vi ni komma åttien meter per sekund i annen og to ampere i annen, og kontrollen kostet hundre og femti kroner og femti øre etter paragraf to en."),
            ("nn", "Den 8. mai 2026 målte vi 9,81 m/s² og 2 A², og kontrollen kosta kr 150,50 etter § 2-1.",
             "Den åttande mai to tusen og tjueseks målte vi ni komma åttiein meter per sekund i andre og to ampere i andre, og kontrollen kosta hundre og femti kroner og femti øre etter paragraf to ein."),
            ("nb", "Etter § 4 (2) viste målingen 9,81 m/s² og 3,14 V² den 9. juni 2026, og gebyret var EUR 12,50.",
             "Etter paragraf fire andre ledd viste målingen ni komma åttien meter per sekund i annen og tre komma fjorten volt i annen den niende juni to tusen og tjueseks, og gebyret var tolv euro og femti cent."),
            ("nn", "Etter § 4 (2) viste målinga 9,81 m/s² og 3,14 V² den 9. juni 2026, og gebyret var EUR 12,50.",
             "Etter paragraf fire andre ledd viste målinga ni komma åttiein meter per sekund i andre og tre komma fjorten volt i andre den niande juni to tusen og tjueseks, og gebyret var tolv euro og femti cent."),
        ):
            self.check(original, expected, language)
