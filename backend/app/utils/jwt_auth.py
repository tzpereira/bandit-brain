import os
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

SECRET_KEY = os.getenv("HASH_SECRET_KEY")
ALGORITHM = os.getenv("HASH_ALGORITHM")
TOKEN_EXPIRE_MINUTES = os.getenv("HASH_TOKEN_EXPIRE_MINUTES")

security = HTTPBearer()

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"user_id": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["user_id"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token")
    except (jwt.InvalidTokenError, jwt.DecodeError):
        raise HTTPException(status_code=401, detail="Invalid token")