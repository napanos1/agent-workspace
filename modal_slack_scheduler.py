"""
Modal Scheduled Task - Sends Slack message every 5 minutes.

Setup:
1. Create a Modal secret named "slack-webhook" with your webhook URL:
   modal secret create slack-webhook SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

2. Deploy with: modal deploy modal_slack_scheduler.py
"""

import modal
import json
import urllib.request
from datetime import datetime

app = modal.App("slack-scheduler")

@app.function(
    schedule=modal.Period(minutes=5),
    secrets=[modal.Secret.from_name("slack-webhook")]
)
def send_slack_message():
    """Send a scheduled Slack message every 5 minutes."""
    import os

    webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    payload = {
        "username": "Claude Agent",
        "icon_emoji": ":robot_face:",
        "attachments": [{
            "color": "#36a64f",
            "title": "Scheduled Check-in",
            "text": "whats good homie",
            "fields": [
                {"title": "Timestamp", "value": datetime.now().strftime("%m/%d/%y %I:%M%p"), "short": True},
                {"title": "Status", "value": "Running", "short": True}
            ],
            "footer": "Modal Scheduler"
        }]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Slack message sent: {response.status}")
        return {"status": "sent", "timestamp": datetime.now().isoformat()}


@app.local_entrypoint()
def main():
    """Test the function locally before deploying."""
    result = send_slack_message.remote()
    print(f"Test result: {result}")
