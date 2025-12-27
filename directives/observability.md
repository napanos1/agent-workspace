# Observability Directive

## Goal
Maintain visibility into all agent workflow executions through real-time Slack notifications, file logging, metrics collection, and console output for script and directive lifecycle events.

## Inputs
- Script execution events (start, progress, completion, failure)
- Directive execution events (start, completion, failure, update)
- Warning events
- Self-annealing events (learnings)
- Metrics (counters and values)

## Tools/Scripts

### Primary Scripts
| Script | Purpose |
|--------|---------|
| `execution/slack_notifier.py` | Sends notifications to Slack webhook and provides script observation |
| `execution/observability.py` | Central observability hub with multi-channel logging, metrics, and event tracking |
| `execution/env_loader.py` | Loads environment variables from `.env` file |

### Environment Variables
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | - | Yes (for Slack) |
| `SLACK_CHANNEL` | Override channel | - | No |
| `SLACK_ENABLED` | Enable/disable Slack | `"true"` | No |
| `SLACK_USERNAME` | Bot username | `"Agent Workflow"` | No |
| `SLACK_ICON` | Bot icon emoji | `":robot_face:"` | No |
| `OBSERVABILITY_CONSOLE` | Enable console logging | `"true"` | No |
| `OBSERVABILITY_FILE` | Enable file logging | `"true"` | No |
| `LOG_DIR` | Directory for log files | `".tmp/logs"` | No |

## Outputs

### Slack Notifications
Messages sent to configured Slack channel with:
- Event type indicator (emoji title)
- Source script/directive name
- Human-readable message
- Structured fields (duration, metrics, context)
- Timestamp and severity color
- Footer: "Agent Workflow Observability" (or custom context)

### File Logs
- Format: JSONL (JSON Lines) in `LOG_DIR/events_YYYY-MM-DD.jsonl`
- Contains: event id, type, source, message, data, level, timestamp

### Console Output
- Formatted with timestamp, level icon, source, and message
- Format: `[HH:MM:SS] {icon} [{source}] {message}`

### Metrics
- Stored in-memory via `MetricsCollector`
- Supports: counters (increment) and metrics (record values with summary stats)

---

## Module: slack_notifier.py

### NotificationLevel (Enum)
Severity levels with corresponding Slack colors.

| Level | Color | Hex |
|-------|-------|-----|
| `INFO` | Green | `#36a64f` |
| `WARNING` | Yellow | `#ffcc00` |
| `ERROR` | Red | `#ff0000` |
| `SUCCESS` | Teal | `#2eb886` |
| `DEBUG` | Gray | `#808080` |

### SlackNotifier Class
Core notification client for sending messages to Slack.

**Constructor:**
```python
SlackNotifier(webhook_url: Optional[str] = None, channel: Optional[str] = None)
```
- Falls back to `SLACK_WEBHOOK_URL` and `SLACK_CHANNEL` env vars

**Methods:**
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `send()` | `message`, `level=INFO`, `title=None`, `fields=None`, `context=None` | `bool` | Send notification to Slack |
| `_is_configured()` | - | `bool` | Check if webhook is set and enabled |

**Usage:**
```python
from slack_notifier import SlackNotifier, NotificationLevel

notifier = SlackNotifier()
notifier.send(
    message="Task completed",
    level=NotificationLevel.SUCCESS,
    title="Optional Title",
    fields={"Key": "Value"},
    context="Optional footer text"
)
```

### AgentObserver Class
Observer for script execution lifecycle with automatic duration tracking.

**Constructor:**
```python
AgentObserver(script_name: str, directive: Optional[str] = None)
```

**Methods:**
| Method | Parameters | Description |
|--------|------------|-------------|
| `script_started()` | `context: Optional[Dict]` | Log script start, begin timing |
| `script_completed()` | `result: Optional[Dict]`, `metrics: Optional[Dict]` | Log successful completion with duration |
| `script_failed()` | `error: Exception`, `context: Optional[Dict]` | Log failure with error details and stack trace (last 500 chars) |
| `log_progress()` | `message: str`, `progress: Optional[float]`, `details: Optional[Dict]` | Log progress update with optional percentage |
| `log_warning()` | `message: str`, `details: Optional[Dict]` | Log warning event |
| `log_learning()` | `learning: str`, `directive_updated: bool = False` | Log self-annealing learning event |

**Usage:**
```python
from slack_notifier import AgentObserver

observer = AgentObserver("my_script", directive="my_directive")
observer.script_started(context={"input": "data"})
observer.log_progress("Processing items...", progress=0.5, details={"batch": 1})
observer.log_warning("Resource running low", details={"memory": "80%"})
observer.log_learning("Discovered optimal batch size is 100", directive_updated=True)
observer.script_completed(result={"items": 100}, metrics={"throughput": "50/s"})
```

**Error Handling:**
```python
try:
    # script logic
    observer.script_completed()
except Exception as e:
    observer.script_failed(e, context={"step": "processing"})
    raise
```

### @observe Decorator
Automatic observation wrapper for functions.

```python
from slack_notifier import observe

@observe("my_script", "my_directive")
def main():
    # Automatically sends script_started on entry (with args/kwargs truncated to 100 chars)
    # Automatically sends script_completed or script_failed on exit
    pass
```

### Quick Notification Functions
Convenience functions using a shared default notifier (singleton).

```python
from slack_notifier import notify, notify_success, notify_error, notify_warning, NotificationLevel, get_notifier

# Get or create default notifier
notifier = get_notifier()

# Generic notification
notify("Custom message", level=NotificationLevel.INFO, title="Custom Title")

# Typed notifications
notify_success("Task completed successfully")  # title: "Success"
notify_error("Something went wrong", error=exception)  # title: "Error", appends error in code block
notify_warning("Resource running low")  # title: "Warning"
```

---

## Module: observability.py

### EventType (Enum)
Types of observable events in the agent workflow.

| Event Type | Value | Description |
|------------|-------|-------------|
| `DIRECTIVE_STARTED` | `"directive_started"` | Directive execution began |
| `DIRECTIVE_COMPLETED` | `"directive_completed"` | Directive finished successfully |
| `DIRECTIVE_FAILED` | `"directive_failed"` | Directive encountered error |
| `DIRECTIVE_UPDATED` | `"directive_updated"` | Directive definition changed |
| `SCRIPT_STARTED` | `"script_started"` | Script execution began |
| `SCRIPT_COMPLETED` | `"script_completed"` | Script finished successfully |
| `SCRIPT_FAILED` | `"script_failed"` | Script encountered error |
| `TASK_PROGRESS` | `"task_progress"` | Progress update during task |
| `TASK_CHECKPOINT` | `"task_checkpoint"` | Checkpoint reached |
| `LEARNING_CAPTURED` | `"learning_captured"` | Self-annealing learning recorded |
| `ERROR_RECOVERED` | `"error_recovered"` | Error was recovered from |
| `SYSTEM_HEALTH` | `"system_health"` | System health check |
| `METRIC_RECORDED` | `"metric_recorded"` | Metric was recorded |

### Event Class
Represents an observable event.

**Constructor:**
```python
Event(
    event_type: EventType,
    source: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    level: NotificationLevel = NotificationLevel.INFO
)
```

**Attributes:**
- `id`: Auto-generated `"{event_type.value}_{timestamp_ms}"`
- `timestamp`: `datetime.now()` at creation

**Methods:**
- `to_dict()`: Serialize to dictionary for JSON

### MetricsCollector Class
Collects and aggregates metrics from agent executions. Thread-safe.

**Methods:**
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `record()` | `name: str`, `value: float` | `None` | Record a metric value |
| `increment()` | `name: str`, `amount: int = 1` | `None` | Increment a counter |
| `get_summary()` | `name: str` | `Dict[str, float]` | Get stats: count, sum, avg, min, max |
| `get_counter()` | `name: str` | `int` | Get counter value (0 if not exists) |
| `get_all()` | - | `Dict[str, Any]` | Get all metrics and counters |
| `reset()` | - | `None` | Reset all metrics |

### EventLogger Class
Logs events to file for audit trail in JSONL format.

**Constructor:**
```python
EventLogger(log_dir: Optional[str] = None)
# Falls back to LOG_DIR env var, then ".tmp/logs"
```

**Methods:**
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `log()` | `event: Event` | `None` | Append event to daily log file |
| `get_events()` | `date: Optional[datetime]`, `event_type: Optional[EventType]`, `source: Optional[str]` | `List[Event]` | Retrieve filtered events from log |

### ObservabilityHub Class (Singleton)
Central hub for all observability concerns. Thread-safe singleton pattern.

**Access:**
```python
from observability import ObservabilityHub, get_hub

hub = ObservabilityHub()  # Always returns same instance
# or
hub = get_hub()
```

**Core Method - emit():**
```python
emit(
    event_type: EventType,
    source: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    level: NotificationLevel = NotificationLevel.INFO,
    notify_slack: bool = True
) -> Event
```

**Convenience Methods:**
| Method | Parameters | Description |
|--------|------------|-------------|
| `directive_started()` | `name: str`, `context: Optional[Dict]` | Track directive start |
| `directive_completed()` | `name: str`, `result: Optional[Dict]` | Track directive completion |
| `directive_failed()` | `name: str`, `error: Exception` | Track directive failure |
| `script_started()` | `name: str`, `directive: Optional[str]` | Track script start |
| `script_completed()` | `name: str`, `metrics: Optional[Dict]` | Track script completion (auto-records numeric metrics) |
| `script_failed()` | `name: str`, `error: Exception` | Track script failure (increments error counters) |
| `learning()` | `source: str`, `learning: str`, `directive_updated: bool` | Log learning event |
| `progress()` | `source: str`, `message: str`, `percent: Optional[float]` | Log progress (no Slack) |
| `subscribe()` | `callback: Callable[[Event], None]` | Subscribe to all events |

### Context Managers

**observe_directive:**
```python
from observability import observe_directive

with observe_directive("my_directive", {"input": "data"}):
    # directive execution code
    # Automatically calls directive_started/directive_completed/directive_failed
    pass
```

**observe_script:**
```python
from observability import observe_script

with observe_script("my_script", "my_directive") as hub:
    hub.progress("my_script", "Processing...", 0.5)
    # script execution code
    # Automatically calls script_started/script_completed/script_failed
```

### Quick Emit Functions
```python
from observability import emit_info, emit_warning, emit_error

emit_info("source", "message", key="value")    # EventType.TASK_PROGRESS, INFO level
emit_warning("source", "message", key="value") # EventType.TASK_PROGRESS, WARNING level
emit_error("source", "message", key="value")   # EventType.SCRIPT_FAILED, ERROR level
```

---

## Event Flow

### Slack Title Mapping
| EventType | Slack Title |
|-----------|-------------|
| `DIRECTIVE_STARTED` | "Directive Started" |
| `DIRECTIVE_COMPLETED` | "Directive Completed" |
| `DIRECTIVE_FAILED` | "Directive Failed" |
| `DIRECTIVE_UPDATED` | "Directive Updated" |
| `SCRIPT_STARTED` | "Script Started" |
| `SCRIPT_COMPLETED` | "Script Completed" |
| `SCRIPT_FAILED` | "Script Failed" |
| `TASK_PROGRESS` | "Progress Update" |
| `TASK_CHECKPOINT` | "Checkpoint" |
| `LEARNING_CAPTURED` | "Learning Captured" |
| `ERROR_RECOVERED` | "Error Recovered" |
| `SYSTEM_HEALTH` | "System Health" |
| `METRIC_RECORDED` | "Metrics" |

### Console Level Icons
| Level | Icon |
|-------|------|
| INFO | information symbol |
| WARNING | warning symbol |
| ERROR | X mark |
| SUCCESS | checkmark |
| DEBUG | magnifying glass |

---

## Edge Cases

### Slack Not Configured
- System continues to function
- `send()` returns `False`
- Message printed: `[SLACK] Not configured - would send: <message>`

### Network Failure
- Slack send fails gracefully with 10-second timeout
- Error logged to console: `[SLACK] Failed to send notification: <error>`
- `send()` returns `False`
- Execution continues uninterrupted

### Long-Running Scripts
- Use `log_progress()` or `hub.progress()` for periodic updates with optional progress percentage
- Progress updates do NOT send to Slack by default (avoid spam)
- Duration automatically tracked from start to completion/failure

### Subscriber Errors
- If a subscriber callback raises an exception, it is caught and logged
- Other subscribers and main flow continue unaffected
- Message printed: `[OBSERVABILITY] Subscriber error: <error>`

### Field Value Truncation
- All field values are truncated to 100 characters in notifications
- Stack traces in error notifications are truncated to last 500 characters
- Error messages in failure events are truncated to 200 characters

### Missing Start Time
- If duration calculated without prior start call, returns `"Unknown"` or `"unknown"`

---

## Self-Annealing Notes

### Learnings
_Add discoveries here as the system evolves:_

1. _Example: "Batch size of 100 optimal for API calls"_

### Common Issues
_Document recurring problems and solutions:_

1. _Example: "Webhook rate limiting - add 1s delay between notifications"_

---

## Setup Checklist

1. [ ] Create Slack webhook at https://api.slack.com/messaging/webhooks
2. [ ] Add `SLACK_WEBHOOK_URL` to `.env`
3. [ ] Optionally set `LOG_DIR` in `.env` for custom log location
4. [ ] Test with: `python execution/slack_notifier.py`
5. [ ] Test with: `python execution/observability.py`
6. [ ] Verify notification appears in Slack
7. [ ] Verify log files created in LOG_DIR

---

## API Limits and Considerations

### Slack Webhook
- HTTP POST with `Content-Type: application/json`
- 10-second timeout on requests
- No built-in rate limiting - consider adding delays for high-volume scripts
- Returns `200` on success

### File Logging
- Daily log rotation by filename (one file per day)
- No automatic log cleanup - manage disk space manually
- Log directory created automatically if missing

### Metrics
- In-memory only - resets on process restart
- Thread-safe with locks
- No persistence across executions
