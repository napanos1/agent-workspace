# Observability Directive

## Goal
Maintain visibility into all agent workflow executions through structured logging, metrics collection, and real-time Slack notifications.

## Inputs
- Script execution events (start, progress, completion, failure)
- Directive lifecycle events
- Self-annealing events (learnings, directive updates)
- System health metrics

## Tools/Scripts

### Primary Scripts
| Script | Purpose |
|--------|---------|
| `execution/slack_notifier.py` | Sends notifications to Slack webhook |
| `execution/observability.py` | Central observability hub and event tracking |

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | Yes |
| `SLACK_CHANNEL` | Override channel (optional) | No |
| `SLACK_ENABLED` | Enable/disable Slack (default: true) | No |
| `SLACK_USERNAME` | Bot username (default: "Agent Workflow") | No |
| `SLACK_ICON` | Bot icon emoji (default: ":robot_face:") | No |
| `OBSERVABILITY_CONSOLE` | Enable console logging (default: true) | No |
| `OBSERVABILITY_FILE` | Enable file logging (default: true) | No |
| `LOG_DIR` | Log file directory (default: .tmp/logs) | No |

## Outputs

### Slack Notifications
Messages sent to configured Slack channel with:
- Event type indicator (emoji)
- Source script/directive name
- Human-readable message
- Structured fields (duration, metrics, context)
- Timestamp and severity color

### Log Files
JSON Lines format stored in `.tmp/logs/`:
- `events_YYYY-MM-DD.jsonl` - Daily event logs
- Contains: event type, source, message, data, level, timestamp

### Metrics
Collected via `MetricsCollector`:
- Execution durations
- Error counts
- Custom per-script metrics

## Usage Patterns

### Basic Script Observability
```python
from observability import observe_script

with observe_script("my_script", "my_directive") as obs:
    obs.progress("my_script", "Processing items...", 0.5)
    # ... script logic ...
```

### Decorator Pattern
```python
from slack_notifier import observe

@observe("my_script", "my_directive")
def main():
    # ... script logic ...
    pass
```

### Quick Notifications
```python
from slack_notifier import notify_success, notify_error, notify_warning

notify_success("Task completed successfully")
notify_error("Something went wrong", exception)
notify_warning("Resource running low")
```

### Full Directive Tracking
```python
from observability import observe_directive, get_hub

with observe_directive("data_processing"):
    hub = get_hub()

    with observe_script("fetch_data"):
        # ... fetch logic ...
        pass

    with observe_script("transform_data"):
        # ... transform logic ...
        pass

    hub.learning("data_processing", "Discovered optimal batch size is 100")
```

## Event Types

| Event | When Triggered | Slack? |
|-------|----------------|--------|
| `directive_started` | Directive begins execution | ✅ |
| `directive_completed` | Directive finishes successfully | ✅ |
| `directive_failed` | Directive encounters unrecoverable error | ✅ |
| `directive_updated` | Directive SOP is modified | ✅ |
| `script_started` | Script begins execution | ✅ |
| `script_completed` | Script finishes successfully | ✅ |
| `script_failed` | Script encounters error | ✅ |
| `task_progress` | Progress update during execution | ❌ |
| `learning_captured` | Self-annealing event recorded | ✅ |
| `error_recovered` | Error handled and execution continued | ✅ |

## Notification Levels

| Level | Color | Use Case |
|-------|-------|----------|
| `INFO` | Green | Normal events, progress updates |
| `WARNING` | Yellow | Non-critical issues, degraded performance |
| `ERROR` | Red | Failures, exceptions |
| `SUCCESS` | Teal | Completions, achievements |
| `DEBUG` | Gray | Detailed debugging info |

## Edge Cases

### Slack Not Configured
- System continues to function
- Events logged to console and file
- Warning printed: `[SLACK] Not configured - would send: <message>`

### Network Failure
- Slack send fails gracefully
- Error logged to console
- Execution continues uninterrupted
- Events still logged to file

### High Event Volume
- Progress events skip Slack by default
- Use `notify_slack=False` for noisy events
- File logging remains unthrottled

### Long-Running Scripts
- Use `progress()` for periodic updates
- Only final completion/failure sent to Slack
- Progress logged to file and console

## Self-Annealing Notes

### Learnings
_Add discoveries here as the system evolves:_

1. _Example: "Batch size of 100 optimal for API calls"_

### Common Issues
_Document recurring problems and solutions:_

1. _Example: "Webhook rate limiting - add 1s delay between notifications"_

## Setup Checklist

1. [ ] Create Slack webhook at https://api.slack.com/messaging/webhooks
2. [ ] Add `SLACK_WEBHOOK_URL` to `.env`
3. [ ] Test with: `python execution/slack_notifier.py`
4. [ ] Verify notification appears in Slack
5. [ ] Import observability in your scripts
