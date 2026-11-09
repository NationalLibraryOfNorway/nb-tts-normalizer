import json
import subprocess
import sys
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.numbers import cardinal
from nb_tn.voxcpm import generate_norwegian


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.normalizer = NorwegianNormalizer()

    def test_supported_readings(self):
        cases = {
            "Det koster kr 150,-.": "Det koster hundre og femti kroner.",
            "150 kr": "hundre og femti kroner",
            "NOK 1,01": "en krone og ett øre",
            "-5 kr": "minus fem kroner",
            "1 000 000 kr": "en million kroner",
            "1.000 kr": "ett tusen kroner",
            "123.456,78 kr": "hundre og tjuetre tusen fire hundre og femtiseks kroner og syttiåtte øre",
            "5 kr 50 øre": "fem kroner og femti øre",
            "-5 kr 50 øre": "minus fem kroner og femti øre",
            "Det er 50 %.": "Det er femti prosent.",
            "0,5 ‰": "null komma fem promille",
            "10–15 %": "ti til femten prosent",
            "10–15 kr": "ti til femten kroner",
            "kr 10–15": "ti til femten kroner",
            "3,14": "tre komma en fire",
            "-0,05": "minus null komma null fem",
            "10 000": "ti tusen",
            "1. mai": "første mai",
            "31. desember 1998": "trettiførste desember nitten nittiåtte",
            "01.05.2026": "første mai to tusen og tjueseks",
            "2026-05-01": "første mai to tusen og tjueseks",
            "29. februar": "tjueniende februar",
            "året 1905": "året nitten null fem",
            "år 1998": "år nitten nittiåtte",
            "Kl. 17:03.": "klokka sytten null tre.",
            "klokken 09.05": "klokka ni null fem",
            "kl. 12": "klokka tolv",
            "12:30": "tolv tretti",
            "00:00": "null",
            "10–15 km": "ti til femten kilometer",
            "10-15 km": "ti til femten kilometer",
            "10–15": "ti til femten",
            "10 m² og 2 m³": "ti kvadratmeter og to kubikkmeter",
            "5km": "fem kilometer",
            "1 min og 2 min": "ett minutt og to minutter",
            "-2 °C": "minus to grader celsius",
            "1 stk. og 2 stk.": "ett stykk og to stykker.",
            "2 stk. Det er alt.": "to stykker. Det er alt.",
            "jf. § 2, §§ 3–5.": "jamfør paragraf to, paragrafene tre til fem.",
            "1. plass og 2. ledd": "første plass og andre ledd",
            "f.eks. NAV, NRK og USA": "for eksempel nav, enn err kå og u ess a",
            "Hei! 150? Ja; 3,14.": "Hei! hundre og femti? Ja; tre komma en fire.",
            "«osv.»": "«og så videre.»",
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                result = self.normalizer.analyze(original)
                self.assertEqual(result.text, expected)
                self.assertFalse(result.issues, result.issues)

    def test_unresolved_forms_are_preserved(self):
        for original in ("-5",):  # A signed cardinal is supported, including its sign.
            self.assertEqual(self.normalizer.normalize(original), "minus fem")
        cases = (
            "1000000", "0012", "12345678", "2026-02-30", "31. februar",
            "3.14", "25:99",
            "AB123", "A4", "postnr. 0123",
            "https://example.org/2026-05-01", "test123@example.no",
            "5 EUR", "$5", "±5",
            "kr 1,234", "1000000000000 kr",
            "12:30:45", "2026-01-01T12:30:00Z", "1 000.000", "5 kr 50",
        )
        for original in cases:
            with self.subTest(original=original):
                result = self.normalizer.analyze(original)
                self.assertEqual(result.text, original)
                self.assertTrue(result.needs_review)

    def test_repeated_unicode_spans_round_trip(self):
        original = "Åse: 50 %, 50 % — 1. mai."
        result = self.normalizer.analyze(original)
        rebuilt = original
        last_end = 0
        for replacement in result.replacements:
            self.assertGreaterEqual(replacement.start, last_end)
            self.assertEqual(original[replacement.start:replacement.end], replacement.original)
            last_end = replacement.end
        for replacement in reversed(result.replacements):
            rebuilt = rebuilt[:replacement.start] + replacement.spoken + rebuilt[replacement.end:]
        self.assertEqual(rebuilt, result.text)
        self.assertEqual(self.normalizer.normalize(result.text), result.text)

    def test_plain_text_and_sentence_punctuation(self):
        for text in ("Hei, Åse! Hvordan går det?", "Første linje.\nAndre linje!", "", "  Hei.  "):
            self.assertEqual(self.normalizer.normalize(text), text)

    def test_custom_acronyms_are_exact_case(self):
        normalizer = NorwegianNormalizer(acronyms={"API": "a pe i"})
        self.assertEqual(normalizer.normalize("API og api og NAV"), "a pe i og api og NAV")

    def test_cardinal_bounds(self):
        self.assertEqual(cardinal(0), "null")
        self.assertEqual(cardinal(21), "tjueen")
        self.assertEqual(cardinal(1001), "ett tusen og en")
        self.assertEqual(cardinal(10**9), "en milliard")
        with self.assertRaises(ValueError):
            cardinal(10**12)


class AdapterTests(unittest.TestCase):
    class FakeModel:
        def __init__(self):
            self.calls = []

        def generate(self, **kwargs):
            self.calls.append(kwargs)
            return "audio"

    def test_normalizes_before_model_and_disables_bundled_frontend(self):
        model = self.FakeModel()
        audio, report = generate_norwegian(model, "50 %", seed=7, prompt_text="Hei.")
        self.assertEqual(audio, "audio")
        self.assertEqual(report.text, "femti prosent")
        self.assertEqual(model.calls, [{"text": "femti prosent", "normalize": False,
                                        "seed": 7, "prompt_text": "Hei."}])

    def test_review_blocks_generation_unless_explicitly_disabled(self):
        model = self.FakeModel()
        with self.assertRaises(ValueError):
            generate_norwegian(model, "AB123")
        self.assertEqual(model.calls, [])
        _, report = generate_norwegian(model, "AB123", strict=False)
        self.assertTrue(report.needs_review)
        self.assertEqual(model.calls[0]["text"], "AB123")

    def test_cannot_enable_english_normalization(self):
        with self.assertRaises(TypeError):
            generate_norwegian(self.FakeModel(), "Hei", normalize=True)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args, text=None):
        return subprocess.run([sys.executable, "-m", "nb_tn", *args], input=text,
                              text=True, capture_output=True)

    def test_json_report_and_stdin(self):
        completed = self.run_cli("--json", text="Åse: 50 %")
        self.assertEqual(completed.returncode, 0)
        report = json.loads(completed.stdout)
        self.assertEqual(report["text"], "Åse: femti prosent")
        self.assertFalse(report["needs_review"])
        self.assertEqual(report["replacements"][0]["start"], 5)

    def test_strict_prevents_plain_text_output(self):
        completed = self.run_cli("--strict", "1000000")
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("1000000", completed.stderr)

    def test_strict_json_remains_available_for_review(self):
        completed = self.run_cli("--strict", "--json", "1000000")
        self.assertEqual(completed.returncode, 2)
        self.assertTrue(json.loads(completed.stdout)["needs_review"])


if __name__ == "__main__":
    unittest.main()
