from datetime import date, time, datetime
from typing import Optional, Literal
from pydantic import BaseModel, field_validator, EmailStr

Frequency = Literal["daily", "every_2_days", "weekdays", "custom"]

class EmailJobCreate(BaseModel):
    organization_id: str
    to_email: EmailStr
    subject: str
    body: str
    start_date: date
    end_date: date
    frequency: Frequency = "daily"
    custom_dates: Optional[list[date]] = None
    send_time: time = time(9, 0, 0)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v

    @field_validator("custom_dates")
    @classmethod
    def custom_required(cls, v, info):
        if info.data.get("frequency") == "custom" and not v:
            raise ValueError("custom_dates required when frequency is 'custom'")
        return v

class EmailJobUpdate(BaseModel):
    to_email: Optional[EmailStr] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    frequency: Optional[Frequency] = None
    custom_dates: Optional[list[date]] = None
    send_time: Optional[time] = None
    status: Optional[str] = None
