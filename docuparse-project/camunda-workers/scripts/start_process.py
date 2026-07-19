#!/usr/bin/env python3
"""Start a DocuParse Camunda process instance from the command line.

docuparse-pipeline (feature 014) has only message start events (one per intake
channel) — it has no "none" start event, so it cannot be started via
CreateProcessInstance. This script publishes the channel's start message
instead; Zeebe creates a new process instance for each published message.

Usage (after uploading a document via existing flow):

    python scripts/start_process.py \\
        --document-id <uuid> \\
        --tenant-id default \\
        --channel email \\
        --file-uri documents/default/<uuid>/original/<filename>

Or with explicit Zeebe address:

    ZEEBE_ADDRESS=localhost:26500 python scripts/start_process.py ...
"""
import argparse
import asyncio
import os
import sys

# Allow running from project root or scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pyzeebe import ZeebeClient, create_insecure_channel  # noqa: E402

CHANNEL_MESSAGE_NAMES = {
    "email": "docuparse-file-received-email",
    "whatsapp": "docuparse-file-received-whatsapp",
}


async def start(
    document_id: str,
    tenant_id: str,
    file_uri: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
    channel: str,
    correlation_id: str,
    zeebe_address: str,
) -> None:
    message_name = CHANNEL_MESSAGE_NAMES[channel]

    grpc_channel = create_insecure_channel(grpc_address=zeebe_address)
    client = ZeebeClient(grpc_channel)

    variables = {
        "documentId": document_id,
        "tenantId": tenant_id,
        "fileUri": file_uri,
        "originalFilename": original_filename,
        "contentType": content_type,
        "sizeBytes": size_bytes,
        "sha256": sha256,
        "channel": channel,
        "correlationId": correlation_id or document_id,
    }

    print(f"Publishing message '{message_name}' with variables:")
    for k, v in variables.items():
        print(f"  {k}: {v}")

    # No process-instance correlation needed for these start events (each
    # message starts a fresh instance), so correlation_key is left empty.
    response = await client.publish_message(
        name=message_name,
        correlation_key="",
        variables=variables,
    )

    print(f"\nMessage published: {response}")
    await grpc_channel.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start a DocuParse Camunda process")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--file-uri", default="")
    parser.add_argument("--original-filename", default="document")
    parser.add_argument("--content-type", default="application/pdf")
    parser.add_argument("--size-bytes", type=int, default=0)
    parser.add_argument("--sha256", default="")
    parser.add_argument("--channel", choices=sorted(CHANNEL_MESSAGE_NAMES), default="email")
    parser.add_argument("--correlation-id", default="")
    parser.add_argument(
        "--zeebe-address",
        default=os.getenv("ZEEBE_ADDRESS", "localhost:26500"),
    )
    args = parser.parse_args()

    asyncio.run(
        start(
            document_id=args.document_id,
            tenant_id=args.tenant_id,
            file_uri=args.file_uri,
            original_filename=args.original_filename,
            content_type=args.content_type,
            size_bytes=args.size_bytes,
            sha256=args.sha256,
            channel=args.channel,
            correlation_id=args.correlation_id,
            zeebe_address=args.zeebe_address,
        )
    )


if __name__ == "__main__":
    main()
