
# start python -m api_testing:api --reload

from fastapi import Request, HTTPException, Body, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from fastapi import FastAPI
import time
import jwt
import requests


JWT_SECRET = "secret"
JWT_ALGORITHM = "HS256"

users = []


class UserSchema(BaseModel):
    username: str
    password: str


def check_user(data: UserSchema):
    for user in users:
        if user.username == data.username and user.password == data.password:
            return True
    return False


def token_response(token: str):
    return {"access_token": token}


def sign_jwt(user_id: str):
    payload = {"user_id": user_id, "expires": time.time() + 600}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token_response(token)


def decode_jwt(token: str):
    try:
        decoded_token = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        return (
            decoded_token if decoded_token["expires"] >= time.time() else None
        )
    except Exception:
        return {}
    

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token."
                )
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=403, detail="Invalid authorization code."
            )

    def verify_jwt(self, jwtoken: str):
        isTokenValid: bool = False

        try:
            payload = decode_jwt(jwtoken)
        except Exception:
            payload = None
        if payload:
            isTokenValid = True
        return isTokenValid


api = FastAPI()

@api.get("/", tags=["root"])
async def read_root():
    return {"message": "Hello World!"}


@api.post("/user/signup", tags=["user"])
async def create_user(user: UserSchema = Body(...)):
    users.append(user)
    return sign_jwt(user.username)

@api.get("/secured", dependencies=[Depends(JWTBearer())], tags=["root"])
async def read_root_secured():
    return {"message": "Hello World! but secured"}



@api.post("/user/login", tags=["user"])
async def user_login(user: UserSchema = Body(...)):
    if check_user(user):
        return sign_jwt(user.username)
    return {"error": "Wrong login details!"}
