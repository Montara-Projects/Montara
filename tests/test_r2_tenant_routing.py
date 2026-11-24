"""Tenant-routing security contract: requires authenticated server context."""
import unittest
from uuid import uuid4

from urano.r2_tenant_routing import (
    R2_BUCKET, R2_ENDPOINT, TenantRoutingDenied, expected_tenant_for_instance,
    verified_tenant_for_owner, require_cloud_only, plan_owner_object,
)

OWNER = {"owner-jm": "pilot-amehc", "owner-fer": "pilot-fergardel",
         "owner-main": "pilot-t4t"}


class CloudTenantRoutingTests(unittest.TestCase):
    def make(self, instance="jmlab", owner="owner-jm", **kwargs):
        opts = dict(
            trusted_instance=instance, verified_owner_id=owner,
            owner_tenants=OWNER, project_id=str(uuid4()), asset_id=str(uuid4()),
            asset_class="originals", extension="mp4",
        )
        opts.update(kwargs)
        return plan_owner_object(**opts)

    def test_jm_routes_only_to_amehc(self):
        p = self.make()
        self.assertEqual("pilot-amehc", p.tenant_id)
        self.assertEqual("montara-media-eu-pilot", p.bucket)
        self.assertTrue(p.endpoint.endswith(".eu.r2.cloudflarestorage.com"))
        self.assertEqual("eu", p.jurisdiction)
        self.assertTrue(p.key.startswith("tenants/pilot-amehc/projects/"))

    def test_fer_aliases_route_only_to_fergardel(self):
        for instance in ("fertrial", "montara-lab-fer"):
            with self.subTest(instance=instance):
                self.assertEqual("pilot-fergardel",
                                 self.make(instance, "owner-fer").tenant_id)

    def test_main_routes_only_to_t4t(self):
        for instance in ("main", "betamain", "montara-main"):
            with self.subTest(instance=instance):
                self.assertEqual("pilot-t4t",
                                 self.make(instance, "owner-main").tenant_id)

    def test_unmapped_lab_denied(self):
        for instance in ("lab", "montara-owner", "lab-fer", "", None):
            with self.subTest(instance=instance):
                with self.assertRaises(TenantRoutingDenied):
                    self.make(instance)

    def test_owner_cannot_select_another_tenant(self):
        for instance, owner in (
            ("jmlab", "owner-fer"),
            ("fertrial", "owner-main"),
            ("main", "owner-jm"),
        ):
            with self.subTest(instance=instance, owner=owner):
                with self.assertRaises(TenantRoutingDenied):
                    self.make(instance, owner)

    def test_missing_or_invalid_owner_denied(self):
        for owner in ("", None, "owner/../main", "not-registered"):
            with self.subTest(owner=owner):
                with self.assertRaises(TenantRoutingDenied):
                    self.make(owner=owner)

    def test_client_supplied_registry_not_implicit(self):
        with self.assertRaises(TenantRoutingDenied):
            self.make(owner_tenants={})
        with self.assertRaises(TenantRoutingDenied):
            self.make(owner_tenants={"owner-jm": "pilot-t4t"})

    def test_invalid_project_or_asset_paths_denied(self):
        for bad in ("../x", "/private/root", "UPPER", str(uuid4()).upper()):
            for key in ("project_id", "asset_id"):
                with self.subTest(bad=bad, key=key):
                    with self.assertRaises(TenantRoutingDenied):
                        self.make(**{key: bad})

    def test_media_classes_and_extensions_enforced(self):
        for asset_class, extension in (
            ("../../external", "mp4"), ("originals", "../mp4"),
            ("originals", "MP4"), ("originals", "mp4/../"),
        ):
            with self.subTest(asset_class=asset_class, extension=extension):
                with self.assertRaises(TenantRoutingDenied):
                    self.make(asset_class=asset_class, extension=extension)
        self.assertIn("project-state/", self.make(asset_class="project-state",
                                                extension="json").key)

    def test_cloud_only_fails_closed(self):
        require_cloud_only("r2_eu")
        for mode in ("local", "vm", "r2_default", "", None):
            with self.subTest(mode=mode):
                with self.assertRaises(TenantRoutingDenied):
                    self.make(persistence_mode=mode)

    def test_no_external_override_or_user_filename_in_key(self):
        p = self.make(extension="mov")
        self.assertEqual(R2_BUCKET, p.bucket)
        self.assertEqual(R2_ENDPOINT, p.endpoint)
        self.assertNotIn("owner-jm", p.key)
        self.assertNotIn("tmp", p.key)


if __name__ == "__main__":
    unittest.main()
