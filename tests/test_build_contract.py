from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
CONTAINERFILE = (REPO / "Containerfile").read_text()
WORKFLOW = (REPO / ".github/workflows/reusable-build.yaml").read_text()
MAIN_WORKFLOW = (REPO / ".github/workflows/build.yaml").read_text()
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

    def test_runtime_inputs_follow_package_layer(self):
        package_layer = CONTAINERFILE.index("RUN --mount=type=bind")

        self.assertLess(
            CONTAINERFILE.index("COPY overlay-root/etc/pki/rpm-gpg/"),
            package_layer,
        )
        self.assertLess(
            CONTAINERFILE.index("COPY overlay-root/etc/yum.repos.d/"),
            package_layer,
        )
        self.assertGreater(CONTAINERFILE.index("COPY overlay-root/ /"), package_layer)
        self.assertGreater(
            CONTAINERFILE.index("COPY secret-run/secret_run.py"),
            package_layer,
        )
        self.assertGreater(
            CONTAINERFILE.index("COPY secret-run/laptop-backup.sh"),
            package_layer,
        )

    def test_ci_preserves_layers_and_configures_remote_cache(self):
        self.assertIn("layers: true", WORKFLOW)
        self.assertIn("squash: false", WORKFLOW)
        self.assertIn("--cache-from ${{ inputs.cache_ref }}", WORKFLOW)
        self.assertIn("--cache-to ${{ inputs.cache_ref }}", WORKFLOW)
        self.assertIn("cache_ref:", MAIN_WORKFLOW)

        cache_refs = [
            line.split("cache_ref:", 1)[1].strip()
            for line in MAIN_WORKFLOW.splitlines()
            if "cache_ref:" in line
        ]
        self.assertTrue(cache_refs)
        self.assertTrue(
            all(":" not in ref.rsplit("/", 1)[-1] for ref in cache_refs)
        )
        self.assertTrue(all("@" not in ref for ref in cache_refs))


if __name__ == "__main__":
    unittest.main()
