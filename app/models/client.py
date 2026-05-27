from dataclasses import dataclass


@dataclass
class Client:
    id: str
    name: str
    webhook_url: str | None = None
