from datetime import time
from typing import Optional
from pydantic import BaseModel

class LunchBlockSettingsUpsert(BaseModel):
    organization_id: str
    enabled: bool = True
    start_time: time = time(13, 0, 0)
    end_time: time = time(14, 0, 0)
    title: str = "Lunch"
    weekdays_only: bool = True
