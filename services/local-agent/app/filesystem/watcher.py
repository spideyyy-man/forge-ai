"""File watcher using Watchdog."""
import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches for filesystem changes in approved workspaces."""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self._observers = []

    def start(self, paths: list[str]):
        """Start watching paths."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class ChangeHandler(FileSystemEventHandler):
                def __init__(self, cb):
                    self.cb = cb

                def on_modified(self, event):
                    if not event.is_directory and self.cb:
                        self.cb({"type": "modified", "path": event.src_path})

                def on_created(self, event):
                    if self.cb:
                        self.cb({"type": "created", "path": event.src_path})

                def on_deleted(self, event):
                    if self.cb:
                        self.cb({"type": "deleted", "path": event.src_path})

            for path in paths:
                if Path(path).exists():
                    observer = Observer()
                    observer.schedule(ChangeHandler(self.callback), path, recursive=True)
                    observer.start()
                    self._observers.append(observer)
                    logger.info(f"Watching: {path}")
        except ImportError:
            logger.warning("Watchdog not installed - file watching disabled")

    def stop(self):
        """Stop all watchers."""
        for observer in self._observers:
            observer.stop()
            observer.join()
        self._observers.clear()
