import json
import subprocess
import sys
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.voxcpm import generate_norwegian


class CurrencyTests(unittest.TestCase):
    def check_cases(self, cases, **options):
        normalizer = NorwegianNormalizer(**options)
        for original, expected in cases.items():
            with self.subTest(original=original, options=options):
                report = normalizer.analyze(original)
                self.assertEqual(report.text, expected)
                self.assertFalse(report.issues, report.issues)
                self.assertEqual(normalizer.normalize(expected), expected)
                rebuilt = original
                for change in reversed(report.replacements):
                    self.assertEqual(original[change.start:change.end], change.original)
                    rebuilt = rebuilt[:change.start] + change.spoken + rebuilt[change.end:]
                self.assertEqual(rebuilt, expected)

    def test_norwegian_names_and_singular_plural(self):
        self.check_cases({
            "100 USD": "hundre amerikanske dollar",
            "USD 1": "en amerikansk dollar",
            "EUR 12": "tolv euro",
            "€ 1": "en euro",
            "GBP 1": "ett britisk pund",
            "£ 2": "to britiske pund",
            "SEK 1": "en svensk krone", "SEK 2": "to svenske kroner",
            "DKK 1": "en dansk krone", "DKK 2": "to danske kroner",
            "CAD 1": "en kanadisk dollar", "AUD 2": "to australske dollar",
            "CHF 2": "to sveitsiske franc", "CNY 2": "to kinesiske yuan",
            "JPY 100": "hundre japanske yen", "KWD 2": "to kuwaitiske dinarer",
            "1 euro og 2 euros": "en euro og to euro",
            "2 US dollars": "to amerikanske dollar",
            "1 British pound": "ett britisk pund",
        })

    def test_minor_units_and_zero_negative_amounts(self):
        self.check_cases({
            "EUR 12,50": "tolv euro og femti cent",
            "EUR 1,01": "en euro og en cent",
            "USD 0,01": "null amerikanske dollar og en cent",
            "GBP 1,01": "ett britisk pund og en penny",
            "GBP 2,50": "to britiske pund og femti pence",
            "SEK 1,01": "en svensk krone og ett øre",
            "DKK 2,50": "to danske kroner og femti øre",
            "CAD 1,01": "en kanadisk dollar og en cent",
            "AUD 0,50": "null australske dollar og femti cent",
            "KWD 1,005": "en kuwaitisk dinar og fem fils",
            "KWD 1,5": "en kuwaitisk dinar og fem hundre fils",
            "CHF 1,20": "en komma to null sveitsiske franc",
            "CNY 2,50": "to komma fem null kinesiske yuan",
            "EUR -0,01": "minus null euro og en cent",
            "-€1,25": "minus en euro og tjuefem cent",
            "€-1,25": "minus en euro og tjuefem cent",
            "−USD 1": "minus en amerikansk dollar",
            "EUR 1,00": "en euro",
            "EUR ,50": "null euro og femti cent",
        })

    def test_norwegian_grouping_and_nok_compatibility(self):
        self.check_cases({
            "USD 1.234,56": "ett tusen to hundre og trettifire amerikanske dollar og femtiseks cent",
            "EUR 1 234,56": "ett tusen to hundre og trettifire euro og femtiseks cent",
            "EUR 1\u202f234,56": "ett tusen to hundre og trettifire euro og femtiseks cent",
            "kr 150,-": "hundre og femti kroner",
            "150,- kr": "hundre og femti kroner",
            "5 kr 50 øre": "fem kroner og femti øre",
            "NOK 1,01": "en krone og ett øre",
            "kr 150,-, 3,14 og 1. mai": "hundre og femti kroner, tre komma en fire og første mai",
        })

    def test_explicit_english_currency_number_format_is_still_spoken_norwegian(self):
        self.check_cases({
            "USD 1,234.56": "ett tusen to hundre og trettifire amerikanske dollar og femtiseks cent",
            "US$12.50": "tolv amerikanske dollar og femti cent",
            "£12.50": "tolv britiske pund og femti pence",
            "EUR 1.05": "en euro og fem cent",
            "EUR .50": "null euro og femti cent",
            "The price is USD 12.50.": "The price is tolv amerikanske dollar og femti cent.",
            "3,14 kg": "tre komma en fire kilo",
        }, currency_locale="en-US")

    def test_ambiguous_and_qualified_symbols(self):
        self.check_cases({
            "US$ 10": "ti amerikanske dollar",
            "C$ 10": "ti kanadiske dollar", "CA$10": "ti kanadiske dollar",
            "A$ 10": "ti australske dollar", "AU$10": "ti australske dollar",
            "CN¥10": "ti kinesiske yuan", "JP¥10": "ti japanske yen",
            "$10 USD": "ti amerikanske dollar", "$10 CAD": "ti kanadiske dollar",
            "¥10 CNY": "ti kinesiske yuan", "kr 10 SEK": "ti svenske kroner",
        })
        self.check_cases({"$12,50": "tolv amerikanske dollar og femti cent"}, symbol_currencies={"$": "USD"})
        self.check_cases({"¥100": "hundre japanske yen"}, symbol_currencies={"¥": "JPY"})
        self.check_cases({"$10 CAD": "ti kanadiske dollar"}, symbol_currencies={"$": "USD"})

    def test_ranges_and_matching_paired_markers(self):
        self.check_cases({
            "10–15 EUR": "ti til femten euro", "EUR 10-15": "ti til femten euro",
            "USD 10–USD 15": "ti til femten amerikanske dollar",
            "10 EUR–15 EUR": "ti til femten euro",
            "$10–15 USD": "ti til femten amerikanske dollar",
            "EUR 1,50–2,25": "en euro og femti cent til to euro og tjuefem cent",
            "NOK -5–-2": "minus fem til minus to kroner",
            "USD 10 USD": "ti amerikanske dollar",
        })

    def test_invalid_ambiguous_or_unsupported_amounts_stay_whole(self):
        cases = ("$10", "¥10", "10 dollars", "EUR 1,234", "JPY 1,01", "KWD 1,2345", "USD 12.50",
                 "EUR 1 23", "EUR 1..234", "EUR 1,,2", "EUR 1.234 567", "USD 1.2.2026",
                 "US$10 CAD", "€10 USD", "EUR 10–GBP 15", "10 EUR–15 GBP", "-€-1",
                 "100 RUB", "₹100", "EUR 1000000000000")
        for original in cases:
            with self.subTest(original=original):
                report = NorwegianNormalizer().analyze(original)
                self.assertEqual(report.text, original)
                self.assertTrue(report.needs_review)
        for original in ("EUR 1.234,56", "EUR 1,,2", "kr 150,-"):
            with self.subTest(en_US=original):
                report = NorwegianNormalizer(currency_locale="en-US").analyze(original)
                self.assertEqual(report.text, original)
                self.assertTrue(report.needs_review)

    def test_currency_rules_do_not_steal_versions_units_dates_or_other_amounts(self):
        self.check_cases({
            "USD 1, EUR 2": "en amerikansk dollar, to euro",
            "v1.2.3, 1.5.26 og EUR 1,05": "versjon en punkt to punkt tre, første mai to tusen og tjueseks og en euro og fem cent",
            "5 MW på NRK1 koster EUR 2,50.": "fem megawatt på enn err kå en koster to euro og femti cent.",
            "1/2 kr": "en halv krone",
            "De veier 10 pounds.": "De veier ti pounds.",
        })

    def test_invalid_configuration_and_adapter_review(self):
        for options in ({"currency_locale": "auto"}, {"symbol_currencies": {"$": "GBP"}},
                        {"symbol_currencies": {"¥": "NOK"}}, {"symbol_currencies": {"kr": "SEK"}}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                NorwegianNormalizer(**options)
        class Model:
            def generate(self, **kwargs):
                raise AssertionError("ambiguous currency must not reach the model")
        with self.assertRaises(ValueError):
            generate_norwegian(Model(), "$10")

    def test_cli_exposes_format_and_symbol_choices(self):
        completed = subprocess.run([sys.executable, "-m", "nb_tn", "--strict", "--json", "--currency-locale", "en-US",
                                    "--dollar-currency", "CAD", "$12.50"], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["text"], "tolv kanadiske dollar og femti cent")
        self.assertFalse(report["needs_review"])

    def test_cli_requires_a_choice_for_bare_dollar(self):
        completed = subprocess.run([sys.executable, "-m", "nb_tn", "--strict", "--json", "--currency-locale", "en-US",
                                    "$12.50"], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 2)
        report = json.loads(completed.stdout)
        self.assertEqual(report["text"], "$12.50")
        self.assertTrue(report["needs_review"])


if __name__ == "__main__":
    unittest.main()
