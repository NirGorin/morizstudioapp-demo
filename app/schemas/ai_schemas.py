from pydantic import BaseModel
from typing import List

class ExerciseRec(BaseModel):
    exercise: str
    reason: str

class AiSummaryOut(BaseModel):
    summary: str
    avoid: List[ExerciseRec]
    caution: List[ExerciseRec]
    safe: List[ExerciseRec]
