"""Explicit expectations for paired years, unit policy and short currency names."""

from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import unittest

from nb_tn import NorwegianNormalizer
from nb_tn.numbers import year


class ReadingOptionsTests(unittest.TestCase):
    def check(self, source, expected, **options):
        n = NorwegianNormalizer(**options)
        r = n.analyze(source)
        self.assertEqual(r.text, expected)
        self.assertFalse(r.issues, r.issues)
        self.assertEqual(n.normalize(expected), expected)
        rebuilt = source
        for c in reversed(r.replacements):
            self.assertEqual(source[c.start:c.end], c.original)
            rebuilt = rebuilt[:c.start] + c.spoken + rebuilt[c.end:]
        self.assertEqual(rebuilt, expected)

    def test_paired_years_and_traditional_option(self):
        for lang, one in (("nb", "en"), ("nn", "ein")):
            for value, expected in {
                1000: "ti hundre", 1001: f"ti null {one}", 1099: "ti nittini",
                1905: "nitten null fem", 1984: "nitten åttifire", 2000: "tjue hundre",
                2001: f"tjue null {one}", 2005: "tjue null fem", 2010: "tjue ti",
                2026: "tjue tjueseks", 2100: f"tjue{one} hundre", 9999: "nittini nittini",
            }.items():
                with self.subTest(lang=lang, value=value):
                    self.assertEqual(year(value, language=lang), expected)
                    self.check(f"året {value}", "året " + expected, language=lang)
            self.check("1.5.26", "første mai tjue tjueseks", language=lang)
            self.check("1.5.26", "første mai to tusen og tjueseks", language=lang, year_style="traditional")
            self.check("2005 m", "to tusen og fem meter", language=lang)
            self.check("v20.26", "versjon tjue punkt tjueseks", language=lang)
            self.assertEqual(year(999, language=lang), "ni hundre og nittini")
            self.assertEqual(year(1905, language=lang, style="traditional"), "nitten null fem")
        for source in ("1.–3. mai 2026", "01.05.2026–03.05.2026", "dato 20260501", "året 2026"):
            self.assertIn("to tusen og tjueseks", NorwegianNormalizer(year_style="traditional").normalize(source))
            self.assertIn("tjue tjueseks", NorwegianNormalizer().normalize(source))

    def test_unit_toggle_across_quantity_paths(self):
        for lang, one, times, raised in (("nb", "en", "ganger", "opphøyd"), ("nn", "ein", "gonger", "opphøgd")):
            for enabled, suffix in ((True, "volt"), (False, "ve")):
                for source, expected in {
                    "2 V": "to " + suffix,
                    "−2 V": "minus to " + suffix,
                    "1,25 V": f"{one} komma tjuefem " + suffix,
                    "2–3 V": "to til tre " + suffix,
                    "1/2 V": f"{one} halv " + suffix,
                    "1.2e-3 V": f"{one} komma to {times} ti {raised} i minus tre " + suffix,
                }.items():
                    self.check(source, expected, language=lang, scientific_units=enabled)
            self.check("2 N, 3 C, 4 J, 5 A, 6 V, 7 W og 8 K",
                       "to enn, tre se, fire jådd, fem a, seks ve, sju dobbeltve og åtte kå",
                       language=lang, scientific_units=False)
            self.check("2 N", "to newton", language=lang)
            self.check("2 B", "to be", language=lang, scientific_units=False)
            for enabled in (False, True):
                self.check("C F K", "C F K", language=lang, scientific_units=enabled)
                r = NorwegianNormalizer(language=lang, scientific_units=enabled).analyze("2 N. Hansen")
                self.assertEqual(r.text, "2 N. Hansen")
                self.assertTrue(r.needs_review)

    def test_everyday_units_and_explicit_compounds_survive_toggle(self):
        for lang in ("nb", "nn"):
            for enabled in (False, True):
                self.check("2 m, 2 g, 2 kg, 2 mg, 2 l, 2 s og 2 h",
                           "to meter, to gram, to kilo, to milligram, to liter, to " +
                           ("sekunder og to timer" if lang == "nb" else "sekund og to timar"),
                           language=lang, scientific_units=enabled)
                self.check("20 °C, 68 °F, 2 m/s, 2 kW og 2 V/m",
                           "tjue grader celsius, sekstiåtte grader fahrenheit, to meter per sekund, to kilowatt og to volt per meter",
                           language=lang, scientific_units=enabled)

    def test_plain_symbols_and_explicit_currency_markers(self):
        for lang, one in (("nb", "en"), ("nn", "ein")):
            for source, expected in {
                "$20 og ¥20": "tjue dollar og tjue yuan",
                "$1": f"{one} dollar", "¥1": f"{one} yuan",
                "$1,25": f"{one} dollar og tjuefem cent",
                "¥1,25": f"{one} komma tjuefem yuan",
                "-$1": f"minus {one} dollar",
                "$2–$3": "to til tre dollar", "¥2–3": "to til tre yuan",
                "$1,25–2,50": f"{one} dollar og tjuefem cent til to dollar og femti cent",
                "USD 20, CAD 20 og CNY 20": "tjue amerikanske dollar, tjue kanadiske dollar og tjue kinesiske yuan",
                "$20 USD og ¥20 CNY": "tjue amerikanske dollar og tjue kinesiske yuan",
            }.items():
                self.check(source, expected, language=lang)
            self.check("¥1,25", f"{one} komma to fem yuan", language=lang, decimal_style="digits")
            self.check("$20", "tjue kanadiske dollar", language=lang, symbol_currencies={"$": "CAD"})
            self.check("¥20", "tjue japanske yen", language=lang, symbol_currencies={"¥": "JPY"})
            for marker in ("$", "¥"):
                self.assertTrue(NorwegianNormalizer(symbol_currencies={marker: None}).analyze(marker + "20").needs_review)

    def test_abbreviation_aliases_and_language_forms(self):
        for lang, one, neuter in (("nb", "en", "ett"), ("nn", "ein", "eitt")):
            self.check("f.eks 2 mins, bl.a 3 hrs og pga kø",
                       "for eksempel to minutter, blant annet tre timer og på grunn av kø" if lang == "nb" else
                       "for eksempel to minutt, blant anna tre timar og på grunn av kø", language=lang, english_unit_aliases=True)
            self.check("1 hr og 1 sec", f"{one} time og {neuter} sekund", language=lang, english_unit_aliases=True)
            self.check("2 secs", "to sekunder" if lang == "nb" else "to sekund", language=lang, english_unit_aliases=True)
            self.check("F.eks. kaffe, osv.", "for eksempel kaffe, " + ("og så videre." if lang == "nb" else "og så vidare."), language=lang)
            self.check("mins hrs secs", "mins hrs secs", language=lang)
            self.check("f.eksperiment", "f.eksperiment", language=lang)
        self.check("t.d kaffi, m.a te, osb", "til dømes kaffi, mellom anna te, og så bortetter", language="nn")

    def test_cli_and_instance_isolation(self):
        result = subprocess.run([sys.executable, "-m", "nb_tn", "--language", "nn",
                                 "--no-scientific-units", "--year-style", "traditional",
                                 "året 2026, 2 V og $20"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "året to tusen og tjueseks, to ve og tjue dollar")
        defaults = NorwegianNormalizer()
        alternate = NorwegianNormalizer(scientific_units=False, year_style="traditional", language="nn")
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(n.normalize, "året 2026 og 2 V") for n in (defaults, alternate) * 5]
            for i, job in enumerate(jobs):
                self.assertEqual(job.result(), "året to tusen og tjueseks og to ve" if i % 2 else "året tjue tjueseks og to volt")
        for kwargs in ({"year_style": "invalid"}, {"scientific_units": "False"}, {"scientific_units": 0}):
            with self.assertRaises(ValueError):
                NorwegianNormalizer(**kwargs)
