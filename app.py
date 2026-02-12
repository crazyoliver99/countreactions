from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import time
from datetime import datetime, timezone
from collections import Counter

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
    "hourglass",
    "hourglass_flowing_sand",
]


def fetch_reactions(channel_id, oldest_ts, latest_ts, user_id):
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    cursor = None
    total_msgs = 0
    iteration = 0

    reaction_counts = {emoji: 0 for emoji in TARGET_REACTIONS_LIST}
    
    # Track ALL emoji names we see
    all_emoji_names = Counter()
    
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

        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params=params,
            timeout=30,
        )

        data = resp.json()
        
        if not data.get("ok"):
            print(f"  ERROR: {data.get('error')}")
            break
        
        messages = data.get("messages", [])
        total_msgs += len(messages)
        
        print(f"  Messages received: {len(messages)}")
        
        # Track ALL emoji names we encounter
        for msg in messages:
            reactions = msg.get("reactions", [])
            for r in reactions:
                name = r.get("name", "")
                users = r.get("users", [])
                
                # Count ALL emoji types (for diagnostic purposes)
                all_emoji_names[name] += len(users) if user_id == "ALL" else (1 if user_id in users else 0)
                
                # If ALL → count everyone. If specific user → only that user.
                if user_id != "ALL" and user_id not in users:
                    continue

                n = name.lower()

                if "white_check_mark" in n:
                    reaction_counts["white_check_mark"] += 1
                elif "detective" in n:
                    reaction_counts["male-detective::skin-tone-2"] += 1
                elif "baby" in n:
                    reaction_counts["baby::skin-tone-2"] += 1
                elif n == "x":
                    reaction_counts["x"] += 1
                elif n == "hourglass":
                    reaction_counts["hourglass"] += 1
                elif n == "hourglass_flowing_sand":
                    reaction_counts["hourglass_flowing_sand"] += 1

        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
        
        if iteration >= 50:
            print(f"\n[SAFETY] Hit iteration limit. Stopping.")
            break

    print("\n" + "=" * 60)
    print(f"FINAL RESULTS:")
    print(f"Total messages: {total_msgs}")
    print(f"Reaction counts: {reaction_counts}")
    print(f"\n🔍 ALL EMOJI NAMES FOUND (with counts):")
    for emoji_name, count in all_emoji_names.most_common(20):
        print(f"  '{emoji_name}': {count}")
    print("=" * 60)

    return {
        "total_messages": total_msgs,
        "reaction_counts": reaction_counts,
        "iterations": iteration,
        "debug_all_emojis": dict(all_emoji_names.most_common(20)),  # Return for debugging
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
