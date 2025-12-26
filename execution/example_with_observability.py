"""
Example Script with Observability

This demonstrates how to integrate observability into your execution scripts.
Run this file to see observability in action (Slack notifications require configuration).
"""

import time
import random
from typing import List, Dict

# Import observability tools
from slack_notifier import (
    observe,
    notify,
    notify_success,
    notify_error,
    notify_warning,
    NotificationLevel,
    AgentObserver
)
from observability import (
    observe_script,
    observe_directive,
    get_hub,
    emit_info,
    emit_warning
)


# =============================================================================
# Pattern 1: Decorator-based observability (simplest)
# =============================================================================

@observe("simple_task", "example_directive")
def simple_task_with_decorator():
    """
    Automatically tracks start/end/errors.
    Best for simple scripts that don't need progress updates.
    """
    print("Doing some work...")
    time.sleep(0.5)
    return {"status": "success", "items_processed": 42}


# =============================================================================
# Pattern 2: Context manager observability (recommended)
# =============================================================================

def task_with_progress():
    """
    Use context manager for scripts that need progress tracking.
    Gives you access to the hub for progress updates.
    """
    with observe_script("data_processing", "example_directive") as hub:
        items = list(range(10))

        for i, item in enumerate(items):
            # Report progress (console + file only, not Slack)
            hub.progress(
                "data_processing",
                f"Processing item {i+1}/{len(items)}",
                percent=(i + 1) / len(items)
            )
            time.sleep(0.1)

        # Script completion is automatic


# =============================================================================
# Pattern 3: Manual observer (most control)
# =============================================================================

def task_with_manual_observer():
    """
    Manual observer for complex scripts that need full control.
    """
    observer = AgentObserver("manual_task", "example_directive")

    # Start tracking
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
            time.sleep(0.1)

        # Report a warning
        if random.random() > 0.5:
            observer.log_warning(
                "Resource usage is high",
                details={"memory_percent": 85}
            )

        # Complete successfully
        observer.script_completed(
            result={"output_file": "result.json"},
            metrics={"rows_processed": 1000, "duration_ms": 500}
        )

    except Exception as e:
        observer.script_failed(e, context={"last_step": "step_3"})
        raise


# =============================================================================
# Pattern 4: Full directive tracking
# =============================================================================

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
            time.sleep(0.3)
            records = [{"id": i, "value": random.random()} for i in range(100)]

        # Script 2: Transform data
        with observe_script("transform_data", "data_pipeline"):
            print("Transforming data...")
            time.sleep(0.2)
            transformed = [{"id": r["id"], "normalized": r["value"] * 100} for r in records]

        # Script 3: Load data
        with observe_script("load_data", "data_pipeline"):
            print("Loading data to database...")
            time.sleep(0.2)

        # Capture a learning
        hub.learning(
            "data_pipeline",
            "Batch processing in groups of 50 is more efficient than single inserts",
            directive_updated=True
        )


# =============================================================================
# Pattern 5: Quick notifications
# =============================================================================

def send_quick_notifications():
    """
    Use quick notification functions for one-off alerts.
    """
    # Simple info notification
    notify("System check completed", title="📋 Health Check")

    # Success notification
    notify_success("Deployment completed to production")

    # Warning notification
    notify_warning("Disk space below 20%", fields={"disk": "/dev/sda1", "used": "82%"})

    # Error notification
    try:
        raise ValueError("Invalid configuration detected")
    except Exception as e:
        notify_error("Configuration validation failed", error=e)


# =============================================================================
# Pattern 6: Error handling with recovery
# =============================================================================

def task_with_error_recovery():
    """
    Demonstrates proper error handling and recovery logging.
    """
    hub = get_hub()

    with observe_script("resilient_task") as obs:
        for attempt in range(3):
            try:
                # Simulate work that might fail
                if attempt < 2 and random.random() > 0.5:
                    raise ConnectionError("API temporarily unavailable")

                print(f"Attempt {attempt + 1} succeeded!")
                break

            except ConnectionError as e:
                emit_warning(
                    "resilient_task",
                    f"Attempt {attempt + 1} failed, retrying...",
                    error=str(e)
                )
                time.sleep(0.5)

                if attempt == 2:
                    raise  # Re-raise on final attempt


# =============================================================================
# Main: Run all examples
# =============================================================================

def main():
    print("=" * 60)
    print("Observability Examples")
    print("=" * 60)
    print()

    print("1. Decorator-based observability")
    print("-" * 40)
    simple_task_with_decorator()
    print()

    print("2. Context manager with progress")
    print("-" * 40)
    task_with_progress()
    print()

    print("3. Manual observer")
    print("-" * 40)
    task_with_manual_observer()
    print()

    print("4. Full directive tracking")
    print("-" * 40)
    run_full_directive()
    print()

    print("5. Quick notifications")
    print("-" * 40)
    send_quick_notifications()
    print()

    print("6. Error handling with recovery")
    print("-" * 40)
    try:
        task_with_error_recovery()
    except Exception as e:
        print(f"Task failed after retries: {e}")
    print()

    # Print metrics summary
    print("=" * 60)
    print("Metrics Summary")
    print("=" * 60)
    import json
    hub = get_hub()
    print(json.dumps(hub.metrics.get_all(), indent=2))


if __name__ == "__main__":
    main()
