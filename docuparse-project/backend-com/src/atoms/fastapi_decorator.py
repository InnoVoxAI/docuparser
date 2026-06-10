# List to hold daemon task functions
daemon_tasks = []


def daemon(func):
    """
    Decorator to register a function as a daemon task for FastAPI lifespan.

    The decorated function will be added to the daemon_tasks list,
    which can be used in the FastAPI lifespan context manager to start
    background tasks.

    Example usage:
        @daemon
        async def my_daemon():
            while True:
                # do something
                await asyncio.sleep(60)

        Then in lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            tasks = [asyncio.create_task(task()) for task in daemon_tasks]
            yield
            for task in tasks:
                task.cancel()
    """
    daemon_tasks.append(func)
    return func


def create_lifespan_with_daemons():
    """
    Helper function to create a FastAPI lifespan context manager that
    starts all registered daemon tasks.

    Returns an asynccontextmanager that can be used as the lifespan for FastAPI.

    Example:
        from atoms.fastapi_decorator import create_lifespan_with_daemons

        app = FastAPI(lifespan=create_lifespan_with_daemons())
    """
    from contextlib import asynccontextmanager
    import asyncio
    from fastapi import FastAPI

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = [asyncio.create_task(task()) for task in daemon_tasks]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    return lifespan
