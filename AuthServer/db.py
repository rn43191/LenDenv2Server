from time import time
from pymongo import MongoClient
import hashlib
import uuid
from datetime import datetime

client = MongoClient(
    'mongodb+srv://rishu_kewl:rishu_kewl@cluster0.pfkvm.mongodb.net/test')

DataBase = client.get_database("LenDen")


users = DataBase.get_collection("users")
accounts = DataBase.get_collection("accounts")
userConvo = DataBase.get_collection("userConversations")


def validateUser(userId, password):

    user = accounts.find_one({"_id": userId})
    salt = ""
    if user != None:
        salt = user["salt"]
        hashed_password = hashPassword(password, salt)

        if hashed_password == user["password"]:
            return {"status":True,"error":None}
        return {"status":False,"error":"Invalid Credentials"}
    return {"status":False,"error":"User not found"}


def addUser(userId, password, email, firstName, lastName, phoneNo,imageUrl):
    account = users.find_one({"email": email})
    try:
        if account is None:
            salt = uuid.uuid4().hex
            accounts.insert_one({"_id": userId, "password": hashPassword(
                password, salt), "salt": salt, "email": email})
            users.insert_one({"first_name": firstName, "_id": userId, "last_name": lastName, "phone": phoneNo,
                             "email": email, "created_at": datetime.now().timestamp(), "email_verified": False, "phone_verified": False,"image_url":imageUrl})
            userConvo.insert_one({"_id": userId, "conversation_ids": []})
            return {"status": True, "error": None}
        else:
            return {"status": False, "error": "Email already in use"}
    except:
        return {"status": False, "error": "Username not available"}


def getUser(userId):
    user=users.find_one({"_id":userId})
    if user is None:
        return {"status":False,"error":"Invalid user id","data":None}
    
    return {"status":True,"error":None,"data":user}

def hashPassword(password, salt):
    return hashlib.sha256(str(password + salt).encode('utf-8')).hexdigest()


def getEmail(userId):
    try:
        emailRes=users.find_one({"_id":userId,},{"email":1,"email_verified":1,})
        if emailRes is None:
            return {"status":False,"error":"User not found","data":None}
        
        return {"status":True,"error":None,"data":emailRes}
    except Exception as e:
        return {"status":False,"error":e.__str__(),"data":None}

def updateEmailVerification(email):
    try:
        res=users.find_one_and_update({"email":email},{"$set":{"email_verified":True}},{"_id":1})
        return {
            "status":True,
            "error":None,
            "data":res
        }
    except Exception as e:
        return {
            "status":False,
            "error":e.__str__(),
            "data":None
        }

def test():
    print(1)
