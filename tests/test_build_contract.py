import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
CONTAINERFILE = (REPO / "Containerfile").read_text()
WORKFLOW = (REPO / ".github/workflows/reusable-build.yaml").read_text()
STORAGE_SCRIPT = REPO / "scripts/configure-ci-container-storage.sh"


class BuildContractTests(unittest.TestCase):
    def test_selinux_policy_store_is_copied_up_before_dnf(self):
        package_layer = CONTAINERFILE[
            CONTAINERFILE.index("# Install the packages") : CONTAINERFILE.index(
                '\n\nRUN ["bootc", "container", "lint"]'
            )
        ]
        steps = (
            "cp -a /etc/selinux/targeted /etc/selinux/targeted.rebuilt",
            "rm -rf /etc/selinux/targeted",
            "mv /etc/selinux/targeted.rebuilt /etc/selinux/targeted",
            "python3 /dnfdef.py",
        )
        positions = [package_layer.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(CONTAINERFILE.count(steps[0]), 1)


if __name__ == "__main__":
    unittest.main()
