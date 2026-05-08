from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    project: str
    version: str
    inference_backend: str
    inference_model: str
