import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.units import parse_unit
from nb_tn.voxcpm import generate_norwegian


class UnitAndChannelTests(unittest.TestCase):
    def setUp(self):
        self.normalizer = NorwegianNormalizer()

    def check_cases(self, cases):
        for original, expected in cases.items():
            with self.subTest(original=original):
                report = self.normalizer.analyze(original)
                self.assertEqual(report.text, expected)
                self.assertFalse(report.issues, report.issues)
                self.assertEqual(self.normalizer.normalize(expected), expected)
                rebuilt = original
                for change in reversed(report.replacements):
                    self.assertEqual(original[change.start:change.end], change.original)
                    rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
                self.assertEqual(rebuilt, expected)

    def test_physical_quantities_and_exact_case_prefixes(self):
        self.check_cases({
            "5 MW og 5 mW": "fem megawatt og fem milliwatt",
            "2 mA og 3 MA": "to milliampere og tre megaampere",
            "12 kWh og 2 MWh": "tolv kilowattimer og to megawattimer",
            "230 V": "to hundre og tretti volt",
            "100 MHz": "hundre megahertz",
            "1013 hPa": "ett tusen og tretten hektopascal",
            "2 kPa, 3 MPa og 4 bar": "to kilopascal, tre megapascal og fire bar",
            "5 J og 10 GJ": "fem joule og ti gigajoule",
            "5 N": "fem newton",
            "2 Ω og 3 MΩ": "to ohm og tre megaohm",
            "2 Ω": "to ohm",
            "2 S og 2 s": "to siemens og to sekunder",
            "2 nF og 5 µF": "to nanofarad og fem mikrofarad",
            "3 μA og 4 uA": "tre mikroampere og fire mikroampere",
            "5 Bq og 2 mSv": "fem becquerel og to millisievert",
            "5 Gy, 3 lx og 2 lm": "fem gray, tre lux og to lumen",
            "2 mol og 3 cd": "to mol og tre candela",
            "5 °F og 273 K": "fem grader fahrenheit og to hundre og syttitre kelvin",
            "45°": "førtifem grader",
            "2 ha og 5 daa": "to hektar og fem dekar",
            "5 mL og 2 ML": "fem milliliter og to megaliter",
            "5 ml og 2 L": "fem milliliter og to liter",
            "1 h, 2 h og 5 ms": "en time, to timer og fem millisekunder",
        })

    def test_singular_plural_and_fraction_units(self):
        self.check_cases({
            "1 s og 2 s": "ett sekund og to sekunder",
            "1 kWh og 2 kWh": "en kilowattime og to kilowattimer",
            "0,1 kWh": "null komma en kilowattimer",
            "10–15 MW": "ti til femten megawatt",
            "1/2 kWh": "en halv kilowattime",
            "1/2–3/4 kWh": "en halv til tre firedeler kilowattime",
            "1/2 ms": "ett halvt millisekund",
        })

    def test_compound_units_and_powers(self):
        self.check_cases({
            "9,81 m/s²": "ni komma åttien meter per sekund i annen",
            "9,81 m/s2": "ni komma åttien meter per sekund i annen",
            "9,81 m/s^2": "ni komma åttien meter per sekund i annen",
            "5 kg/m³": "fem kilo per kubikkmeter",
            "5 g/cm3": "fem gram per kubikkcentimeter",
            "5 N·m": "fem newton meter",
            "5 N * m": "fem newton meter",
            "5 s⁻¹": "fem per sekund",
            "5 s^-1": "fem per sekund",
            "2 m^4": "to meter i fjerde potens",
            "5 m²/s": "fem kvadratmeter per sekund",
            "5 J/kg/K": "fem joule per kilo kelvin",
            "80 km/h": "åtti kilometer i timen",
            "10–15 kg/m3": "ti til femten kilo per kubikkmeter",
        })

    def test_unknown_symbol_units_are_not_partially_normalized(self):
        for original in ("5 mw", "5 mhz", "5 kwh", "5 XYZ", "5XYZ", "½XYZ", "5 m/xyz",
                         "5 W/(m²·K)", "5 m^10", "5 m^0", "5 m//s", "5 m/", "5 m^",
                         "1/2 XYZ", "10–15 XYZ"):
            with self.subTest(original=original):
                report = self.normalizer.analyze(original)
                self.assertEqual(report.text, original)
                self.assertTrue(report.needs_review)
        with self.assertRaises(ValueError):
            parse_unit("mw")

    def test_ordinary_count_nouns_are_not_units(self):
        self.check_cases({
            "5 personer og 3 hus": "fem personer og tre hus",
            "5 Oslo-bilder": "fem Oslo-bilder",
            "1 dag og 2 dager": "en dag og to dager",
            "3,14 kg og 2 m²": "tre komma fjorten kilo og to kvadratmeter",
        })

    def test_broadcast_names_and_aliases(self):
        self.check_cases({
            "NRK1, NRK 2 og NRK3": "enn err kå en, enn err kå to og enn err kå tre",
            "TV2, TV 2 og TVNorge": "te ve to, te ve to og te ve Norge",
            "TV 2 Direkte og TV2 Nyheter": "te ve to direkte og te ve to nyheter",
            "TV 2 Sport Premium 2": "te ve to sport premium to",
            "NRK P1+ og NRK P1": "enn err kå pe en pluss og enn err kå pe en",
            "NRKP1 +": "enn err kå pe en pluss",
            "NRK P3 Musikk og NRK P13": "enn err kå pe tre musikk og enn err kå pe tretten",
            "NRK mP3 og mp3": "enn err kå emm pe tre og emm pe tre",
            "P4, P5 Hits og P6 Rock": "pe fire, pe fem Hits og pe seks Rock",
            "P7 Klem og P10 Country": "pe sju Klem og pe ti Country",
            "P11 Dance og P12 Hitmix": "pe elleve Dance og pe tolv Hitmix",
            "NRK Nyheter, NRK Klassisk og NRK Jazz": "enn err kå nyheter, enn err kå klassisk og enn err kå jazz",
            "NRK Super og NRK Tegnspråk": "enn err kå super og enn err kå tegnspråk",
            "NRK TV og Radio Norge": "enn err kå te ve og Radio Norge",
        })

    def test_longest_channel_match_and_boundaries(self):
        report = self.normalizer.analyze("NRK P1+")
        self.assertEqual(len(report.replacements), 1)
        self.assertEqual(report.replacements[0].original, "NRK P1+")
        self.assertEqual(report.replacements[0].category, "channel")
        for text in ("P42", "NRK10", "minTV2app", "TV2.no", "https://tv2.no/NRK1"):
            with self.subTest(text=text):
                self.assertEqual(self.normalizer.normalize(text), text)

    def test_channel_dictionary_is_replaceable_or_can_be_disabled(self):
        n = NorwegianNormalizer(channels={"Min Radio 7": "min radio sju"})
        self.assertEqual(n.normalize("MinRadio7"), "min radio sju")
        self.assertTrue(n.analyze("NRK1").needs_review)
        self.assertTrue(NorwegianNormalizer(channels={}).analyze("P4").needs_review)

    def test_combined_text_and_adapter_review(self):
        self.check_cases({
            "På NRK1 kl. 09:05: 5 MW og 12 kWh.": "På enn err kå en klokka ni null fem: fem megawatt og tolv kilowattimer.",
        })
        class Model:
            def generate(self, **kwargs):
                raise AssertionError("unreviewed unknown units must not reach TTS")
        with self.assertRaises(ValueError):
            generate_norwegian(Model(), "5 mw")


if __name__ == "__main__":
    unittest.main()
