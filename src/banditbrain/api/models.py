from pydantic import BaseModel


class User(BaseModel):
    id: int
    email: str
    password: str
    created_at: str
    is_demo: bool = False
