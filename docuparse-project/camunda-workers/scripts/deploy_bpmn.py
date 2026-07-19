#!/usr/bin/env python3
"""Deploy BPMN + Camunda Form resources to Zeebe.

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
from pyzeebe.grpc_internals.zeebe_process_adapter import DeployResourceResponse  # noqa: E402

ZEEBE_ADDRESS = os.getenv("ZEEBE_ADDRESS", "localhost:26500")
BPMN_DIR = pathlib.Path(__file__).parent.parent / "bpmn"


async def deploy() -> None:
    print(f"Connecting to Zeebe at {ZEEBE_ADDRESS}")
    channel = create_insecure_channel(grpc_address=ZEEBE_ADDRESS)
    client = ZeebeClient(channel)

    # Bundled into one deployment call (not one per file): a process' userTasks
    # reference forms by formId, and bundling — same as Camunda Modeler's own
    # "Deploy" action — is what guarantees the BPMN and the forms it references
    # land in the same deployment.
    bpmn_files = sorted(BPMN_DIR.glob("*.bpmn"))
    form_files = sorted(BPMN_DIR.glob("*.form"))
    resource_files = bpmn_files + form_files
    if not resource_files:
        print(f"No .bpmn/.form files found in {BPMN_DIR}")
        return

    print(f"Deploying {len(resource_files)} resource(s): {[f.name for f in resource_files]}")
    try:
        result = await client.deploy_resource(*(str(f) for f in resource_files))
        print(f"  OK — key: {result.key}")
        for d in result.deployments:
            if isinstance(d, DeployResourceResponse.ProcessMetadata):
                print(f"     process    : {d.bpmn_process_id} v{d.version} (key={d.process_definition_key})")
            elif isinstance(d, DeployResourceResponse.FormMetadata):
                print(f"     form       : {d.form_id} v{d.version} (key={d.form_key})")
            else:
                print(f"     resource   : {d}")
    except Exception as exc:
        import traceback
        print(f"  FAILED ({type(exc).__name__}): {exc}")
        traceback.print_exc()

    await channel.close()


if __name__ == "__main__":
    asyncio.run(deploy())
