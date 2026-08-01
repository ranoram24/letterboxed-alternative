from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str
    display_name: str
    profile_picture_url: str | None
    created_at: datetime
