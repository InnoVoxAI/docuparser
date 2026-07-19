import asyncio
import structlog

from pyzeebe import ZeebeWorker, create_insecure_channel

from config import settings
from workers.document import register_document, get_document, archive_document
from workers.ocr import process_ocr, reprocess_ocr
from workers.layout import classify_layout
from workers.extraction import extract_fields
from workers.validation import validate_document
from workers.notification import notify_user
from workers.observability import log_failure
from workers.preprocessing import preprocess_image
from workers.reprocessing import reset_for_reprocessing

log = structlog.get_logger()


async def main() -> None:
    log.info("camunda_workers_starting", zeebe_address=settings.zeebe_address)

    channel = create_insecure_channel(grpc_address=settings.zeebe_address)

    worker = ZeebeWorker(channel)

    worker.include_router(register_document)
    worker.include_router(get_document)
    worker.include_router(archive_document)
    worker.include_router(process_ocr)
    worker.include_router(reprocess_ocr)
    worker.include_router(classify_layout)
    worker.include_router(extract_fields)
    worker.include_router(validate_document)
    worker.include_router(notify_user)
    worker.include_router(log_failure)
    worker.include_router(preprocess_image)
    worker.include_router(reset_for_reprocessing)

    log.info("camunda_workers_ready")

    await worker.work()


if __name__ == "__main__":
    asyncio.run(main())
