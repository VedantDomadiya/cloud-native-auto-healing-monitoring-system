"""Kubernetes API client. Wired up in Session 2.

The Session 1 demo path runs entirely against Docker. These functions
exist so the dispatch table can reference them, but they raise
``RemediationError`` until the Kubernetes deployments land.
"""
from __future__ import annotations

import os
from typing import Any, Dict

# Defer kubernetes import so this module is cheap to load when running
# Docker-only tests.
_kube_api = None


def _api():
    global _kube_api
    if _kube_api is None:
        from kubernetes import client, config

        if os.environ.get("KUBE_IN_CLUSTER") == "1":
            config.load_incluster_config()
        else:
            config.load_kube_config(context=os.environ.get("KUBE_CONTEXT") or None)
        _kube_api = client
    return _kube_api


def delete_pod(service: str) -> Dict[str, Any]:
    """Delete a pod so the Deployment controller recreates it.

    Looks up pods by label ``app=<service>`` in the ``demo`` namespace.
    """
    from dispatch import RemediationError

    try:
        v1 = _api().CoreV1Api()
        pods = v1.list_namespaced_pod(
            namespace="demo", label_selector=f"app={service}"
        ).items
        if not pods:
            raise RemediationError(f"no pods found for service '{service}'")
        for p in pods:
            v1.delete_namespaced_pod(name=p.metadata.name, namespace="demo")
        return {"service": service, "deleted": [p.metadata.name for p in pods]}
    except Exception as exc:  # noqa: BLE001
        raise RemediationError(f"k8s delete_pod failed for {service}: {exc}") from exc


def scale_deployment(service: str, replicas_delta: int) -> Dict[str, Any]:
    from dispatch import RemediationError

    try:
        apps = _api().AppsV1Api()
        dep = apps.read_namespaced_deployment(name=service, namespace="demo")
        current = dep.spec.replicas or 1
        target = max(1, current + replicas_delta)
        dep.spec.replicas = target
        apps.patch_namespaced_deployment_scale(
            name=service,
            namespace="demo",
            body={"spec": {"replicas": target}},
        )
        return {"service": service, "previous_replicas": current, "new_replicas": target}
    except Exception as exc:  # noqa: BLE001
        raise RemediationError(f"k8s scale_deployment failed for {service}: {exc}") from exc


def capture_logs(service: str, lines: int = 100) -> Dict[str, Any]:
    from dispatch import RemediationError

    try:
        v1 = _api().CoreV1Api()
        pods = v1.list_namespaced_pod(
            namespace="demo", label_selector=f"app={service}"
        ).items
        if not pods:
            raise RemediationError(f"no pods found for service '{service}'")
        pod = pods[0]
        raw = v1.read_namespaced_pod_log(
            name=pod.metadata.name, namespace="demo", tail_lines=lines
        )
        return {"service": service, "pod": pod.metadata.name, "lines": raw.splitlines()}
    except Exception as exc:  # noqa: BLE001
        raise RemediationError(f"k8s capture_logs failed for {service}: {exc}") from exc
