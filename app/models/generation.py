from dataclasses import dataclass
from enum import Enum


class GenerationStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Generation:
    id: str
    client_id: str
    status: GenerationStatus
    prompt: str
    style: str | None
    output_size: str
    cost: int
    result_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = ""
    updated_at: str = ""
