# Observability Patterns Directive

## Goal
Document the standard patterns for integrating observability into execution scripts, providing templates for different use cases.

## Reference Script
| Script | Purpose |
|--------|---------|
| `execution/example_with_observability.py` | Reference implementation demonstrating all observability patterns |

## Prerequisites
- `execution/slack_notifier.py` - Slack notifications and AgentObserver
- `execution/observability.py` - ObservabilityHub, context managers, and emit functions
- `execution/env_loader.py` - Environment variable loading

---

## Pattern 1: Decorator-Based (Simplest)

**Use Case:** Simple scripts that do not need progress updates during execution.

**Features:**
- Automatic start/end/error tracking
- Minimal code changes required
- Returns function result unchanged

**Implementation:**
```python
from slack_notifier import observe

@observe("script_name", "directive_name")
def main():
    """
    Automatically tracks start/end/errors.
    Best for simple scripts that don't need progress updates.
    """
    # Your code here
    return {"status": "success", "items_processed": 42}
```

**Events Emitted:**
| Event | When | Data |
|-------|------|------|
| `script_started` | Function entry | `args` (truncated), `kwargs` (truncated) |
| `script_completed` | Function return | `return_type` |
| `script_failed` | Exception raised | Error details |

---

## Pattern 2: Context Manager (Recommended)

**Use Case:** Scripts that need progress tracking during execution.

**Features:**
- Access to ObservabilityHub for progress updates
- Automatic lifecycle management
- Clean try/except handling

**Implementation:**
```python
from observability import observe_script

def task_with_progress():
    """
    Use context manager for scripts that need progress tracking.
    Gives you access to the hub for progress updates.
    """
    with observe_script("data_processing", "directive_name") as hub:
        items = list(range(10))

        for i, item in enumerate(items):
            # Report progress (console + file only, not Slack)
            hub.progress(
                "data_processing",
                f"Processing item {i+1}/{len(items)}",
                percent=(i + 1) / len(items)
            )
            # Process item...

        # Script completion is automatic
```

**Events Emitted:**
| Event | When | Data |
|-------|------|------|
| `script_started` | Context entry | `directive` (if provided) |
| `task_progress` | Each `hub.progress()` call | `percent` (formatted) |
| `script_completed` | Context exit (success) | `duration` |
| `script_failed` | Exception raised | `duration`, `error` |

**Note:** Progress events do NOT send to Slack by default to avoid spam.

---

## Pattern 3: Manual Observer (Most Control)

**Use Case:** Complex scripts needing full control over all events.

**Features:**
- Direct control over all event details
- Custom fields and metrics
- Warning and learning capture

**Implementation:**
```python
from slack_notifier import AgentObserver

def task_with_manual_observer():
    """
    Manual observer for complex scripts that need full control.
    """
    observer = AgentObserver("manual_task", "directive_name")

    # Start tracking with custom context
    observer.script_started({
        "input_file": "data.csv",
        "mode": "full"
    })

    try:
        # Simulate work with progress
        for i in range(5):
            observer.log_progress(
                f"Step {i+1}/5 completed",
                progress=(i + 1) / 5,
                details={"current_step": f"step_{i+1}"}
            )

        # Report warnings as needed
        if resource_usage_high:
            observer.log_warning(
                "Resource usage is high",
                details={"memory_percent": 85}
            )

        # Complete with results and metrics
        observer.script_completed(
            result={"output_file": "result.json"},
            metrics={"rows_processed": 1000, "duration_ms": 500}
        )

    except Exception as e:
        observer.script_failed(e, context={"last_step": "step_3"})
        raise
```

**Available Methods:**
| Method | Purpose | Sends to Slack |
|--------|---------|----------------|
| `script_started(context)` | Begin tracking | Yes |
| `script_completed(result, metrics)` | Success completion | Yes |
| `script_failed(error, context)` | Failure with error | Yes |
| `log_progress(message, progress, details)` | Progress update | Yes |
| `log_warning(message, details)` | Warning event | Yes |
| `log_learning(learning, directive_updated)` | Learning capture | Yes |

---

## Pattern 4: Full Directive Tracking

**Use Case:** Multi-script workflows under a single directive.

**Features:**
- Nested script tracking within directive
- Learning capture for self-annealing
- Shows script hierarchy

**Implementation:**
```python
from observability import observe_directive, observe_script, get_hub

def run_full_directive():
    """
    Track an entire directive with multiple scripts.
    Shows how scripts nest within directives.
    """
    with observe_directive("data_pipeline", {"source": "api", "target": "database"}):
        hub = get_hub()

        # Script 1: Fetch data
        with observe_script("fetch_data", "data_pipeline"):
            print("Fetching data from API...")
            records = fetch_from_api()

        # Script 2: Transform data
        with observe_script("transform_data", "data_pipeline"):
            print("Transforming data...")
            transformed = transform(records)

        # Script 3: Load data
        with observe_script("load_data", "data_pipeline"):
            print("Loading data to database...")
            load_to_db(transformed)

        # Capture a learning for self-annealing
        hub.learning(
            "data_pipeline",
            "Batch processing in groups of 50 is more efficient than single inserts",
            directive_updated=True
        )
```

**Event Hierarchy:**
```
DIRECTIVE_STARTED: data_pipeline
  SCRIPT_STARTED: fetch_data
  SCRIPT_COMPLETED: fetch_data
  SCRIPT_STARTED: transform_data
  SCRIPT_COMPLETED: transform_data
  SCRIPT_STARTED: load_data
  SCRIPT_COMPLETED: load_data
  LEARNING_CAPTURED: data_pipeline
DIRECTIVE_COMPLETED: data_pipeline
```

---

## Pattern 5: Quick Notifications

**Use Case:** One-off alerts without full lifecycle tracking.

**Features:**
- Simple function calls
- No context required
- Good for standalone notifications

**Implementation:**
```python
from slack_notifier import (
    notify,
    notify_success,
    notify_error,
    notify_warning,
    NotificationLevel
)

def send_quick_notifications():
    """
    Use quick notification functions for one-off alerts.
    """
    # Simple info notification with custom title
    notify("System check completed", title="Health Check")

    # Success notification
    notify_success("Deployment completed to production")

    # Warning notification with additional fields
    notify_warning(
        "Disk space below 20%",
        fields={"disk": "/dev/sda1", "used": "82%"}
    )

    # Error notification with exception
    try:
        raise ValueError("Invalid configuration detected")
    except Exception as e:
        notify_error("Configuration validation failed", error=e)
```

**Function Reference:**
| Function | Level | Default Title |
|----------|-------|---------------|
| `notify(message, level, **kwargs)` | Configurable | None |
| `notify_success(message, **kwargs)` | SUCCESS | "Success" |
| `notify_warning(message, **kwargs)` | WARNING | "Warning" |
| `notify_error(message, error, **kwargs)` | ERROR | "Error" |

---

## Pattern 6: Error Handling with Recovery

**Use Case:** Scripts with retry logic that need to track recovery attempts.

**Features:**
- Warning on each failed attempt
- Proper re-raise on final failure
- Recovery tracking

**Implementation:**
```python
from observability import observe_script, emit_warning

def task_with_error_recovery():
    """
    Demonstrates proper error handling and recovery logging.
    """
    with observe_script("resilient_task") as obs:
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                # Attempt the operation
                result = perform_operation()
                print(f"Attempt {attempt + 1} succeeded!")
                break

            except ConnectionError as e:
                # Log warning for each failed attempt
                emit_warning(
                    "resilient_task",
                    f"Attempt {attempt + 1} failed, retrying...",
                    error=str(e)
                )

                if attempt == max_attempts - 1:
                    raise  # Re-raise on final attempt

                time.sleep(backoff_delay)
```

**Event Flow (3 attempts, success on 3rd):**
```
SCRIPT_STARTED: resilient_task
TASK_PROGRESS (WARNING): Attempt 1 failed, retrying...
TASK_PROGRESS (WARNING): Attempt 2 failed, retrying...
SCRIPT_COMPLETED: resilient_task
```

**Event Flow (3 attempts, all fail):**
```
SCRIPT_STARTED: resilient_task
TASK_PROGRESS (WARNING): Attempt 1 failed, retrying...
TASK_PROGRESS (WARNING): Attempt 2 failed, retrying...
SCRIPT_FAILED: resilient_task
```

---

## Choosing the Right Pattern

| Scenario | Recommended Pattern |
|----------|---------------------|
| Simple one-shot script | Pattern 1: Decorator |
| Script with progress updates | Pattern 2: Context Manager |
| Complex script with warnings/learnings | Pattern 3: Manual Observer |
| Multi-script workflow | Pattern 4: Full Directive |
| Standalone alert/notification | Pattern 5: Quick Notifications |
| Script with retry logic | Pattern 6: Error Recovery |

---

## Common Imports

```python
# From slack_notifier.py
from slack_notifier import (
    observe,                 # Decorator
    notify,                  # Generic notification
    notify_success,          # Success notification
    notify_error,            # Error notification
    notify_warning,          # Warning notification
    NotificationLevel,       # Enum for levels
    AgentObserver            # Manual observer class
)

# From observability.py
from observability import (
    observe_script,          # Script context manager
    observe_directive,       # Directive context manager
    get_hub,                 # Get ObservabilityHub singleton
    emit_info,               # Quick info emit
    emit_warning             # Quick warning emit
)
```

---

## Running the Examples

```bash
# Run all example patterns
python execution/example_with_observability.py
```

**Output includes:**
1. Each pattern execution with console logging
2. Slack notifications (if configured)
3. File logging to LOG_DIR
4. Metrics summary at the end

---

## Self-Annealing Notes

### Learnings
_Add discoveries here as patterns evolve:_

1. _Example: "Decorator pattern insufficient for ETL jobs needing progress"_

### Common Issues
_Document recurring problems and solutions:_

1. _Example: "Remember to use `as hub` to get reference in context manager"_
