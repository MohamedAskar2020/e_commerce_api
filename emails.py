from typing import List
from fastapi import BackgroundTasks, FastAPI
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse
from dotenv import dotenv_values
import jwt

from models import User


config_credentials = dotenv_values(".env")


conf = ConnectionConfig(
    MAIL_USERNAME=config_credentials["EMAIL"],
    MAIL_PASSWORD=config_credentials["PASSWORD"],
    MAIL_FROM=config_credentials["EMAIL"],
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="HudaStore",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

class EmailSchema(BaseModel):
    email: List[EmailStr]


# @app.post("/email")
async def send_email(email: EmailSchema, instance: User) -> JSONResponse:

    token_data = {
        "id": instance.id,
        "username": instance.username
    }
    token = jwt.encode(token_data, config_credentials["SECRET_KEY"], algorithm=config_credentials["ALGORITHM"])
    template = f"""
        <!DOCTYPE html>
            <html>
                <head></head>
                <body>
                    <div style= "display: flex; align-items: center; justify-content: center; flex-direction: column;">
                        <h3>Account Verification</h3>
                        <br />
                        <p>Thanks for choosing HudaShop, please click on the link below to verify your account</p>
                        <a 
                            style="margin-top: 1rem; padding: 1rem border-radius: 0.5rem; font-size: 1rem; text-decoration: none; background: #0275d8; color: white;" 
                            href="http://localhost:8000/verification/?token={token}">
                            Click here to verify your email
                        </a>
                        <p>Please kindly ignore this email if you did not register for HudaShop</p>
                    </div>
                </body>
        </html>
    """


    
    message = MessageSchema(
        subject="HudaShop Verification Email",
        recipients=email, 
        # .model_dump().get("email")
        body=template,
        subtype="html"
        )

    fm = FastMail(conf)
    await fm.send_message(message=message)
    return JSONResponse(status_code=200, content={"message": "email has been sent"}) 