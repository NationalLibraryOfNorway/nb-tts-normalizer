from copy import deepcopy
import unittest
from unittest.mock import patch

from nb_tn.provenance import load_manifest, verify_provenance


class ProvenanceTests(unittest.TestCase):
    def test_shipped_manifest_covers_changed_implementation(self):
        manifest = load_manifest()
        self.assertEqual(set(manifest["artifacts"]), {
            "profiles.py", "numbers.py", "readings.py", "units.py", "currencies.py",
            "legal.py", "channels.py", "normalizer.py", "__main__.py", "provenance.py", "pdf_unit_inventory.json", "scientific.py",
        })
        self.assertEqual(verify_provenance(manifest), [])
        self.assertEqual(manifest["sources"]["cldr-nn-49"]["revision"],
                         "96e54b273d2da4ec6fbad350ba19ff23fa24a588")
        self.assertEqual(manifest["sources"]["cldr-nn-49"]["license"], "Unicode-3.0")

    def test_offline_audit_never_fetches_references(self):
        with patch("nb_tn.provenance.urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            self.assertEqual(verify_provenance(), [])

    def test_scientific_sources_are_traceable_not_falsely_byte_pinned(self):
        manifest = load_manifest()
        names = {"scientific-ndla", "scientific-matematikk", "scientific-mattehefte",
                 "scientific-wikibooks", "scientific-decimals", "scientific-policy"}
        self.assertTrue(names.issubset(manifest["artifacts"]["scientific.py"]["sources"]))
        for name in names:
            self.assertNotIn("sha256", manifest["sources"][name])
        self.assertEqual(manifest["sources"]["scientific-wikibooks"]["revision"], "3338134")

    def test_unit_power_policy_has_both_document_and_language_sources(self):
        manifest = load_manifest()
        for name in ("profiles.py", "units.py"):
            self.assertTrue({"government-unit-draft", "sprakradet-ordinals"}.issubset(
                manifest["artifacts"][name]["sources"]))
        reference = manifest["sources"]["government-unit-draft"]
        self.assertIn("[dato] 2007", reference["role"])
        self.assertNotIn("sha256", reference)  # No bytes were retrieved for hashing.

    def test_direct_pdf_is_now_byte_pinned_and_inventory_is_tracked(self):
        m = load_manifest()
        source = m["sources"]["government-unit-pdf-bytes"]
        self.assertEqual(source["bytes"], 269420)
        self.assertEqual(source["sha256"], "f2eac3904b09efab0a9651ee23d4d43424d6b1bbef705f5aa19577ab8c2b6986")
        self.assertIn("government-unit-pdf-bytes", m["artifacts"]["pdf_unit_inventory.json"]["sources"])

    def test_artifact_changes_are_detected_not_silently_refreshed(self):
        original = load_manifest()
        changed = deepcopy(original)
        changed["artifacts"]["profiles.py"]["sha256"] = "0" * 64
        self.assertIn("artifact changed without provenance update: profiles.py", verify_provenance(changed))
        self.assertEqual(changed["artifacts"]["profiles.py"]["sha256"], "0" * 64)
        self.assertEqual(load_manifest(), original)

    def test_missing_references_invalid_digests_and_paths_are_rejected(self):
        changed = deepcopy(load_manifest())
        changed["artifacts"]["profiles.py"]["sources"] = ["unrecorded-source"]
        self.assertIn("incomplete artifact provenance: profiles.py", verify_provenance(changed))
        changed["artifacts"]["../outside.py"] = changed["artifacts"]["profiles.py"]
        self.assertIn("invalid package artifact path: ../outside.py", verify_provenance(changed))
        changed["artifacts"]["profiles.py"]["sha256"] = "bad-hash"
        self.assertIn("invalid artifact digest: profiles.py", verify_provenance(changed))
        changed["schema_version"] = 999
        self.assertIn("unsupported provenance schema", verify_provenance(changed))
