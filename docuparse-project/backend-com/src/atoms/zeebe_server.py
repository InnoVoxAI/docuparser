from atoms.email_reader import camunda_email_fetch_unread
from atoms.zeebe_decorator import ZeebeWorker

if __name__ == "__main__":
    worker = ZeebeWorker(
        hostname="localhost",
        port=26500,
        worker_id="readerserver",
    )

    worker.subscribe(camunda_email_fetch_unread)

    worker.start()
