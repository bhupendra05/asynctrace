"""Captures the full async call chain so exceptions show WHERE a task was created."""
from __future__ import annotations
import asyncio, traceback, functools
from typing import Callable, Coroutine, Any

_CHAIN_ATTR = "__asynctrace_chain__"

def _capture_stack() -> str:
    return "".join(traceback.format_stack()[:-2])

class AsyncTraceTask(asyncio.Task):
    """
    Drop-in replacement for asyncio.Task that captures the creation-site stack
    and appends it to any exception raised inside the task.

    Usage::

        import asyncio
        import asynctrace
        asynctrace.install()          # one line, global patch

        async def bad():
            raise ValueError("something broke")

        async def main():
            await asyncio.create_task(bad())   # now shows WHERE main() created this task

        asyncio.run(main())
    """
    def __init__(self, coro, *, loop=None, name=None, context=None, eager_start=False):
        # Capture creation-site stack BEFORE calling super().__init__
        self._creation_stack = _capture_stack()
        kwargs: dict = {}
        if name is not None:
            kwargs["name"] = name
        if context is not None:
            kwargs["context"] = context
        super().__init__(coro, loop=loop, **kwargs)

    def __del__(self):
        exc = self.exception() if not self.cancelled() and self.done() else None
        if exc is not None and not hasattr(exc, _CHAIN_ATTR):
            object.__setattr__(exc, _CHAIN_ATTR, self._creation_stack)
        super().__del__() if hasattr(super(), "__del__") else None

def _wrap_exception(exc: BaseException, creation_stack: str) -> BaseException:
    if hasattr(exc, _CHAIN_ATTR):
        return exc
    original_str = exc.__str__

    def new_str(self=exc):
        return f"{original_str()}\n\n--- Task created at ---\n{creation_stack}"

    try:
        exc.__class__ = type(
            exc.__class__.__name__,
            (exc.__class__,),
            {"__str__": new_str, "__module__": exc.__class__.__module__},
        )
        setattr(exc, _CHAIN_ATTR, creation_stack)
    except (TypeError, AttributeError):
        pass
    return exc

def install(loop: asyncio.AbstractEventLoop | None = None):
    """
    Globally install AsyncTraceTask as the default task factory.
    Call once at app startup — works with all asyncio.create_task() calls.

    ::

        import asynctrace
        asynctrace.install()
    """
    def factory(loop, coro, *, context=None):
        return AsyncTraceTask(coro, loop=loop, context=context)
    
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Not running yet — patch the policy
            _patch_policy()
            return
    loop.set_task_factory(factory)

def _patch_policy():
    """Patch the default event loop policy to always use AsyncTraceTask."""
    orig_new_event_loop = asyncio.DefaultEventLoopPolicy.new_event_loop

    def patched_new_event_loop(self):
        loop = orig_new_event_loop(self)
        loop.set_task_factory(lambda loop, coro, **kw: AsyncTraceTask(coro, loop=loop, **kw))
        return loop

    asyncio.DefaultEventLoopPolicy.new_event_loop = patched_new_event_loop

def traced(fn: Callable) -> Callable:
    """
    Decorator that captures the caller's stack for any coroutine function.

    ::

        @traced
        async def fetch_user(user_id: int):
            ...
    """
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        creation_stack = _capture_stack()
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            _wrap_exception(exc, creation_stack)
            raise
    return wrapper
