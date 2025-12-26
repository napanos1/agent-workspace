"""
Observability Module - Centralized event tracking and monitoring for agent workflows.

This module provides a unified interface for:
- Event logging and tracking
- Metrics collection
- Audit trail generation
- Multi-channel notifications (Slack, file, console)

Integrates with the 3-layer architecture to provide visibility into:
- Directive execution
- Script lifecycle
- Self-annealing events
- System health
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from pathlib import Path
from contextlib import contextmanager
import threading

from slack_notifier import (
    SlackNotifier,
    AgentObserver,
    NotificationLevel,
    notify,
    notify_error,
    notify_success
)


class EventType(Enum):
    """Types of observable events in the agent workflow."""
    DIRECTIVE_STARTED = "directive_started"
    DIRECTIVE_COMPLETED = "directive_completed"
    DIRECTIVE_FAILED = "directive_failed"
    DIRECTIVE_UPDATED = "directive_updated"

    SCRIPT_STARTED = "script_started"
    SCRIPT_COMPLETED = "script_completed"
    SCRIPT_FAILED = "script_failed"

    TASK_PROGRESS = "task_progress"
    TASK_CHECKPOINT = "task_checkpoint"

    LEARNING_CAPTURED = "learning_captured"
    ERROR_RECOVERED = "error_recovered"

    SYSTEM_HEALTH = "system_health"
    METRIC_RECORDED = "metric_recorded"


class Event:
    """Represents an observable event in the workflow."""

    def __init__(
        self,
        event_type: EventType,
        source: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        level: NotificationLevel = NotificationLevel.INFO
    ):
        self.event_type = event_type
        self.source = source
        self.message = message
        self.data = data or {}
        self.level = level
        self.timestamp = datetime.now()
        self.id = f"{event_type.value}_{int(time.time() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.event_type.value,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "level": self.level.name,
            "timestamp": self.timestamp.isoformat()
        }

    def __repr__(self) -> str:
        return f"Event({self.event_type.value}, {self.source}, {self.message[:50]})"


class MetricsCollector:
    """Collects and aggregates metrics from agent executions."""

    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._counters: Dict[str, int] = {}
        self._lock = threading.Lock()

    def record(self, name: str, value: float) -> None:
        """Record a metric value."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(value)

    def increment(self, name: str, amount: int = 1) -> None:
        """Increment a counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def get_summary(self, name: str) -> Dict[str, float]:
        """Get summary statistics for a metric."""
        with self._lock:
            values = self._metrics.get(name, [])
            if not values:
                return {}
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        with self._lock:
            return self._counters.get(name, 0)

    def get_all(self) -> Dict[str, Any]:
        """Get all metrics and counters."""
        with self._lock:
            return {
                "metrics": {k: self.get_summary(k) for k in self._metrics},
                "counters": dict(self._counters)
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()


class EventLogger:
    """
    Logs events to file for audit trail.

    Events are stored as JSONL (JSON Lines) format for easy parsing.
    """

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir or os.getenv("LOG_DIR", ".tmp/logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, event: Event) -> None:
        """Log an event to file."""
        log_file = self.log_dir / f"events_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def get_events(
        self,
        date: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None
    ) -> List[Event]:
        """Retrieve events from log file with optional filtering."""
        target_date = date or datetime.now()
        log_file = self.log_dir / f"events_{target_date.strftime('%Y-%m-%d')}.jsonl"

        if not log_file.exists():
            return []

        events = []
        with open(log_file, "r") as f:
            for line in f:
                data = json.loads(line)
                if event_type and data["type"] != event_type.value:
                    continue
                if source and data["source"] != source:
                    continue
                events.append(data)

        return events


class ObservabilityHub:
    """
    Central hub for all observability concerns.

    Coordinates between:
    - Slack notifications
    - File logging
    - Metrics collection
    - Console output

    Usage:
        hub = ObservabilityHub()
        hub.emit(EventType.SCRIPT_STARTED, "my_script", "Starting execution")
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global observability hub."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.slack = SlackNotifier()
        self.logger = EventLogger()
        self.metrics = MetricsCollector()
        self.subscribers: List[Callable[[Event], None]] = []

        # Configuration
        self.console_enabled = os.getenv("OBSERVABILITY_CONSOLE", "true").lower() == "true"
        self.file_enabled = os.getenv("OBSERVABILITY_FILE", "true").lower() == "true"
        self.slack_enabled = os.getenv("SLACK_ENABLED", "true").lower() == "true"

        # Track active contexts
        self._active_directives: Dict[str, datetime] = {}
        self._active_scripts: Dict[str, datetime] = {}

        self._initialized = True

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """Subscribe to all events."""
        self.subscribers.append(callback)

    def emit(
        self,
        event_type: EventType,
        source: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        level: NotificationLevel = NotificationLevel.INFO,
        notify_slack: bool = True
    ) -> Event:
        """
        Emit an event to all channels.

        Args:
            event_type: Type of event
            source: Source component (script name, directive name, etc.)
            message: Human-readable message
            data: Additional structured data
            level: Severity level
            notify_slack: Whether to send Slack notification

        Returns:
            The created Event object
        """
        event = Event(event_type, source, message, data, level)

        # Console output
        if self.console_enabled:
            self._log_to_console(event)

        # File logging
        if self.file_enabled:
            self.logger.log(event)

        # Slack notification
        if notify_slack and self.slack_enabled:
            self._notify_slack(event)

        # Notify subscribers
        for callback in self.subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"[OBSERVABILITY] Subscriber error: {e}")

        return event

    def _log_to_console(self, event: Event) -> None:
        """Log event to console with formatting."""
        level_icons = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.DEBUG: "🔍"
        }
        icon = level_icons.get(event.level, "•")
        timestamp = event.timestamp.strftime("%H:%M:%S")
        print(f"[{timestamp}] {icon} [{event.source}] {event.message}")

    def _notify_slack(self, event: Event) -> None:
        """Send event to Slack."""
        title_map = {
            EventType.DIRECTIVE_STARTED: "📋 Directive Started",
            EventType.DIRECTIVE_COMPLETED: "✅ Directive Completed",
            EventType.DIRECTIVE_FAILED: "❌ Directive Failed",
            EventType.DIRECTIVE_UPDATED: "📝 Directive Updated",
            EventType.SCRIPT_STARTED: "🚀 Script Started",
            EventType.SCRIPT_COMPLETED: "✅ Script Completed",
            EventType.SCRIPT_FAILED: "❌ Script Failed",
            EventType.TASK_PROGRESS: "📊 Progress Update",
            EventType.TASK_CHECKPOINT: "🏁 Checkpoint",
            EventType.LEARNING_CAPTURED: "🧠 Learning Captured",
            EventType.ERROR_RECOVERED: "🔄 Error Recovered",
            EventType.SYSTEM_HEALTH: "💚 System Health",
            EventType.METRIC_RECORDED: "📈 Metrics"
        }

        fields = {"Source": event.source}
        fields.update({k: str(v)[:100] for k, v in event.data.items()})

        self.slack.send(
            event.message,
            level=event.level,
            title=title_map.get(event.type, "📌 Event"),
            fields=fields
        )

    # Convenience methods for common events

    def directive_started(self, name: str, context: Optional[Dict] = None) -> None:
        """Track directive execution start."""
        self._active_directives[name] = datetime.now()
        self.emit(
            EventType.DIRECTIVE_STARTED,
            name,
            f"Started directive: {name}",
            context
        )

    def directive_completed(self, name: str, result: Optional[Dict] = None) -> None:
        """Track directive completion."""
        duration = self._get_duration(self._active_directives.pop(name, None))
        data = {"duration": duration}
        if result:
            data.update(result)
        self.emit(
            EventType.DIRECTIVE_COMPLETED,
            name,
            f"Completed directive: {name}",
            data,
            NotificationLevel.SUCCESS
        )

    def directive_failed(self, name: str, error: Exception) -> None:
        """Track directive failure."""
        duration = self._get_duration(self._active_directives.pop(name, None))
        self.emit(
            EventType.DIRECTIVE_FAILED,
            name,
            f"Failed directive: {name} - {str(error)}",
            {"duration": duration, "error": str(error), "error_type": type(error).__name__},
            NotificationLevel.ERROR
        )

    def script_started(self, name: str, directive: Optional[str] = None) -> None:
        """Track script execution start."""
        self._active_scripts[name] = datetime.now()
        data = {"directive": directive} if directive else {}
        self.emit(EventType.SCRIPT_STARTED, name, f"Started script: {name}", data)

    def script_completed(self, name: str, metrics: Optional[Dict] = None) -> None:
        """Track script completion."""
        duration = self._get_duration(self._active_scripts.pop(name, None))
        data = {"duration": duration}
        if metrics:
            data.update(metrics)
            # Record metrics
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    self.metrics.record(f"{name}.{k}", float(v))
        self.emit(
            EventType.SCRIPT_COMPLETED,
            name,
            f"Completed script: {name}",
            data,
            NotificationLevel.SUCCESS
        )

    def script_failed(self, name: str, error: Exception) -> None:
        """Track script failure."""
        duration = self._get_duration(self._active_scripts.pop(name, None))
        self.metrics.increment("errors.total")
        self.metrics.increment(f"errors.{name}")
        self.emit(
            EventType.SCRIPT_FAILED,
            name,
            f"Script failed: {name} - {str(error)}",
            {"duration": duration, "error": str(error)},
            NotificationLevel.ERROR
        )

    def learning(self, source: str, learning: str, directive_updated: bool = False) -> None:
        """Track self-annealing learning event."""
        self.emit(
            EventType.LEARNING_CAPTURED,
            source,
            learning,
            {"directive_updated": directive_updated},
            NotificationLevel.INFO
        )

    def progress(self, source: str, message: str, percent: Optional[float] = None) -> None:
        """Track task progress."""
        data = {"percent": f"{percent:.1%}"} if percent is not None else {}
        self.emit(
            EventType.TASK_PROGRESS,
            source,
            message,
            data,
            notify_slack=False  # Don't spam Slack with progress updates
        )

    def _get_duration(self, start: Optional[datetime]) -> str:
        """Calculate duration string."""
        if not start:
            return "unknown"
        seconds = (datetime.now() - start).total_seconds()
        if seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        return f"{seconds/3600:.1f}h"


# Context managers for clean observability

@contextmanager
def observe_directive(name: str, context: Optional[Dict] = None):
    """
    Context manager for observing directive execution.

    Usage:
        with observe_directive("my_directive"):
            # directive execution code
            pass
    """
    hub = ObservabilityHub()
    hub.directive_started(name, context)
    try:
        yield hub
        hub.directive_completed(name)
    except Exception as e:
        hub.directive_failed(name, e)
        raise


@contextmanager
def observe_script(name: str, directive: Optional[str] = None):
    """
    Context manager for observing script execution.

    Usage:
        with observe_script("my_script", "my_directive") as obs:
            obs.progress("Processing...", 0.5)
            # script execution code
    """
    hub = ObservabilityHub()
    hub.script_started(name, directive)
    try:
        yield hub
        hub.script_completed(name)
    except Exception as e:
        hub.script_failed(name, e)
        raise


# Global hub accessor
def get_hub() -> ObservabilityHub:
    """Get the global observability hub instance."""
    return ObservabilityHub()


# Quick emit functions
def emit_info(source: str, message: str, **data) -> None:
    """Emit an info event."""
    get_hub().emit(EventType.TASK_PROGRESS, source, message, data, NotificationLevel.INFO)


def emit_warning(source: str, message: str, **data) -> None:
    """Emit a warning event."""
    get_hub().emit(EventType.TASK_PROGRESS, source, message, data, NotificationLevel.WARNING)


def emit_error(source: str, message: str, **data) -> None:
    """Emit an error event."""
    get_hub().emit(EventType.SCRIPT_FAILED, source, message, data, NotificationLevel.ERROR)


# Example usage
if __name__ == "__main__":
    print("Testing Observability Hub...")

    hub = get_hub()

    # Test directive tracking
    with observe_directive("test_directive", {"input": "test_data"}):
        print("Executing directive...")

        # Test script tracking
        with observe_script("test_script", "test_directive") as obs:
            obs.progress("test_script", "Starting...", 0.0)
            time.sleep(0.1)
            obs.progress("test_script", "Processing...", 0.5)
            time.sleep(0.1)
            obs.progress("test_script", "Finishing...", 0.9)

        # Test learning capture
        hub.learning("test_script", "Discovered that X works better than Y")

    # Print metrics
    print("\nMetrics collected:")
    print(json.dumps(hub.metrics.get_all(), indent=2))

    print("\nTest complete!")
