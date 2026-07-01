import asyncio
import structlog

from pyzeebe import ZeebeWorker, create_insecure_channel

from config import settings
from workers.document import register_document, get_document, delete_document
from workers.ocr import process_ocr, reprocess_ocr
from workers.layout import classify_layout
from workers.extraction import extract_fields
from workers.validation import validate_document
from workers.erp import export_erp

log = structlog.get_logger()


async def main() -> None:
    log.info("camunda_workers_starting", zeebe_address=settings.zeebe_address)

    channel = create_insecure_channel(grpc_address=settings.zeebe_address)

    worker = ZeebeWorker(channel)

    worker.include_router(register_document)
    worker.include_router(get_document)
    worker.include_router(delete_document)
    worker.include_router(process_ocr)
    worker.include_router(reprocess_ocr)
    worker.include_router(classify_layout)
    worker.include_router(extract_fields)
    worker.include_router(validate_document)
    worker.include_router(export_erp)

    log.info("camunda_workers_ready")

    await worker.work()


if __name__ == "__main__":
    asyncio.run(main())
