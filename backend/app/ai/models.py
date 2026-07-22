from pydantic import BaseModel, Field


class AIWorkoutRequest(BaseModel):
    module: str
    level: str
    stance: str
    rounds: int = Field(default=6)
    round_time: int = Field(default=180)
    pace_seconds: int = Field(default=10)
