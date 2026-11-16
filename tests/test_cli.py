#!/usr/bin/env python3
"""Behaviour tests for video-shotcraft-draft-verify (stdlib unittest only)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "video-shotcraft-draft-verify")
IN = os.path.join(ROOT, "examples", "in")
OUT = os.path.join(ROOT, "examples", "out")


def run(*args):
    return subprocess.run([sys.executable, BIN] + list(args),
                          capture_output=True, text=True, cwd=ROOT)


class VerifierTests(unittest.TestCase):
    def test_valid_mac_exits_zero(self):
        proc = run("examples/in/valid-mac", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_valid_mac_stats(self):
        data = json.loads(run("examples/in/valid-mac", "--json").stdout)
        self.assertEqual(data["stats"]["tracks"], 3)
        self.assertEqual(data["stats"]["segments"], 3)
        self.assertEqual(data["stats"]["media"], 2)

    def test_valid_mac_only_privacy_warning(self):
        data = json.loads(run("examples/in/valid-mac", "--json").stdout)
        self.assertEqual([f["id"] for f in data["findings"]], ["J030"])

    def test_valid_windows_passes_without_meta(self):
        proc = run("examples/in/valid-windows", "--json")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual([f["id"] for f in data["findings"]], ["J024"])

    def test_broken_exits_one(self):
        self.assertEqual(run("examples/in/broken-mac", "--json").returncode, 1)

    def test_unknown_material_id(self):
        findings = json.loads(run("examples/in/broken-mac", "--json").stdout)["findings"]
        self.assertIn("J011", [f["id"] for f in findings])

    def test_track_type_mismatch(self):
        findings = json.loads(run("examples/in/broken-mac", "--json").stdout)["findings"]
        self.assertIn("J012", [f["id"] for f in findings])

    def test_overlap_on_same_track(self):
        findings = json.loads(run("examples/in/broken-mac", "--json").stdout)["findings"]
        self.assertIn("J016", [f["id"] for f in findings])

    def test_range_exceeds_draft_and_source(self):
        ids = [f["id"] for f in json.loads(run("examples/in/broken-mac", "--json").stdout)["findings"]]
        self.assertIn("J014", ids)
        self.assertIn("J015", ids)

    def test_missing_and_external_media(self):
        ids = [f["id"] for f in json.loads(run("examples/in/broken-mac", "--json").stdout)["findings"]]
        self.assertIn("J020", ids)
        self.assertIn("J021", ids)

    def test_registration_missing_and_stale(self):
        ids = [f["id"] for f in json.loads(run("examples/in/broken-mac", "--json").stdout)["findings"]]
        self.assertIn("J022", ids)
        self.assertIn("J023", ids)

    def test_bad_json_is_input_error(self):
        proc = run("examples/in/bad-json", "--json")
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(json.loads(proc.stdout)["ok"])

    def test_missing_directory_is_input_error(self):
        proc = run("examples/in/does-not-exist", "--json")
        self.assertEqual(proc.returncode, 2)

    def test_strict_promotes_warning(self):
        proc = run("examples/in/valid-windows", "--json", "--strict")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)["findings"][0]["severity"], "error")

    def test_mac_and_windows_entry_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "valid-mac")
            shutil.copytree(os.path.join(IN, "valid-mac"), target)
            with open(os.path.join(target, "draft_content.json"), "a") as fh:
                fh.write(" ")
            proc = run(target, "--json")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("J003", [f["id"] for f in json.loads(proc.stdout)["findings"]])

    def test_human_output_summary(self):
        proc = run("examples/in/valid-mac")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("OK: 3 track(s), 3 segment(s)", proc.stdout)
        proc = run("examples/in/broken-mac")
        self.assertIn("FAIL:", proc.stdout)

    def test_golden_outputs_match(self):
        for name in ("valid-mac", "valid-windows", "broken-mac"):
            with open(os.path.join(OUT, name + ".json"), encoding="utf-8") as fh:
                expected = json.load(fh)
            actual = json.loads(run("examples/in/" + name, "--json").stdout)
            self.assertEqual(actual, expected, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)