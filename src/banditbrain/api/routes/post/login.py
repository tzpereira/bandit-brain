import bcrypt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from banditbrain.api.jwt_auth import create_access_token
from banditbrain.api.rate_limit import limiter
from banditbrain.api.repositories.users import get_user_by_email

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest):
    user = get_user_by_email(data.email)

    if not user or not bcrypt.checkpw(data.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer"}
