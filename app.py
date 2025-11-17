from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime
import pytz
import os

app = Flask(__name__)

# ---- Slack Config ----
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
CHANNEL_ID = "C04H3PK3KEJ"
HEADERS = {"Authorization": f"Bearer {SLACK_TOKEN}"}

TARGET_REACTIONS_LIST = [
    "white_check_mark",
    "baby::skin-tone-2",
    "x",
    "male-detective::skin-tone-2",
]
#let's see

def fetch_reactions(oldest, latest, target_user):
    counts = {emoji: 0 for emoji in TARGET_REACTIONS_LIST}
    cursor = None
    total_msgs = 0

    while True:
        params = {
            "channel": CHANNEL_ID,
            "oldest": str(oldest),
            "latest": str(latest),
            "limit": 200,
            "inclusive": True,
        }

        if cursor:
            params["cursor"] = cursor

        r = requests.get(
            "https://slack.com/api/conversations.history",
            headers=HEADERS,
            params=params,
        )

        data = r.json()
        messages = data.get("messages", [])
        total_msgs += len(messages)

        for msg in messages:
            reactions = msg.get("reactions", [])
            for r in reactions:
                if r["name"] in counts and target_user in r.get("users", []):
                    counts[r["name"]] += 1

        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return total_msgs, counts


@app.route("/count", methods=["POST"])
def count():
    body = request.json
    user = body["user"]
    local_ts = body["start_ts"]
    timezone_name = body["timezone"]  # NEW — user’s timezone

    # ---- Convert provided timestamp from user's timezone → UTC ----
    try:
        tz = pytz.timezone(timezone_name)
    except Exception:
        return jsonify({"error": f"Invalid timezone: {timezone_name}"}), 400

    dt_local = datetime.fromtimestamp(local_ts, tz)
    dt_utc = dt_local.astimezone(pytz.utc)
    start_ts_utc = int(dt_utc.timestamp())

    # ---- Slack uses UTC always ----
    end_ts = int(time.time())

    total, counts = fetch_reactions(start_ts_utc, end_ts, user)

    return jsonify({
        "messages_scanned": total,
        "reaction_counts": counts,
        "converted_start_timestamp_utc": start_ts_utc
    })

    # ---- Convert provided timestamp from user's timezone → UTC ----
@app.route("/")
def home():
    return "Slack Reaction Counter API is running"


if __name__ == "__main__":
    app.run()
