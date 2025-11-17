from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

import os
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
CHANNEL_ID = "C04H3PK3KEJ"

HEADERS = {"Authorization": f"Bearer {SLACK_TOKEN}"}

TARGET_REACTIONS_LIST = [
    "white_check_mark",
    "baby::skin-tone-2",
    "x",
    "male-detective::skin-tone-2",
]

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
    start_ts = body["start_ts"]
    end_ts = int(time.time())

    total, counts = fetch_reactions(start_ts, end_ts, user)

    return jsonify(
        {
            "messages_scanned": total,
            "reaction_counts": counts,
        }
    )


@app.route("/")
def home():
    return "Slack Reaction Counter API Running"
