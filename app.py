from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import time
from datetime import datetime, timezone

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
    iteration = 0

    reaction_counts = {emoji: 0 for emoji in TARGET_REACTIONS_LIST}
    
    # DIAGNOSTIC LOGGING
    print("=" * 60)
    print(f"FETCH REACTIONS CALLED")
    print(f"oldest_ts: {oldest_ts} -> {datetime.fromtimestamp(float(oldest_ts), tz=timezone.utc)}")
    print(f"latest_ts: {latest_ts} -> {datetime.fromtimestamp(float(latest_ts), tz=timezone.utc)}")
    print(f"user_id: {user_id}")
    print(f"Time range: {(float(latest_ts) - float(oldest_ts))/86400:.2f} days")
    print("=" * 60)

    while True:
        iteration += 1
        params = {
            "channel": channel_id,
            "oldest": str(oldest_ts),
            "latest": str(latest_ts),
            "limit": 200,
        }

        if cursor:
            params["cursor"] = cursor

        print(f"\n[Iteration {iteration}] Making API request...")
        print(f"  Cursor: {cursor if cursor else 'None (first request)'}")

        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params=params,
            timeout=30,
        )

        data = resp.json()
        
        print(f"  API Response OK: {data.get('ok')}")
        if not data.get("ok"):
            print(f"  ERROR: {data.get('error')}")
            break
        
        messages = data.get("messages", [])
        total_msgs += len(messages)
        
        print(f"  Messages received: {len(messages)}")
        print(f"  Total messages so far: {total_msgs}")
        
        # Count reactions in these messages
        reactions_in_batch = 0
        for msg in messages:
            reactions = msg.get("reactions", [])
            for r in reactions:
                name = r.get("name", "")
                users = r.get("users", [])

                # If ALL → count everyone. If specific user → only that user.
                if user_id != "ALL" and user_id not in users:
                    continue

                n = name.lower()

                if "white_check_mark" in n:
                    reaction_counts["white_check_mark"] += 1
                    reactions_in_batch += 1
                elif "detective" in n:
                    reaction_counts["male-detective::skin-tone-2"] += 1
                    reactions_in_batch += 1
                elif "baby" in n:
                    reaction_counts["baby::skin-tone-2"] += 1
                    reactions_in_batch += 1
                elif n == "x":
                    reaction_counts["x"] += 1
                    reactions_in_batch += 1
        
        print(f"  Reactions found in this batch: {reactions_in_batch}")

        # Check for next cursor
        next_cursor = data.get("response_metadata", {}).get("next_cursor")
        has_more = data.get("has_more", False)
        
        print(f"  has_more: {has_more}")
        print(f"  next_cursor exists: {bool(next_cursor)}")
        
        if next_cursor:
            print(f"  Next cursor: {next_cursor[:50]}...")
        
        cursor = next_cursor
        if not cursor:
            print(f"\n[END] No more pages. Stopping pagination.")
            break
        
        # Safety limit
        if iteration >= 50:
            print(f"\n[SAFETY] Hit iteration limit of 50. Stopping.")
            break

    print("\n" + "=" * 60)
    print(f"FINAL RESULTS:")
    print(f"Total iterations: {iteration}")
    print(f"Total messages: {total_msgs}")
    print(f"Reaction counts: {reaction_counts}")
    print("=" * 60)

    return {
        "total_messages": total_msgs,
        "reaction_counts": reaction_counts,
        "iterations": iteration,  # Extra debug info
    }


@app.route("/", methods=["GET"])
def home():
    return "Slack Reaction Counter API is running"


@app.route("/count", methods=["POST"])
def count_reactions_route():
    data = request.get_json()

    user = data.get("user")
    start_ts = data.get("start_ts")

    if user != "ALL" and user not in USER_IDS:
        return jsonify({"error": "Unknown user"}), 400

    if start_ts is None:
        return jsonify({"error": "Missing timestamp"}), 400

    try:
        start_ts = int(start_ts)
    except:
        return jsonify({"error": "Invalid timestamp format"}), 400

    # If ALL → special flag
    user_id = "ALL" if user == "ALL" else USER_IDS[user]

    end_ts = int(time.time())

    results = fetch_reactions(CHANNEL_ID, start_ts, end_ts, user_id)
    return jsonify(results)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
