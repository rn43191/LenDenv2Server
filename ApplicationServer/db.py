
from datetime import datetime
from re import U

from pymongo import MongoClient
from bson.objectid import ObjectId

from ApplicationServer.dbDetails import *

####

def addConversation(userId, title, participants,desc):
    try:
        for p in participants:
            if users.find_one({"_id": p}, {"_id": 1}) is not None:
                if p!=userId:
                    connSafeRes = checkConnectionSafe(userId, p)
                    if connSafeRes.get("status"):
                        return {"status": False, "error": "User not connected to participant"}

            else:
                return {"status": False, "error": "Invalid participant id"}

        res = convo.insert_one({"title": title, "creator_id": userId, "created_at": datetime.now(
        ).timestamp(), "participants": participants,"description":desc})
        for p in participants:
            userConvo.find_one_and_update(
                {"_id": p, }, {"$push": {"conversation_ids": res.inserted_id}})

        return {"status": True, "error": None}
    except:
        return {"status": False, "error": "An error occured while adding conversation"}

####

def addMemo(memoType, memo, sentTime, convoId, senderId, chatOrTransType):
    userConvoRes = userConvo.find_one(
        {"_id": senderId, "conversation_ids": ObjectId(convoId)})

    if userConvoRes is None:
        return {
            "status": False, "error": "User not part of conversation"
        }

    try:
        creator_id = convo.find_one(
            {"_id": ObjectId(convoId)}, {"creator_id": 1}).get("creator_id")
        if memoType == "chat":
            chats.insert_one({"memo_type": memoType, "type": chatOrTransType, "message": memo, "sent_time": sentTime,
                              "conversation_id": ObjectId(convoId), "sender_id": senderId})
        if memoType == "transaction":
            if creator_id != senderId:
                chatOrTransType = (-1*chatOrTransType)
            transactions.insert_one({"memo_type": memoType, "type": chatOrTransType, "amount": memo, "sent_time": sentTime,
                                     "conversation_id": ObjectId(convoId), "sender_id": senderId})

        return {"status": True, "error": None}
    except Exception as e:
        return {"status": False, "error": e.__str__()}

def fetchUserMemos(userId, convoId):
    userConvoRes = userConvo.find_one(
        {"_id": userId, "conversation_ids": ObjectId(convoId)})

    if userConvoRes is None:
        return {
            "status": False, "error": "User not part of conversation", "data": None
        }

    try:
        userTrans = transactions.find({"conversation_id": ObjectId(convoId)})
        userChats = chats.find({"conversation_id": ObjectId(convoId)})
        data=[]
        for uT in userTrans:
            uT["_id"]=str(uT["_id"])
            uT["conversation_id"]=str(uT["conversation_id"])
            data.append(uT)
        for uC in userChats:
            uC["_id"]=str(uC["_id"])
            uC["conversation_id"]=str(uC["conversation_id"])
            data.append(uC)
        return {"status": True, "error": None, "data": data}
    except Exception as e:
        return {"status": False, "error": e.__str__(), "data": None}

#### Methods for connections

def addConnection(userId, contactId, usersName, contactsName, isPending):

    connSafeRes = checkConnectionSafe(userId, contactId)
    if not connSafeRes.get("status"):
        return {"status": False, "error": connSafeRes.get("error")}

    try:
        connections.insert_one({"user_id": userId, "contact_id": contactId, "alias_name_user": usersName,
                                "alias_name_contact": contactsName, "created_at": datetime.now().timestamp(), "is_pending": isPending})

        return {"status": True, "error": None}
    except:
        return {"status": False, "error": "Unable to add connection"}


def checkConnectionSafe(userId, contactId):
    if connections.find_one({"user_id": userId, "contact_id": contactId}) is not None or connections.find_one({"user_id": contactId, "contact_id": userId}) is not None:
        return {"status": False, "error": "Entry already exists"}
    return {"status": True, "error": None}


def getUserConnections(userId):
    try:
        res1 = connections.find({"user_id": userId})
        res2 = connections.find({"contact_id": userId})
        result1=[]
        result2=[]
        for doc in res1:
            user=users.find_one({"_id":doc["contact_id"]},{"email": 1, "first_name": 1, "last_name": 1, "image_url": 1})
            user.update({"already_connected":True})
            doc['_id']=str(doc['_id'])
            doc.update({"other_user":user})
            result1.append(doc)
            
        for doc in res2:
            user=users.find_one({"_id":doc["user_id"]},{"email": 1, "first_name": 1, "last_name": 1, "image_url": 1})
            user.update({"already_connected":True})
            doc['_id']=str(doc['_id'])
            doc.update({"other_user":user})
            result2.append(doc)
        
        data = result1+result2
        return {"status": True, "error": None, "data": data}
    except Exception as e:
        return {"status": False, "error": e.__str__(), "data": None}



# change email verified to true
def getContactDetails(value, userId):
    res=list(users.find({"$and": [{"_id": {"$regex": value, "$options": "i"}},
                                     {"_id": {"$ne": userId}},{"email_verified":True}]},
                           {"email": 1, "first_name": 1, "last_name": 1, "image_url": 1}))
    result=[]
    for doc in res:
        if checkConnectionSafe(userId,doc.get("_id")).get("status"):
            doc.update({"already_connected":False})
            result.append(doc)
    return result

####





def summarizeTransaction(convoId, userId):
    userConvoRes = userConvo.find_one(
        {"_id": userId, "conversation_ids": ObjectId(convoId)})

    if userConvoRes is None:
        return {
            "status": False, "error": "User not part of conversation", "data": None
        }

    try:
        creator_id = convo.find_one(
            {"_id": ObjectId(convoId)}, {"creator_id": 1})
        data = list(transactions.find({"conversation_id": ObjectId(
            convoId), }, {"amount": 1, "type": 1, "_id": 1}))
        netLen = 0
        netDen = 0
        for d in data:

            if d.get("type") == 1:
                netLen += d.get("amount")
            else:
                netDen += d.get("amount")

        if creator_id != userId:
            c = netLen
            netLen = netDen
            netDen = c
        return {"status": True, "error": None, "data": {"len": netLen, "den": netDen}}
    except Exception as e:
        return {"status": False, "error": e.__str__(), "data": None}


def getUserDetails(userId):
    return users.find_one({"_id": userId})



def getUserConversations(userId):
    res = userConvo.find_one({"_id": userId})
    convoIds = res.get("conversation_ids")
    conversations = []
    for c in convoIds:
        res=convo.find_one({"_id": c})
        res["_id"]=str(res["_id"])
        conversations.append(res)
    return conversations
