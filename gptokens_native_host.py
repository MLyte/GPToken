#!/usr/bin/env python3
import json
import os
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path


CONFIG_DIR = Path(
    os.environ.get("GPTOKENS_CONFIG_DIR", str(Path.home() / ".config" / "gptokens"))
)
STATE_FILE = CONFIG_DIR / "usage_state.json"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def read_message() -> dict | None:
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("<I", raw_length)[0]
    payload = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(payload)


def send_message(message: dict) -> None:
    encoded = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def enrich_model(model: dict) -> dict:
    used = int(model.get("used", 0))
    quota = int(model.get("quota", 0))
    hours = int(model.get("hours", 0))
    remaining = max(0, quota - used) if quota > 0 else 0
    reset_at = (datetime.now() + timedelta(hours=hours)).isoformat(timespec="seconds")

    enriched = dict(model)
    enriched["remaining"] = remaining
    enriched["remaining_percent"] = int(round((remaining / max(1, quota or 1)) * 100))
    enriched["reset_at"] = reset_at
    return enriched


def persist_state(message: dict) -> dict:
    ensure_config_dir()

    models = [enrich_model(model) for model in message.get("models", [])]
    payload = {
        "plan": message.get("plan", "plus"),
        "source": message.get("source", "browser-extension"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "models": models,
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return {"ok": True, "saved_to": str(STATE_FILE)}


def main() -> int:
    ensure_config_dir()

    while True:
        message = read_message()
        if message is None:
            break

        message_type = message.get("type")
        if message_type == "write_state":
            send_message(persist_state(message))
        elif message_type == "ping":
            send_message({"ok": True, "pong": True})
        else:
            send_message({"ok": False, "error": f"unknown message type: {message_type}"})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
