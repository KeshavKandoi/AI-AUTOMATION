from typing import Any
from pydantic import BaseModel, ConfigDict


class DiscordWebhookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    webhook_url: Any
