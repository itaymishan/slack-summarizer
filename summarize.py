from flask import Request, jsonify
import os
import openai
import requests

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def fetch_messages(channel_id):
    url = "https://slack.com/api/conversations.history"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    params = {
        "channel": channel_id,
        "limit": 50
    }
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    if not data.get("ok"):
        raise Exception("Failed to fetch messages")
    return [m["text"] for m in reversed(data["messages"]) if "subtype" not in m]

def summarize_messages(messages):
    prompt = "Summarize the following Slack conversation:\n\n" + "\n".join(messages)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=300
    )
    return response['choices'][0]['message']['content']

def post_message(channel, text):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-type": "application/json"
    }
    json_data = {
        "channel": channel,
        "text": text
    }
    requests.post(url, headers=headers, json=json_data)

def handler(request: Request):
    form = request.form
    user_id = form.get("user_id")
    channel_id = form.get("channel_id")
    text = form.get("text").strip()

    try:
        messages = fetch_messages(channel_id)
        summary = summarize_messages(messages)

        if text == "private":
            resp = requests.post("https://slack.com/api/conversations.open", headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-type": "application/json"
            }, json={"users": user_id})
            dm_channel = resp.json()["channel"]["id"]
            post_message(dm_channel, f"📝 Here's your private summary:\n\n{summary}")
        else:
            post_message(channel_id, f"📝 Summary of recent messages:\n\n{summary}")

        return "", 200
    except Exception as e:
        return f"Error: {str(e)}", 500