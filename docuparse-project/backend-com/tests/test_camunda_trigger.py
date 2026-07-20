from __future__ import annotations

from backend_com.services import camunda_trigger


def _kwargs(**overrides):
    kwargs = dict(
        tenant_id="tenant-demo",
        document_id="doc-1",
        file_uri="s3://docuparse/documents/tenant-demo/doc-1/original",
        original_filename="fixture.pdf",
        content_type="application/pdf",
        size_bytes=123,
        sha256="abc",
        channel="manual",
        correlation_id="corr-1",
    )
    kwargs.update(overrides)
    return kwargs


def test_start_docuparse_pipeline_publishes_whatsapp_message(monkeypatch):
    captured: dict = {}

    class _FakeClient:
        def __init__(self, channel):
            captured["channel"] = channel

        async def publish_message(self, *, name, correlation_key, variables):
            captured["name"] = name
            captured["correlation_key"] = correlation_key
            captured["variables"] = variables

    class _FakeChannel:
        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(camunda_trigger, "create_insecure_channel", lambda grpc_address: _FakeChannel())
    monkeypatch.setattr(camunda_trigger, "ZeebeClient", _FakeClient)

    status = camunda_trigger.start_docuparse_pipeline(**_kwargs())

    assert status == "published"
    assert captured["name"] == "docuparse-file-received-whatsapp"
    assert captured["correlation_key"] == ""
    assert captured["closed"] is True
    assert captured["variables"] == {
        "documentId": "doc-1",
        "tenantId": "tenant-demo",
        "fileUri": "s3://docuparse/documents/tenant-demo/doc-1/original",
        "originalFilename": "fixture.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 123,
        "sha256": "abc",
        "channel": "manual",
        "correlationId": "corr-1",
    }


def test_start_docuparse_pipeline_returns_failed_when_broker_unreachable(monkeypatch):
    class _FailingClient:
        def __init__(self, channel):
            pass

        async def publish_message(self, *, name, correlation_key, variables):
            raise ConnectionError("zeebe broker unreachable")

    class _FakeChannel:
        async def close(self):
            pass

    monkeypatch.setattr(camunda_trigger, "create_insecure_channel", lambda grpc_address: _FakeChannel())
    monkeypatch.setattr(camunda_trigger, "ZeebeClient", _FailingClient)

    status = camunda_trigger.start_docuparse_pipeline(**_kwargs())

    assert status == "failed"
