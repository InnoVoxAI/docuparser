from __future__ import annotations

import argparse
import json

from backend_com.services.imap_polling import poll_configured_imap_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll configured IMAP inbox once and ingest accepted attachments.")
    parser.add_argument("--tenant", default="tenant-demo")
    args = parser.parse_args()

    result = poll_configured_imap_once(tenant_id=args.tenant)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
