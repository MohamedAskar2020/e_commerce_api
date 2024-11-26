from fastapi import HTTPException, status
import jwt
from passlib.context import CryptContext
from dotenv import dotenv_values
from models import User

config_credentials = dotenv_values(".env")
SECRET_KEY = config_credentials["SECRET_KEY"]
ALGORITHM = config_credentials["ALGORITHM"]
ACCESS_TOKEN_EXPIRE_MINUTES = int(config_credentials["ACCESS_TOKEN_EXPIRE_MINUTES"])

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = await User.get(id=payload.get("id"))
    except:
        raise credentials_exception
    return user

async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def authenticated_user(username: str, password: str):
    user = await User.get(username=username)
    if user and verify_password(password, user.password):
        return user
    return False




async def token_generator(username: str, password: str):
    user = await authenticated_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = {
        "id": user.id,
        "username": user.username
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return token


