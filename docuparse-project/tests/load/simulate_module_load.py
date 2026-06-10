from __future__ import annotations

import argparse
import base64
import json
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

PROJECT_DIR = Path(__file__).resolve().parents[2]
for path in (
    PROJECT_DIR / "backend-com" / "src",
    PROJECT_DIR / "backend-core",
    PROJECT_DIR / "contracts",
    PROJECT_DIR / "shared",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from backend_com import config as backend_com_config
from backend_com.services import document_ingest
from backend_com.services.email_capture import process_email_attachments
from backend_com.services.manual_upload import process_manual_upload
from backend_com.services.whatsapp_capture import process_whatsapp_media
from docuparse_events import LocalJsonlEventBus
from documents.services.erp_mock import handle_erp_integration_requested_event
from events import (
    ERPIntegrationRequestedEvent,
    ExtractionCompletedEvent,
    LayoutClassifiedEvent,
    OCRCompletedEvent,
)


Scenario = Callable[[int], None]


def main() -> int:
    parser = argparse.ArgumentParser(description="DocuParse local load simulator")
    parser.add_argument("--scenario", default="all", choices=[*SCENARIOS, "all"])
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    selected = SCENARIOS if args.scenario == "all" else {args.scenario: SCENARIOS[args.scenario]}
    report = {}
    for name, factory in selected.items():
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            storage_dir = root / "objects"
            event_dir = root / "events"
            _point_backend_com_to_tmp(storage_dir, event_dir)
            bus = LocalJsonlEventBus(event_dir)
            report[name] = run_scenario(
                name=name,
                scenario=factory(bus),
                iterations=args.iterations,
                concurrency=args.concurrency,
                event_dir=event_dir,
            )

    output = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


def run_scenario(
    *,
    name: str,
    scenario: Scenario,
    iterations: int,
    concurrency: int,
    event_dir: Path,
) -> dict:
    started = time.perf_counter()
    latencies_ms: list[float] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_timed_call, scenario, index) for index in range(iterations)]
        for future in as_completed(futures):
            latency_ms, error = future.result()
            latencies_ms.append(latency_ms)
            if error:
                errors.append(error)

    elapsed_seconds = max(time.perf_counter() - started, 0.000001)
    successful = iterations - len(errors)
    return {
        "scenario": name,
        "iterations": iterations,
        "successful": successful,
        "errors": len(errors),
        "sample_errors": errors[:5],
        "throughput_per_second": round(successful / elapsed_seconds, 2),
        "p95_ms": round(_percentile(latencies_ms, 95), 2),
        "p50_ms": round(statistics.median(latencies_ms), 2) if latencies_ms else 0.0,
        "backlog": _event_counts(event_dir),
    }


def _timed_call(scenario: Scenario, index: int) -> tuple[float, str | None]:
    started = time.perf_counter()
    try:
        scenario(index)
        return (time.perf_counter() - started) * 1000, None
    except Exception as exc:
        return (time.perf_counter() - started) * 1000, str(exc)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percentile / 100) * (len(ordered) - 1)))
    return ordered[index]


def _event_counts(event_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(event_dir.glob("*.jsonl")):
        counts[path.stem] = len(path.read_text(encoding="utf-8").splitlines())
    return counts


def _point_backend_com_to_tmp(storage_dir: Path, event_dir: Path) -> None:
    backend_com_config.settings.local_storage_dir = storage_dir
    backend_com_config.settings.local_event_dir = event_dir
    backend_com_config.settings.email_webhook_token = ""
    backend_com_config.settings.whatsapp_webhook_token = ""
    backend_com_config.settings.internal_service_token = ""
    document_ingest.settings.local_storage_dir = storage_dir
    document_ingest.settings.local_event_dir = event_dir
    document_ingest.settings.email_webhook_token = ""
    document_ingest.settings.whatsapp_webhook_token = ""


def manual_upload_scenario(_: LocalJsonlEventBus) -> Scenario:
    def run(index: int) -> None:
        process_manual_upload(
            tenant_id="tenant-demo",
            filename=f"manual-{index}.pdf",
            content_type="application/pdf",
            content=b"%PDF load manual",
            sender="load@example.test",
        )

    return run


def email_capture_scenario(_: LocalJsonlEventBus) -> Scenario:
    def run(index: int) -> None:
        process_email_attachments(
            tenant_id="tenant-demo",
            sender="sender@example.test",
            message_id=f"msg-{index}",
            subject="Carga",
            provider="webhook",
            attachments=[
                {
                    "filename": f"email-{index}.pdf",
                    "content_type": "application/pdf",
                    "content": b"%PDF load email",
                }
            ],
        )

    return run


def whatsapp_capture_scenario(_: LocalJsonlEventBus) -> Scenario:
    encoded = base64.b64encode(b"%PDF load whatsapp").decode("ascii")

    def run(index: int) -> None:
        process_whatsapp_media(
            tenant_id="tenant-demo",
            sender="whatsapp:+5511999999999",
            message_sid=f"SM{index}",
            body="carga",
            media_items=[
                {
                    "filename": f"whatsapp-{index}.pdf",
                    "content_type": "application/pdf",
                    "content_base64": encoded,
                }
            ],
        )

    return run


def ocr_mock_scenario(bus: LocalJsonlEventBus) -> Scenario:
    def run(_: int) -> None:
        event = OCRCompletedEvent(
            tenant_id="tenant-demo",
            document_id=uuid4(),
            correlation_id=uuid4(),
            source="load-test",
            data={
                "raw_text_uri": "local://mock/raw_text.json",
                "raw_text_preview": "valor R$ 123,45",
                "document_type": "digital_pdf",
                "engine_used": "mock",
                "confidence": 0.9,
                "processing_time_seconds": 0.01,
            },
        ).model_dump(mode="json")
        bus.publish("ocr.completed", event)

    return run


def layout_mock_scenario(bus: LocalJsonlEventBus) -> Scenario:
    def run(_: int) -> None:
        event = LayoutClassifiedEvent(
            tenant_id="tenant-demo",
            document_id=uuid4(),
            correlation_id=uuid4(),
            source="load-test",
            data={
                "layout": "boleto_bb",
                "confidence": 0.9,
                "document_type": "digital_pdf",
                "requires_human_validation": False,
            },
        ).model_dump(mode="json")
        bus.publish("layout.classified", event)

    return run


def langextract_mock_scenario(bus: LocalJsonlEventBus) -> Scenario:
    def run(_: int) -> None:
        event = ExtractionCompletedEvent(
            tenant_id="tenant-demo",
            document_id=uuid4(),
            correlation_id=uuid4(),
            source="load-test",
            occurred_at=datetime.now(timezone.utc),
            data={
                "schema_id": "boleto",
                "schema_version": "v1",
                "fields": {"valor": "R$ 123,45"},
                "confidence": 0.9,
                "requires_human_validation": True,
            },
        ).model_dump(mode="json")
        bus.publish("extraction.completed", event)

    return run


def erp_mock_scenario(bus: LocalJsonlEventBus) -> Scenario:
    def run(_: int) -> None:
        event = ERPIntegrationRequestedEvent(
            tenant_id="tenant-demo",
            document_id=uuid4(),
            correlation_id=uuid4(),
            source="load-test",
            data={
                "connector": "mock",
                "payload": {"fields": {"valor": "R$ 123,45"}},
                "idempotency_key": str(uuid4()),
            },
        ).model_dump(mode="json")
        handle_erp_integration_requested_event(event, bus)

    return run


SCENARIOS: dict[str, Callable[[LocalJsonlEventBus], Scenario]] = {
    "manual_upload": manual_upload_scenario,
    "email_capture": email_capture_scenario,
    "whatsapp_capture": whatsapp_capture_scenario,
    "ocr_mock": ocr_mock_scenario,
    "layout_mock": layout_mock_scenario,
    "langextract_mock": langextract_mock_scenario,
    "erp_mock": erp_mock_scenario,
}


if __name__ == "__main__":
    raise SystemExit(main())
