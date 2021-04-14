import jwt
import time
import db
from flask import request
from itsdangerous import URLSafeTimedSerializer

from dotenv import load_dotenv
from os import getenv

load_dotenv("lenden.env")

ISSUER = "auth-server"
JWT_LIFE_SPAN = 86400
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

authorization_codes = {}

serializer=URLSafeTimedSerializer(getenv("SECRET_KEY"))

with open(".\\AuthServer\\private.pem", "rb") as f:
    private_key = f.read()

with open(".\\AuthServer\\public.pem", "rb") as f:
    public_key = f.read()

def allowedFile(filename):
    ext=filename.rsplit('.', 1)[1].lower()
    if '.' in filename and ext in ALLOWED_EXTENSIONS:
        return {"status":True,"data":ext}
    return {"status":False,"data":None}

def authenticateUserCredentials(userId, password):
    return db.validateUser(userId=userId, password=password)


def verifyToken(token):
    try:
        data = jwt.decode(token, public_key, algorithms=["RS256"])
        return {"isVerified": True, "error": None, "data": data}
    except Exception as e:
        return {"isVerified": False, "error": e.__str__(), "data": None}


def generateAccessToken(userId):

    headers = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": ISSUER,
        "exp": time.time() + JWT_LIFE_SPAN,
        "user_id": userId,
    }

    access_token = jwt.encode(
        payload=payload, key=private_key, algorithm="RS256", headers=headers).decode()

    return access_token


def authentication():
    token = request.headers.get("Authorization")

    if token is None:
        return {
            "isVerified": False,
            "statusCode": 400,
            "error": "Invalid Request",
            "data": None,
        }

    if not token.startswith("Token "):
        return {
            "isVerified": False,
            "statusCode": 400,
            "error": "Invalid Authorization Header",
            "data": None,
        }

    token = token.split(" ")[1]
    resp = verifyToken(token=token)
    if not resp["isVerified"]:
        resp.update(
            {
                "statusCode": 401,
            }
        )
        return resp

    resp.update(
        {
            "statusCode": 200,
        }
    )
    
    return resp


