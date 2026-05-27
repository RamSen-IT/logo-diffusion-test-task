from pydantic import BaseModel, field_validator


class CreateGenerationRequest(BaseModel):
    prompt: str
    style: str | None = None
    output_size: str = "1024"

    @field_validator("output_size")
    @classmethod
    def validate_output_size(cls, v: str) -> str:
        if v not in ("512", "1024", "2048"):
            raise ValueError("output_size must be one of: 512, 1024, 2048")
        return v

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt is required and cannot be empty")
        return v.strip()


CREDIT_COSTS = {
    "512": 2,
    "1024": 5,
    "2048": 10,
}
