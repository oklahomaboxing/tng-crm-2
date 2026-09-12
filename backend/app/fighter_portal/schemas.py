from pydantic import BaseModel


class InviteFighterIn(BaseModel):
    fighter_id: int


class ActivateFighterIn(BaseModel):
    token: str
    password: str
    confirm_password: str
