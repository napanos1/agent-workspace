"""
Slack Notifier - Centralized Slack notification utility for agent observability.

This module provides a simple interface for sending notifications to Slack
as part of the 3-layer agent architecture observability system.
"""

# Load environment variables from .env
from env_loader import load_env
load_env()

import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from functools import wraps
import traceback


class NotificationLevel(Enum):
    """Notification severity levels with corresponding Slack colors."""
    INFO = "#36a64f"      # Green
    WARNING = "#ffcc00"   # Yellow
    ERROR = "#ff0000"     # Red
    SUCCESS = "#2eb886"   # Teal
    DEBUG = "#808080"     # Gray


class SlackNotifier:
    """
    Slack notification client for agent observability.

    Usage:
        notifier = SlackNotifier()
        notifier.send("Task completed", level=NotificationLevel.SUCCESS)
    """

    def __init__(self, webhook_url: Optional[str] = None, channel: Optional[str] = None):
        """
        Initialize the Slack notifier.

        Args:
            webhook_url: Slack webhook URL. Falls back to SLACK_WEBHOOK_URL env var.
            channel: Override channel. Falls back to SLACK_CHANNEL env var.
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.channel = channel or os.getenv("SLACK_CHANNEL")
        self.enabled = os.getenv("SLACK_ENABLED", "true").lower() == "true"
        self.default_username = os.getenv("SLACK_USERNAME", "Agent Workflow")
        self.default_icon = os.getenv("SLACK_ICON", ":robot_face:")

    def _is_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return bool(self.webhook_url) and self.enabled

    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
        fields: Optional[Dict[str, str]] = None,
        context: Optional[str] = None
    ) -> bool:
        """
        Send a notification to Slack.

        Args:
            message: Main message text
            level: Notification severity level
            title: Optional title for the message
            fields: Optional key-value pairs to display
            context: Optional context/footer text

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_configured():
            print(f"[SLACK] Not configured - would send: {message}")
            return False

        payload = self._build_payload(message, level, title, fields, context)
        return self._send_payload(payload)

    def _build_payload(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str],
        fields: Optional[Dict[str, str]],
        context: Optional[str]
    ) -> Dict[str, Any]:
        """Build the Slack message payload."""
        attachment = {
            "color": level.value,
            "text": message,
            "ts": datetime.now().timestamp(),
            "footer": "Agent Workflow Observability"
        }

        if title:
            attachment["title"] = title

        if fields:
            attachment["fields"] = [
                {"title": k, "value": v, "short": len(str(v)) < 40}
                for k, v in fields.items()
            ]

        if context:
            attachment["footer"] = context

        payload = {
            "username": self.default_username,
            "icon_emoji": self.default_icon,
            "attachments": [attachment]
        }

        if self.channel:
            payload["channel"] = self.channel

        return payload

    def _send_payload(self, payload: Dict[str, Any]) -> bool:
        """Send the payload to Slack webhook."""
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except urllib.error.URLError as e:
            print(f"[SLACK] Failed to send notification: {e}")
            return False
        except Exception as e:
            print(f"[SLACK] Unexpected error: {e}")
            return False


class AgentObserver:
    """
    Observer for agent execution events.

    Provides structured observability for:
    - Script execution lifecycle (start, end, error)
    - Task progress tracking
    - Metrics collection
    - Error reporting with context

    Usage:
        observer = AgentObserver("my_script")
        observer.script_started({"input": "data"})
        # ... do work ...
        observer.script_completed({"result": "success"})
    """

    def __init__(self, script_name: str, directive: Optional[str] = None):
        """
        Initialize the observer.

        Args:
            script_name: Name of the executing script
            directive: Optional directive name this script belongs to
        """
        self.script_name = script_name
        self.directive = directive
        self.notifier = SlackNotifier()
        self.start_time: Optional[datetime] = None
        self.metrics: Dict[str, Any] = {}

    def script_started(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Log script execution start."""
        self.start_time = datetime.now()

        fields = {"Script": self.script_name}
        if self.directive:
            fields["Directive"] = self.directive
        if context:
            for k, v in context.items():
                fields[k] = str(v)[:100]  # Truncate long values

        self.notifier.send(
            f"Started execution of `{self.script_name}`",
            level=NotificationLevel.INFO,
            title="🚀 Script Started",
            fields=fields
        )

    def script_completed(
        self,
        result: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log successful script completion."""
        duration = self._get_duration()

        fields = {
            "Script": self.script_name,
            "Duration": duration
        }
        if metrics:
            self.metrics.update(metrics)
            for k, v in metrics.items():
                fields[k] = str(v)
        if result:
            for k, v in result.items():
                fields[k] = str(v)[:100]

        self.notifier.send(
            f"Successfully completed `{self.script_name}`",
            level=NotificationLevel.SUCCESS,
            title="✅ Script Completed",
            fields=fields
        )

    def script_failed(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log script failure with error details."""
        duration = self._get_duration()

        fields = {
            "Script": self.script_name,
            "Duration": duration,
            "Error Type": type(error).__name__,
            "Error": str(error)[:200]
        }
        if self.directive:
            fields["Directive"] = self.directive
        if context:
            for k, v in context.items():
                fields[k] = str(v)[:100]

        # Include stack trace in message
        stack = traceback.format_exc()
        message = f"Failed execution of `{self.script_name}`\n```{stack[-500:]}```"

        self.notifier.send(
            message,
            level=NotificationLevel.ERROR,
            title="❌ Script Failed",
            fields=fields
        )

    def log_progress(
        self,
        message: str,
        progress: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log progress update for long-running tasks."""
        fields = {"Script": self.script_name}
        if progress is not None:
            fields["Progress"] = f"{progress:.1%}"
        if details:
            for k, v in details.items():
                fields[k] = str(v)[:100]

        self.notifier.send(
            message,
            level=NotificationLevel.INFO,
            title="📊 Progress Update",
            fields=fields
        )

    def log_warning(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning event."""
        fields = {"Script": self.script_name}
        if details:
            for k, v in details.items():
                fields[k] = str(v)[:100]

        self.notifier.send(
            message,
            level=NotificationLevel.WARNING,
            title="⚠️ Warning",
            fields=fields
        )

    def log_learning(self, learning: str, directive_updated: bool = False) -> None:
        """Log when the system learns something (self-annealing event)."""
        fields = {
            "Script": self.script_name,
            "Directive Updated": "Yes" if directive_updated else "No"
        }
        if self.directive:
            fields["Directive"] = self.directive

        self.notifier.send(
            learning,
            level=NotificationLevel.INFO,
            title="🧠 Learning Captured",
            fields=fields
        )

    def _get_duration(self) -> str:
        """Calculate execution duration."""
        if not self.start_time:
            return "Unknown"
        delta = datetime.now() - self.start_time
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


def observe(script_name: str, directive: Optional[str] = None):
    """
    Decorator to automatically observe function execution.

    Usage:
        @observe("my_script", "my_directive")
        def main():
            # your code here
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            observer = AgentObserver(script_name, directive)
            observer.script_started({"args": str(args)[:100], "kwargs": str(kwargs)[:100]})

            try:
                result = func(*args, **kwargs)
                observer.script_completed({"return_type": type(result).__name__})
                return result
            except Exception as e:
                observer.script_failed(e)
                raise

        return wrapper
    return decorator


# Convenience functions for quick notifications
_default_notifier = None

def get_notifier() -> SlackNotifier:
    """Get or create the default notifier instance."""
    global _default_notifier
    if _default_notifier is None:
        _default_notifier = SlackNotifier()
    return _default_notifier


def notify(
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    **kwargs
) -> bool:
    """Quick notification using the default notifier."""
    return get_notifier().send(message, level, **kwargs)


def notify_error(message: str, error: Optional[Exception] = None, **kwargs) -> bool:
    """Quick error notification."""
    if error:
        message = f"{message}\n```{str(error)}```"
    return notify(message, NotificationLevel.ERROR, title="❌ Error", **kwargs)


def notify_success(message: str, **kwargs) -> bool:
    """Quick success notification."""
    return notify(message, NotificationLevel.SUCCESS, title="✅ Success", **kwargs)


def notify_warning(message: str, **kwargs) -> bool:
    """Quick warning notification."""
    return notify(message, NotificationLevel.WARNING, title="⚠️ Warning", **kwargs)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Slack Notifier...")
    print(f"Configured: {get_notifier()._is_configured()}")

    # Test basic notification
    notify("Test notification from Agent Workflow", title="🧪 Test")

    # Test observer
    observer = AgentObserver("test_script", "test_directive")
    observer.script_started({"test": True})
    observer.log_progress("Processing items...", progress=0.5)
    observer.script_completed({"items_processed": 100})

    print("Test complete!")
