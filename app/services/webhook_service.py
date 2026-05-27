import threading
from datetime import datetime, timezone

import httpx


def _deliver(url: str, payload: dict) -> None:
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(url, json=payload)
    except Exception:
        pass


def dispatch_webhook(webhook_url: str, generation_id: str, status: str, **kwargs) -> None:
    payload = {
        "generation_id": generation_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    thread = threading.Thread(target=_deliver, args=(webhook_url, payload), daemon=True)
    thread.start()
