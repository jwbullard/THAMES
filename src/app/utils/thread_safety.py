"""Thread-safety guards for GTK widget access.

GTK is not thread-safe on Windows. Touching the widget tree from a
background thread silently corrupts the heap; on a GUI process the
heap manager later detects the corruption and terminates the process
with STATUS_HEAP_CORRUPTION (0xC0000374) and no exception. The crash
can land arbitrarily far from the bad call site, so direct debugging
is impractical.

Use `assert_main_thread()` at the top of any method that mutates GTK
widgets. A background-thread caller will fail loudly with a clean
Python traceback at the bad call site instead of silently corrupting
the heap.
"""

import threading


def assert_main_thread() -> None:
    """Raise if the current thread is not the main thread.

    GTK widget mutation must happen on the main thread. Background
    threads must marshal via `GLib.idle_add(callable, *args)`.
    """
    current = threading.current_thread()
    if current is not threading.main_thread():
        raise RuntimeError(
            f"GTK widget method called from background thread "
            f"'{current.name}'. Use GLib.idle_add to marshal the call "
            f"onto the main thread."
        )
