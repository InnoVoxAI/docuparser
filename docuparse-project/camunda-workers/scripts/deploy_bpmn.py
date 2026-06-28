#!/usr/bin/env python3
"""Deploy BPMN resources to Zeebe.

Usage (inside container):
    python scripts/deploy_bpmn.py

Usage (local, requires pyzeebe installed):
    ZEEBE_ADDRESS=localhost:26500 python scripts/deploy_bpmn.py
"""
import asyncio
import os
import pathlib
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pyzeebe import ZeebeClient, create_insecure_channel  # noqa: E402

ZEEBE_ADDRESS = os.getenv("ZEEBE_ADDRESS", "localhost:26500")
BPMN_DIR = pathlib.Path(__file__).parent.parent / "bpmn"


async def deploy() -> None:
    print(f"Connecting to Zeebe at {ZEEBE_ADDRESS}")
    channel = create_insecure_channel(grpc_address=ZEEBE_ADDRESS)
    client = ZeebeClient(channel)

    bpmn_files = list(BPMN_DIR.glob("*.bpmn"))
    if not bpmn_files:
        print(f"No .bpmn files found in {BPMN_DIR}")
        return

    for bpmn_file in bpmn_files:
        print(f"Deploying {bpmn_file.name} ...")
        try:
            result = await client.deploy_resource(str(bpmn_file))
            print(f"  OK — key: {result.key}")
            for d in result.deployments:
                print(f"     process id : {d.bpmn_process_id}")
                print(f"     version    : {d.version}")
                print(f"     definition : {d.process_definition_key}")
        except Exception as exc:
            import traceback
            print(f"  FAILED ({type(exc).__name__}): {exc}")
            traceback.print_exc()

    await channel.close()


if __name__ == "__main__":
    asyncio.run(deploy())
