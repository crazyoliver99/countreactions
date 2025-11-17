from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime
from pytz import timezone, utc
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow frontend to access backend

SLACK_TOKEN = "YOUR_SLACK_BOT_TOKEN"
CHANNEL_ID = "YOUR_CHANNEL_ID"

def fetch_reactions(channel_id, start_ts, end_ts, target_user):
    url = "https://slack.com/api/conversations.history"
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    params = {
        "channel": channel_id,
        "oldest": start_ts,
        "latest": end_ts,
        "inclusive": True
    }

    all_reactions = {}
    user_post_found = False

    while True:
        response = requests.get(url, headers=headers, params=params).json()

        if not response.get("ok"):
            return {"error": response.get("error", "Unknown error")}

        messages = response.get("messages", [])

        for msg in messages:
            if msg.get("user") == target_user:
                user_post_found = True

            if "reactions" in msg:
                for reaction in msg["reactions"]:
                    name = reaction["name"]
                    count = reaction["count"]
                    all_reactions[name] = all_reactions.get(name, 0) + count

        if not response.get("has_more"):
            break

        params["cursor"] = response.get("response_metadata", {}).get("next_cursor")
        if not params["cursor"]:
            break

    return {
        "user_post_found": user_post_found,
        "reactions": all_reactions,
        "total_reactions": sum(all_reactions.values())
    }

@app.route("/", methods=["GET"])
def home():
    return "Slack Reaction Counter API is running"

# NEW WORKING POST ENDPOINT
@app.route("/count", methods=["POST"])
def count_reactions():
    data = request.get_json()
    user = data.get("user")
    start_ts = data.get("start_ts")

    if not user or not start_ts:
        return jsonify({"error": "Missing user or timestamp"}), 400

    end_ts = int(time.time())
    result = fetch_reactions(CHANNEL_ID, start_ts, end_ts, user)

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
