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

    def test_every_buildah_job_selects_vfs_before_building(self):
        configure = "run: ./scripts/configure-ci-container-storage.sh"
        buildah = "uses: redhat-actions/buildah-build@"
        self.assertEqual(WORKFLOW.count(configure), 2)
        self.assertEqual(WORKFLOW.count(buildah), 2)

        for job in WORKFLOW.split("\n  build-")[1:]:
            if buildah not in job:
                continue
            self.assertLess(job.index(configure), job.index(buildah))

    def test_storage_configurator_selects_vfs_and_preserves_options(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "system-storage.conf"
            destination = temp / "user" / "storage.conf"
            source.write_text(
                "[storage]\n"
                'driver = "overlay"\n'
                'graphroot = "/var/lib/containers/storage"\n'
                "\n[storage.options.overlay]\n"
                'mount_program = "/usr/local/bin/fuse-overlayfs"\n'
            )

            environment = os.environ.copy()
            environment["HOME"] = str(temp / "home")
            subprocess.run(
                [STORAGE_SCRIPT, source, destination],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

            configured = destination.read_text()
            self.assertIn('driver = "vfs"', configured)
            self.assertIn('graphroot = "/var/lib/containers/storage"', configured)
            self.assertIn('mount_program = "/usr/local/bin/fuse-overlayfs"', configured)

    def test_storage_configurator_creates_vfs_config_when_system_config_is_missing(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "missing-storage.conf"
            destination = temp / "user" / "storage.conf"

            subprocess.run(
                [STORAGE_SCRIPT, source, destination],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(destination.read_text(), '[storage]\ndriver = "vfs"\n')


if __name__ == "__main__":
    unittest.main()
