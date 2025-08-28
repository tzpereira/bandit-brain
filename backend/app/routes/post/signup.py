import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.repositories.users import get_user_by_email, create_user

router = APIRouter()

class SignupRequest(BaseModel):
	email: EmailStr
	password: str

@router.post("/signup")
def signup(data: SignupRequest):
	if get_user_by_email(data.email):
		raise HTTPException(status_code=400, detail="Email already registered")

	hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
	user_id = create_user(data.email, hashed)
	return {"user_id": user_id, "email": data.email}