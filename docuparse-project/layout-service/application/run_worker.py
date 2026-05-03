from __future__ import annotations

import argparse

from application.layout_event_worker import worker_from_env


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DocuParse layout event worker.")
    parser.add_argument("--once", action="store_true", help="Process available events once and exit.")
    args = parser.parse_args()

    worker = worker_from_env()
    if args.once:
        processed_count = worker.run_once()
        print(f"Processed {processed_count} event(s).")
        return
    worker.run_forever()


if __name__ == "__main__":
    main()
