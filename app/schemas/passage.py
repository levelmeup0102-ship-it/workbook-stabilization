from datetime import datetime

from pydantic import BaseModel


class Passage(BaseModel):
    id: int | None = None
    book_name: str
    unit: str
    lesson: str
    english_text: str
    korean_translation: str = ""
    updated_at: datetime | None = None
