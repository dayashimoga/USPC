"""Validation test suite for K3s Kubernetes declarative manifests."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_k3s_manifests_syntax_and_schema():
    manifests_dir = Path("deploy/k3s")
    assert manifests_dir.exists(), "deploy/k3s directory must exist"

    manifest_files = list(manifests_dir.glob("*.yaml"))
    assert len(manifest_files) >= 7, (
        f"Expected at least 7 K3s manifests, found {len(manifest_files)}"
    )

    for f in manifest_files:
        content = f.read_text(encoding="utf-8")
        docs = list(yaml.safe_load_all(content))
        assert len(docs) > 0, f"Manifest {f.name} is empty"

        for doc in docs:
            if not doc:
                continue
            assert "apiVersion" in doc, f"Missing apiVersion in {f.name}"
            assert "kind" in doc, f"Missing kind in {f.name}"
            assert "metadata" in doc, f"Missing metadata in {f.name}"
            assert "name" in doc["metadata"], f"Missing metadata.name in {f.name}"

            # Validate namespace assignment on non-Namespace resources
            if doc["kind"] != "Namespace" and doc["kind"] != "Kustomization":
                assert doc["metadata"].get("namespace") == "uspc", (
                    f"Resource in {f.name} must be in namespace 'uspc'"
                )


def test_k3s_deployments_resource_limits():
    manifests_dir = Path("deploy/k3s")
    for f in manifests_dir.glob("*.yaml"):
        docs = list(yaml.safe_load_all(f.read_text(encoding="utf-8")))
        for doc in docs:
            if not doc or doc.get("kind") != "Deployment":
                continue
            spec = doc.get("spec", {})
            containers = spec.get("template", {}).get("spec", {}).get("containers", [])
            for c in containers:
                res = c.get("resources", {})
                assert "requests" in res, (
                    f"Deployment {doc['metadata']['name']} container {c['name']} missing resource requests"
                )
                assert "limits" in res, (
                    f"Deployment {doc['metadata']['name']} container {c['name']} missing resource limits"
                )
