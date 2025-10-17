# instructor.py
# Sends test JSON POST to main.py for round 1 and round 2

import requests
import json
import base64

API_URL = "http://127.0.0.1:8000/api-endpoint"

# Encode a small image/file as data URI (mock attachment)
def encode_attachment(data: bytes, name="sample.png"):
    b64 = base64.b64encode(data).decode()
    return {"name": name, "url": f"data:image/png;base64,{b64}"}

# Round 1 payload
payload_round1 = {
    "email": "student@example.com",
    "secret": "Rock3535",
    "task": "captcha-solver-demo",
    "round": 1,
    "nonce": "abc123",
    "brief": "Create a captcha solver that handles ?url=...",
    "checks": [
        "Repo has MIT license",
        "README.md is professional",
        "Page displays captcha URL passed at ?url=...",
        "Page displays solved captcha text within 15 seconds"
    ],
    "evaluation_url": "http://127.0.0.1:9000/notify",

    "attachments": [
        encode_attachment(b"sample image bytes", "sample.png")
    ]
}

# Round 2 payload (update)
payload_round2 = {
    "email": "student@example.com",
    "secret": "Rock3535",
    "task": "captcha-solver-demo",
    "round": 2,
    "nonce": "abc123",
    "brief": "Round 2 update: handle new captcha types",
    "checks": [
        "Repo has MIT license",
        "README.md is professional",
        "Page displays captcha URL passed at ?url=...",
        "Page displays solved captcha text within 15 seconds"
    ],
    "evaluation_url": "http://127.0.0.1:9000/notify",

    "attachments": [
        encode_attachment(b"round 2 image bytes", "sample_round2.png")
    ]
}

def send_request(payload):
    resp = requests.post(API_URL, json=payload)
    print("Status Code:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)



if __name__ == "__main__":
    print("=== Sending Round 1 Request ===")
    send_request(payload_round1)

    print("\n=== Sending Round 2 Request ===")
    send_request(payload_round2)
