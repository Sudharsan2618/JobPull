"""
Generic bounded thread pool — the single concurrency primitive for the whole
pipeline. I/O-bound blocking libraries (jobspy, firecrawl, requests) release the
GIL during network waits, so threads give real parallelism without asyncio.

A failing task never kills the batch: its exception is logged and skipped, so a
partial run still stores everything that succeeded.

on_result(item) runs in the CALLER's thread as each task finishes — use it for
thread-safe streaming writes (Mongo upserts) without locking.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional

ErrorHandler = Callable[[Any, BaseException], None]


def run_pool(
    tasks: List[Any],
    worker: Callable[[Any], Any],
    max_workers: int,
    on_result: Optional[Callable[[Any], None]] = None,
    on_error: Optional[ErrorHandler] = None,
    label: str = "pool",
) -> List[Any]:
    """
    Run worker(task) across tasks with at most max_workers in flight.

    worker may return a single item or a list of items; all are flattened into
    the returned list. Returns [] for an empty task list.
    """
    if not tasks:
        return []

    out: List[Any] = []
    max_workers = max(1, min(max_workers, len(tasks)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(worker, t): t for t in tasks}
        done = 0
        for fut in as_completed(futures):
            done += 1
            task = futures[fut]
            try:
                result = fut.result()
            except Exception as exc:
                print(f"[{label}] task failed ({task!r}): {type(exc).__name__}: {exc}")
                if on_error is not None:
                    try:
                        on_error(task, exc)
                    except Exception as callback_exc:
                        print(f"[{label}] on_error failed: {type(callback_exc).__name__}: {callback_exc}")
                continue
            if result is None:
                continue
            items = result if isinstance(result, list) else [result]
            for it in items:
                out.append(it)
                if on_result is not None:
                    try:
                        on_result(it)
                    except Exception as exc:
                        print(f"[{label}] on_result failed: {type(exc).__name__}: {exc}")
                        if on_error is not None:
                            try:
                                on_error(task, exc)
                            except Exception as callback_exc:
                                print(f"[{label}] on_error failed: {type(callback_exc).__name__}: {callback_exc}")
            print(f"[{label}] {done}/{len(futures)} done")
    return out
