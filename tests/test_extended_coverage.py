import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.readings import DASH_CHARS


class ExtendedCoverageTests(unittest.TestCase):
    def setUp(self):
        self.normalizer = NorwegianNormalizer()

    def check_cases(self, cases):
        for original, expected in cases.items():
            with self.subTest(original=original):
                report = self.normalizer.analyze(original)
                self.assertEqual(report.text, expected)
                self.assertFalse(report.issues, report.issues)
                # The source spans remain a faithful audit trail after tolerant parsing.
                rebuilt = original
                for change in reversed(report.replacements):
                    self.assertEqual(original[change.start:change.end], change.original)
                    rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
                self.assertEqual(rebuilt, expected)
                self.assertEqual(self.normalizer.normalize(expected), expected)

    def test_tolerant_dates(self):
        self.check_cases({
            "01.05": "første mai",
            "1 . 5 . 2026": "første mai tjue tjueseks",
            "1..5..2026": "første mai tjue tjueseks",
            "1/5/2026": "første mai tjue tjueseks",
            "1-5-2026": "første mai tjue tjueseks",
            "2026/5/1": "første mai tjue tjueseks",
            "2026 - 5 - 1": "første mai tjue tjueseks",
            "1.5.26": "første mai tjue tjueseks",
            "1.5.98": "første mai nitten nittiåtte",
            "1mai2026": "første mai tjue tjueseks",
            "1 mai": "første mai",
            "1.mai.2026": "første mai tjue tjueseks",
            "1. sept. 2026": "første september tjue tjueseks",
            "Dato 1/5": "Dato første mai",
            "dato 20260501": "dato første mai tjue tjueseks",
            "dato 01052026": "dato første mai tjue tjueseks",
            "1.–3. mai": "første til tredje mai",
            "1-3 mai 2026": "første til tredje mai tjue tjueseks",
            "Fra 1.–3. mai er det stengt.": "Fra første til tredje mai er det stengt.",
            "01.05.2026–03.05.2026": "første mai tjue tjueseks til tredje mai tjue tjueseks",
            "1.-3.5.2026": "første til tredje mai tjue tjueseks",
            "1.5.-3.5.2026": "første mai til tredje mai tjue tjueseks",
            "1. mai-3. mai 2026": "første mai til tredje mai tjue tjueseks",
        })

    def test_two_digit_years_are_deterministic_and_configurable(self):
        self.assertEqual(self.normalizer.normalize("1.5.49"), "første mai tjue førtini")
        self.assertEqual(self.normalizer.normalize("1.5.50"), "første mai nitten femti")
        self.assertEqual(NorwegianNormalizer(two_digit_year_pivot=0).normalize("1.5.26"), "første mai nitten tjueseks")

    def test_legal_structure_and_bad_spacing(self):
        self.check_cases({
            "jf. §2-1": "jamfør paragraf to en",
            "§2.1": "paragraf to en",
            "§ 2 - 1": "paragraf to en",
            "§2-1a": "paragraf to en a",
            "§ 136 a": "paragraf hundre og trettiseks a",
            "§ 2 i loven": "paragraf to i loven",
            "§§3-5": "paragrafene tre til fem",
            "§§3,4 og 5": "paragrafene tre, fire og fem",
            "§§ 3-4 til 3-7": "paragrafene tre fire til tre sju",
            "§§ 3-4–3-7": "paragrafene tre fire til tre sju",
            "§2(1)": "paragraf to første ledd",
            "§2(1)(b)": "paragraf to første ledd bokstav be",
            "§2-1 2.ledd 3.punktum bokstav b": "paragraf to en andre ledd tredje punktum bokstav be",
            "nr. 3, kap. 2, pkt. 4": "nummer tre, kapittel to, punkt fire",
            "§§ 2-1 og 2-2": "paragrafene to en og to to",
            "jf.§2-1(2)(b), §§3-4 til 3-7 og 2.ledd.": "jamfør paragraf to en andre ledd bokstav be, paragrafene tre fire til tre sju og andre ledd.",
        })

    def test_fractions_and_singular_units(self):
        self.check_cases({
            "1/2": "en halv", "2/3": "to tredeler", "3/4": "tre firedeler",
            "8/13": "åtte trettendeler", "9/34": "ni trettifiredeler",
            "1/100": "en hundredel", "2/1000": "to tusendeler",
            "-1/2": "minus en halv", "−1/2": "minus en halv",
            "2 1/2": "to og en halv", "-2 1/2": "minus to og en halv",
            "½": "en halv", "2½": "to og en halv", "¾": "tre firedeler",
            "⅔": "to tredeler", "1⁄2": "en halv", "1∕2": "en halv",
            "1/2 min": "ett halvt minutt", "2 1/2 min": "to og ett halvt minutt",
            "2/3 min": "to tredeler minutt", "½ l": "en halv liter",
            "1/2 kr": "en halv krone", "1/2 %": "en halv prosent",
            "1/2–3/4": "en halv til tre firedeler",
            "1/2–3/4 l": "en halv til tre firedeler liter",
        })

    def test_ratios_and_clock_context(self):
        self.check_cases({
            "4:3": "fire til tre", "16:9": "seksten til ni",
            "1 : 50 000": "en til femti tusen", "4∶3": "fire til tre",
            "Forholdet er 16:10": "Forholdet er seksten til ti",
            "format 16:10": "format seksten til ti", "blandingsforhold 1:10": "blandingsforhold en til ti",
            "12:30": "tolv tretti", "kl. 12:30": "klokka tolv tretti",
            "kl. 0905": "klokka ni null fem", "kl. 24:00": "klokka tjuefire",
            "kl. 09.00-10.30": "klokka ni til ti tretti",
            "09:00—10:30": "ni til ti tretti",
            "16:10-format": "seksten til ti-format",
        })

    def test_enumeration_markers_have_a_full_stop(self):
        self.check_cases({
            "1. Godkjenn.\n2. Send svar.": "en. Godkjenn.\nto. Send svar.",
            "1) Godkjenn.": "en. Godkjenn.",
            "a. Les.\nb) Svar.": "a. Les.\nbe. Svar.",
            "I. Les.\nII. Svar.\niv. Arkiver.": "en. Les.\nto. Svar.\nfire. Arkiver.",
            "  12. Tolvte punkt": "  tolv. Tolvte punkt",
            "• Les.\n- Svar.\n* Arkiver.": "punkt. Les.\npunkt. Svar.\npunkt. Arkiver.",
            "Velg: 1. Les.": "Velg: en. Les.",
        })

    def test_telephones_preserve_every_digit(self):
        self.check_cases({
            "tlf. 01234567": "telefon null en to tre fire fem seks sju",
            "Tlf: 12 34 56 78.": "telefon en to tre fire fem seks sju åtte.",
            "tlf. +47 12345678": "telefon pluss fire sju en to tre fire fem seks sju åtte",
            "telefonnummer 12-34-56-78": "telefonnummer en to tre fire fem seks sju åtte",
            "tlf.": "telefon.",
        })

    def test_area_volume_and_small_units(self):
        self.check_cases({
            "75 m2 og 2 m3": "syttifem kvadratmeter og to kubikkmeter",
            "75m2 og 2m3": "syttifem kvadratmeter og to kubikkmeter",
            "m2, m², m3 og m³": "kvadratmeter, kvadratmeter, kubikkmeter og kubikkmeter",
            "5 mg og 10 µg": "fem milligram og ti mikrogram",
            "1 mg": "ett milligram",
        })

    def test_all_dash_variants_are_ranges_but_legal_paths_are_not(self):
        for dash in DASH_CHARS:
            with self.subTest(dash=repr(dash)):
                self.assertEqual(self.normalizer.normalize(f"10{dash}15"), "ti til femten")
                self.assertEqual(self.normalizer.normalize(f"10{dash}15 m2"), "ti til femten kvadratmeter")
                self.assertEqual(self.normalizer.normalize(f"§2{dash}1"), "paragraf to en")

    def test_software_versions_and_release_metadata(self):
        self.check_cases({
            "v1.2.3": "versjon en punkt to punkt tre",
            "V2.10.0": "versjon to punkt ti punkt null",
            "1.2.3": "en punkt to punkt tre",
            "versjon 1.2": "versjon en punkt to",
            "versjonen v1.2.3": "versjonen en punkt to punkt tre",
            "v1.2.3-beta.2": "versjon en punkt to punkt tre beta punkt to",
            "v1.2.3-rc.1+build.42": "versjon en punkt to punkt tre err se punkt en pluss bygg punkt førtito",
            "v1.02.003": "versjon en punkt null to punkt null null tre",
            "Installer v1.2.3.": "Installer versjon en punkt to punkt tre.",
        })

    def test_invalid_forms_are_retained_as_whole_spans(self):
        for text in ("31/2/2026", "2026-13-01", "29.2.2025", "1/0", "1/2/3", "1:2:3",
                     "tlf. 12", "§§3-4-3-7", "31. februar 26", "kl. 24:01"):
            with self.subTest(text=text):
                report = self.normalizer.analyze(text)
                self.assertEqual(report.text, text)
                self.assertTrue(report.needs_review)


if __name__ == "__main__":
    unittest.main()
