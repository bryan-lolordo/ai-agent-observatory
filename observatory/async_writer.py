# observatory/async_writer.py
"""
Async Write Queue for non-blocking database operations.

Provides background thread processing for Observatory database writes,
ensuring that tracking calls don't block the main application.

Features:
- Background daemon thread for database writes
- Batching for efficiency (configurable batch size/interval)
- Queue overflow protection with configurable limits
- Graceful shutdown with atexit flush
- Fallback to synchronous writes if disabled

Configuration via environment variables:
- ASYNC_WRITER_ENABLED: Enable async writes (default: true)
- ASYNC_WRITER_BATCH_SIZE: Items per batch (default: 10)
- ASYNC_WRITER_FLUSH_INTERVAL: Seconds between flushes (default: 1.0)
- ASYNC_WRITER_MAX_QUEUE_SIZE: Max pending items (default: 1000)

Usage:
    from observatory.async_writer import AsyncWriteQueue

    async_writer = AsyncWriteQueue(storage=storage)
    async_writer.start()

    # Non-blocking - returns immediately
    async_writer.enqueue_llm_call(llm_call)
    async_writer.enqueue_session(session)

    # On shutdown
    async_writer.shutdown(wait=True)
"""

import os
import time
import queue
import atexit
import logging
import threading
from typing import Callable, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class WriteOperation(Enum):
    """Types of write operations."""
    SAVE_SESSION = "save_session"
    SAVE_LLM_CALL = "save_llm_call"
    UPDATE_SESSION = "update_session"


@dataclass
class WriteTask:
    """A single write task for the queue."""
    operation: WriteOperation
    data: Any
    timestamp: float
    retry_count: int = 0


class AsyncWriteQueue:
    """
    Non-blocking write queue with background thread processing.

    Queues database write operations and processes them in a background
    thread, allowing the main application to continue without waiting
    for database I/O.

    Usage:
        storage = Storage()
        async_writer = AsyncWriteQueue(storage=storage)
        async_writer.start()

        # These return immediately
        async_writer.enqueue_llm_call(llm_call)
        async_writer.enqueue_session(session)

        # Shutdown with flush
        async_writer.shutdown(wait=True)
    """

    def __init__(
        self,
        storage,  # Storage instance
        batch_size: int = None,
        flush_interval: float = None,
        max_queue_size: int = None,
        enabled: bool = None,
        on_error: Optional[Callable[[Exception, WriteTask], None]] = None,
        max_retries: int = 3,
    ):
        """
        Initialize the async write queue.

        Args:
            storage: Storage instance for database operations
            batch_size: Items to process per batch (default: 10)
            flush_interval: Seconds between batch flushes (default: 1.0)
            max_queue_size: Maximum pending items before dropping (default: 1000)
            enabled: Enable async writes (default: true from env)
            on_error: Callback for error handling (receives exception and task)
            max_retries: Maximum retry attempts for failed writes (default: 3)
        """
        self.storage = storage
        self.batch_size = batch_size or int(os.getenv("ASYNC_WRITER_BATCH_SIZE", "10"))
        self.flush_interval = flush_interval or float(os.getenv("ASYNC_WRITER_FLUSH_INTERVAL", "1.0"))
        self.max_queue_size = max_queue_size or int(os.getenv("ASYNC_WRITER_MAX_QUEUE_SIZE", "1000"))
        self.max_retries = max_retries

        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = os.getenv("ASYNC_WRITER_ENABLED", "true").lower() == "true"

        self.on_error = on_error or self._default_error_handler

        self._queue: queue.Queue = queue.Queue(maxsize=self.max_queue_size)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started = False
        self._shutdown_complete = threading.Event()

        # Statistics
        self._stats = {
            "total_enqueued": 0,
            "total_processed": 0,
            "total_errors": 0,
            "total_dropped": 0,
            "total_retries": 0,
            "batches_processed": 0,
        }
        self._stats_lock = threading.Lock()

        # Register shutdown hook
        atexit.register(self._atexit_handler)

    def _default_error_handler(self, error: Exception, task: WriteTask) -> None:
        """Default error handler - log and continue."""
        logger.error(
            f"AsyncWriteQueue error on {task.operation.value}: {error}",
            exc_info=True
        )

    def start(self) -> None:
        """Start the background writer thread."""
        if not self.enabled:
            logger.info("AsyncWriteQueue disabled - writes will be synchronous")
            return

        if self._started:
            return

        self._stop_event.clear()
        self._shutdown_complete.clear()

        self._thread = threading.Thread(
            target=self._worker_loop,
            name="observatory-async-writer",
            daemon=True,
        )
        self._thread.start()
        self._started = True

        logger.info(
            f"AsyncWriteQueue started (batch_size={self.batch_size}, "
            f"flush_interval={self.flush_interval}s, max_queue={self.max_queue_size})"
        )

    def stop(self, wait: bool = True, timeout: float = 10.0) -> None:
        """
        Stop the background writer thread.

        Args:
            wait: Wait for queue to flush before returning
            timeout: Maximum seconds to wait for shutdown
        """
        if not self._started:
            return

        logger.info("AsyncWriteQueue stopping...")
        self._stop_event.set()

        if wait and self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(
                    f"AsyncWriteQueue did not stop within {timeout}s timeout "
                    f"({self._queue.qsize()} items may be lost)"
                )

        self._started = False
        self._shutdown_complete.set()
        logger.info("AsyncWriteQueue stopped")

    def shutdown(self, wait: bool = True, timeout: float = 10.0) -> None:
        """Alias for stop() - flush queue and shutdown."""
        self.stop(wait=wait, timeout=timeout)

    def _atexit_handler(self) -> None:
        """Flush queue on process exit."""
        if self._started and not self._shutdown_complete.is_set():
            logger.info("AsyncWriteQueue: flushing on exit...")
            self.stop(wait=True, timeout=5.0)

    def enqueue(self, operation: WriteOperation, data: Any) -> bool:
        """
        Enqueue a write task.

        If async writing is disabled, performs synchronous write immediately.

        Args:
            operation: Type of write operation
            data: Data to write (LLMCall, Session, etc.)

        Returns:
            True if enqueued successfully, False if queue is full
        """
        if not self.enabled:
            # Fallback to synchronous write
            self._execute_write(WriteTask(operation, data, time.time()))
            return True

        task = WriteTask(operation=operation, data=data, timestamp=time.time())

        try:
            self._queue.put_nowait(task)
            with self._stats_lock:
                self._stats["total_enqueued"] += 1
            return True
        except queue.Full:
            with self._stats_lock:
                self._stats["total_dropped"] += 1
            logger.warning(
                f"AsyncWriteQueue full ({self.max_queue_size}), "
                f"dropping {operation.value}"
            )
            return False

    def enqueue_llm_call(self, llm_call) -> bool:
        """
        Enqueue an LLM call for async saving.

        Args:
            llm_call: LLMCall object to save

        Returns:
            True if enqueued, False if dropped
        """
        return self.enqueue(WriteOperation.SAVE_LLM_CALL, llm_call)

    def enqueue_session(self, session) -> bool:
        """
        Enqueue a session for async saving.

        Args:
            session: Session object to save

        Returns:
            True if enqueued, False if dropped
        """
        return self.enqueue(WriteOperation.SAVE_SESSION, session)

    def enqueue_session_update(self, session) -> bool:
        """
        Enqueue a session update for async saving.

        Args:
            session: Session object to update

        Returns:
            True if enqueued, False if dropped
        """
        return self.enqueue(WriteOperation.UPDATE_SESSION, session)

    def _worker_loop(self) -> None:
        """Background worker loop - batches and writes."""
        while not self._stop_event.is_set():
            batch: List[WriteTask] = []

            # Collect batch with timeout
            deadline = time.time() + self.flush_interval

            while len(batch) < self.batch_size and time.time() < deadline:
                try:
                    remaining = max(0.01, deadline - time.time())
                    task = self._queue.get(timeout=remaining)
                    batch.append(task)
                except queue.Empty:
                    break

                if self._stop_event.is_set():
                    break

            # Process batch
            if batch:
                self._process_batch(batch)

        # Flush remaining items on shutdown
        self._flush_remaining()

    def _process_batch(self, batch: List[WriteTask]) -> None:
        """Process a batch of write tasks."""
        for task in batch:
            self._execute_write(task)

        with self._stats_lock:
            self._stats["batches_processed"] += 1

    def _execute_write(self, task: WriteTask) -> None:
        """Execute a single write task with retry logic."""
        try:
            if task.operation == WriteOperation.SAVE_LLM_CALL:
                self.storage.save_llm_call(task.data)
            elif task.operation == WriteOperation.SAVE_SESSION:
                self.storage.save_session(task.data)
            elif task.operation == WriteOperation.UPDATE_SESSION:
                self.storage.update_session(task.data)

            with self._stats_lock:
                self._stats["total_processed"] += 1

        except Exception as e:
            # Retry logic
            if task.retry_count < self.max_retries:
                task.retry_count += 1
                with self._stats_lock:
                    self._stats["total_retries"] += 1

                logger.warning(
                    f"AsyncWriteQueue retry {task.retry_count}/{self.max_retries} "
                    f"for {task.operation.value}: {e}"
                )

                # Re-queue for retry (best effort, don't block)
                try:
                    self._queue.put_nowait(task)
                except queue.Full:
                    self._handle_final_error(e, task)
            else:
                self._handle_final_error(e, task)

    def _handle_final_error(self, error: Exception, task: WriteTask) -> None:
        """Handle error after all retries exhausted."""
        with self._stats_lock:
            self._stats["total_errors"] += 1
        self.on_error(error, task)

    def _flush_remaining(self) -> None:
        """Flush any remaining items in queue on shutdown."""
        count = 0
        while not self._queue.empty():
            try:
                task = self._queue.get_nowait()
                self._execute_write(task)
                count += 1
            except queue.Empty:
                break

        if count > 0:
            logger.info(f"AsyncWriteQueue: flushed {count} remaining items")

    def get_stats(self) -> dict:
        """Get queue statistics."""
        with self._stats_lock:
            return {
                **self._stats,
                "queue_size": self._queue.qsize(),
                "max_queue_size": self.max_queue_size,
                "batch_size": self.batch_size,
                "flush_interval": self.flush_interval,
                "enabled": self.enabled,
                "running": self._started,
            }

    @property
    def queue_size(self) -> int:
        """Current number of items in queue."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if the writer thread is running."""
        return self._started

    def wait_for_empty(self, timeout: float = 30.0) -> bool:
        """
        Wait for queue to become empty.

        Useful for testing or ensuring all writes complete.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if queue is empty, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self._queue.empty():
                return True
            time.sleep(0.1)
        return False


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "WriteOperation",
    "WriteTask",
    "AsyncWriteQueue",
]
