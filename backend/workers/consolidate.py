"""
Consolidated worker plane integration for FastAPI lifespan.

Exposes the internal _start_plane() / _stop_plane() machinery from
WorkerHost so that the API process can spawn worker planes as asyncio
tasks alongside the HTTP server, without the signal-handler logic that
conflicts with uvicorn.

Usage (in main.py lifespan):
    from workers.consolidate import start_planes, stop_planes
    worker_hosts = await start_planes(["trading", "news", "discovery"])
    yield
    await stop_planes(worker_hosts)
"""
from __future__ import annotations

import asyncio

from workers.host import WorkerHost

logger = __import__("utils.logging").get_logger(__name__)

WORKER_PLANES = ["trading", "news", "discovery"]


async def start_planes(planes: list[str] | None = None) -> dict[str, WorkerHost]:
    """
    Start the named worker planes as asyncio tasks within the current event loop.

    Skips the signal-handler setup in WorkerHost.run() because uvicorn owns
    the signal handlers and will relay SIGTERM to the lifespan shutdown path.
    """
    if planes is None:
        planes = WORKER_PLANES

    hosts: dict[str, WorkerHost] = {}
    plane_tasks: dict[str, asyncio.Task] = {}

    for plane_name in planes:
        try:
            host = WorkerHost(plane_name)
            hosts[plane_name] = host
        except Exception:
            logger.exception("Failed to create WorkerHost for plane '%s'", plane_name)
            continue

        async def _plane_runner(h: WorkerHost, name: str) -> None:
            try:
                await h._start_plane()
                logger.info("Worker plane running", plane=name)
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("Worker plane cancelled", plane=name)
                raise
            except Exception:
                logger.exception("Worker plane runner crashed", plane=name)
                raise

        task = asyncio.create_task(_plane_runner(host, plane_name), name=f"worker-plane-{plane_name}")
        plane_tasks[plane_name] = task

    if plane_tasks:
        logger.info("Worker planes starting", planes=list(plane_tasks.keys()))

    return hosts


async def stop_planes(hosts: dict[str, WorkerHost]) -> None:
    """
    Gracefully shut down all worker planes started by start_planes().
    """
    logger.info("Stopping worker planes", planes=list(hosts.keys()))

    for plane_name, host in hosts.items():
        try:
            await host._stop_plane()
            logger.info("Worker plane stopped", plane=plane_name)
        except Exception:
            logger.exception("Error stopping worker plane '%s'", plane_name)

    logger.info("All worker planes stopped")
