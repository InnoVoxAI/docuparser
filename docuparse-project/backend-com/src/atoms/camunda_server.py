from atoms.camunda_decorator import CamundaWorker
from atoms.email_reader import camunda_email_fetch_unread

if __name__ == "__main__":
    worker = CamundaWorker(
        base_url="http://localhost:8080/engine-rest",
        worker_id="readerserver",
    )

    worker.subscribe(camunda_email_fetch_unread)

    worker.start()
