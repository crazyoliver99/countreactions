from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import time

app = Flask(__name__)
CORS(app)

# === Slack Config ===
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
CHANNEL_ID = "C04H3PK3KEJ"

if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN is not set in Render environment variables")

USER_IDS = {
    "Harilaos": "U07QSV6C8BU",
    "Ahmed": "U07U12AQD62",
    "Abi": "U07UYDUQ96K",
    "Luciana": "U05EVPH8FFU",
}

TARGET_REACTIONS_LIST = [
    "white_check_mark",
    "baby::skin-tone-2",
    "x",
    "male-detective::skin-tone-2",
]


def fetch_reactions(channel_id, oldest_ts, latest_ts, user_id):
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    cursor = None
    total_msgs = 0

    reaction_counts = {emoji: 0 for emoji in TARGET_REACTIONS_LIST}

    while True:
        params = {
            "channel": channel_id,
            "oldest": str(oldest_ts),
            "latest": str(latest_ts),
            "limit": 200
        }

        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params=params,
            timeout=30
        )

        data = resp.json()
        messages = data.get("messages", [])
        total_msgs += len(messages)

        for msg in messages:
            reactions = msg.get("reactions", [])
            for r in reactions:
                name = r.get("name")
                users = r.get("users", [])
                if name in reaction_counts and user_id in users:
                    reaction_counts[name] += 1

        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return {
        "total_messages": total_msgs,
        "reaction_counts": reaction_counts,
    }


@app.route("/", methods=["GET"])
def home():
    return "Slack Reaction Counter API is running"


@app.route("/count", methods=["POST"])
def count_reactions_route():
    data = request.get_json()

    user = data.get("user")
    start_ts = data.get("start_ts")

    if user not in USER_IDS:
        return jsonify({"error": "Unknown user"}), 400

    if start_ts is None:
        return jsonify({"error": "Missing timestamp"}), 400

    # FRONTEND sends UNIX timestamp already (UTC)
    try:
        start_ts = int(start_ts)
    except:
        return jsonify({"error": "Invalid timestamp format"}), 400

    # Safety check: timestamp cannot be in the future
    now = int(time.time())
    if start_ts > now:
        return jsonify({"error": "Timestamp cannot be in the future"}), 400

    user_id = USER_IDS[user]

    results = fetch_reactions(CHANNEL_ID, start_ts, now, user_id)
    return jsonify(results)


# Render will not run this block. Only for local debugging.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
