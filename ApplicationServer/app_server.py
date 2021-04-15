
from datetime import datetime
import json
from bson.objectid import ObjectId


#import ssl
from AuthServer.auth import authentication
from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room, emit, close_room

from bson import json_util

import db

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')


@app.route("/convo", methods=["POST", "GET"])
def conversation():
    authResponse = authentication()

    if request.method == "POST" and authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        data = request.get_json()
        title = data.get("title")
        participants = data.get("participants")
        desc = data.get("description")

        if None in [title, participants]:
            return app.response_class(response=json.dumps({"status": "failure", "error": "Invalid request","data":None}), mimetype="application/json",), 400

        userId = authResponse.get("data").get("user_id")
        participants.append(userId)
        addConvoRes = db.addConversation(userId, title, participants, desc)
        if addConvoRes.get("status"):
            return app.response_class(response=json.dumps({"status": "success", "error": None,"data":addConvoRes.get("data")}), mimetype="application/json",), 200
        else:
            return app.response_class(response=json.dumps({"status": "failure", "error": addConvoRes.get("error")}), mimetype="application/json",), 400

    if request.method == "GET" and authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        userId = authResponse.get("data").get("user_id")
        userConvo = db.getUserConversations(userId)

        return app.response_class(response=json.dumps({"status": "success", "error": None, "data": userConvo}, default=json_util.default), mimetype="application/json"), 200

    return app.response_class(response=json.dumps({"status": "unauthorized", "error": authResponse.get("error")}), mimetype="application/json",), 401


@app.route("/memo", methods=["POST", "GET"])
def chatOrTrans():
    authResponse = authentication()
    if request.method == "POST" and authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        data = request.get_json()
        memoType = data.get("memo_type")
        msgType = data.get("msg_type")
        transType = data.get("transaction_type")
        memo = data.get("memo")
        sentTime = data.get("sent_time")
        convoId = data.get("conversation_id")

        if None in [memoType, memo, sentTime, convoId]:
            return app.response_class(response=json.dumps({"status": "failure", "error": "Invalid Request"}), mimetype="application/json",), 400

        userId = authResponse.get("data").get("user_id")
        chatOrTransType = ""
        if memoType == "chat":
            chatOrTransType = msgType
        if memoType == "transaction":
            chatOrTransType = transType
        addMemoRes = db.addMemo(memoType, memo, sentTime,
                                convoId, userId, chatOrTransType)
        if addMemoRes.get("status"):
            return app.response_class(response=json.dumps({"status": "success", "error": None}), mimetype="application/json",), 200
        else:
            return app.response_class(response=json.dumps({"status": "failure", "error": addMemoRes.get("error")}), mimetype="application/json",), 400

    if request.method == "GET" and authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        userId = authResponse.get("data").get("user_id")

    return app.response_class(response=json.dumps({"status": "unauthorized", "error": authResponse.get("error")}), mimetype="application/json",), 401


@app.route("/connections", methods=["POST", "GET"])
def connection():
    authResponse = authentication()
    if request.method == "POST" and authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        data = request.get_json()
        contactId = data.get("contact_id")
        contactsName = data.get("alias_name_contact")

        if contactId is None:
            return app.response_class(response=json.dumps({
                "status": "failure", "error": "Invalid request"
            })), 400

        userId = authResponse.get("data").get("user_id")
        userDetails = db.getUserDetails(userId)
        contactDetails = db.getUserDetails(contactId)
        if not userDetails.get("email_verified") or not contactDetails.get("email_verified"):
            return app.response_class(response=json.dumps({"status": "failure", "error": "Email not verified"}), mimetype="application/json",), 400
        usersName = userDetails.get("first_name") + \
            " "+userDetails.get("last_name")
        if contactsName is None:
            contactsName = contactDetails.get(
                "first_name")+" "+contactDetails.get("last_name")
        addConnRes = db.addConnection(
            userId, contactId, usersName, contactsName, True)
        if addConnRes.get("status"):
            return app.response_class(response=json.dumps({"status": "success", "error": None}), mimetype="application/json",), 200

        if not addConnRes.get("status"):
            return app.response_class(response=json.dumps({"status": "failure", "error": addConnRes.get("error")}), mimetype="application/json",), 400

    if request.method == "GET" and authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        userId = authResponse.get("data").get("user_id")
        data = db.getUserConnections(userId)

        if not data.get("status"):

            return app.response_class(response=json.dumps({"status": "failure", "error": data.get("error"), "data": None}), mimetype="application/json"),  400

        return app.response_class(response=json.dumps({"status": "success", "error": None, "data": data.get("data")}), mimetype="application/json"),  200

    return app.response_class(response=json.dumps({"status": "unauthorized", "error": authResponse.get("error")}), mimetype="application/json",), 401


@app.route("/fetch/users/<value>", methods=["GET"])
def fetchUsers(value):
    authResponse = authentication()
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        userId = authResponse.get("data").get("user_id")
        contactRes = db.getContactDetails(value, userId)

        return app.response_class(response=json.dumps({"status": "success", "error": None, "data": contactRes}), mimetype="application/json",), 200

    return app.response_class(response=json.dumps({"status": "unauthorized", "error": authResponse.get("error")}), mimetype="application/json",), 401


@app.route("/summary/<convoId>", methods=["GET"])
def summary(convoId):
    authResponse = authentication()
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        userId = authResponse.get("data").get("user_id")
        transRes = db.summarizeTransaction(convoId, userId)

        if not transRes.get("status"):
            return app.response_class(response=json.dumps({"status": "failure", "error": transRes.get("error"), "data": None}), mimetype="application/json",), 400

        return app.response_class(response=json.dumps({"status": "success", "error": None, "data": transRes.get("data")}), mimetype="application/json",), 401

    return app.response_class(response=json.dumps({"status": "unauthorized", "error": authResponse.get("error")}), mimetype="application/json",), 401


@socketio.on("join", namespace="/memo")
def joinRoom(data):
    print(request.sid)
    authResponse = authentication()
    print("authRes : ", authResponse)
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        convoId = data.get("conversation_id")
        userId = authResponse.get("data").get("user_id")
        join_room(userId, request.sid, namespace="/memo")
        if convoId is None:

            emit("join",
                 {
                     "status": "failure",
                     "error": "Invalid request",
                     "data": None
                 },
                 namespace="/memo", room=userId)

        else:

            userMemosRes = db.fetchUserMemos(userId, convoId)
            if userMemosRes.get("status"):

                emit("join", json.dumps(
                    {
                        "status": "success",
                        "error": None,
                        "data": userMemosRes.get("data")
                    }, default=json_util.default),
                    namespace="/memo", room=userId)

                join_room(convoId, request.sid, namespace="/memo")
            else:
                emit("join", json.dumps(
                    {
                        "status": "failure",
                        "error": userMemosRes.get("error"),
                        "data": userMemosRes.get("data")
                    }, default=json_util.default),
                    namespace="/memo", room=userId)

        close_room(userId, namespace="/memo")

    else:
        raise ConnectionRefusedError('unauthorized!')


@socketio.on("chat", namespace="/memo")
def chat(data):
    authResponse = authentication()
    print("authRes : ", authResponse)
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        memoType = data.get("memo_type")
        msgType = data.get("msg_type")
        transType = data.get("transaction_type")
        memo = data.get("memo")
        sentTime = datetime.now().timestamp()
        convoId = data.get("conversation_id")
        userId = authResponse.get("data").get("user_id")

        if None in [memoType, memo, convoId, userId]:
            join_room(userId, request.sid, namespace="/memo")
            emit("chat",
                 {
                     "status": "failure",
                     "error": "Invalid request",
                     "data": None
                 },
                 namespace="/memo", room=userId)
            close_room(userId, namespace="/memo")
        else:
            chatOrTransType = ""
            if memoType == "chat":
                chatOrTransType = msgType
            if memoType == "transaction":
                chatOrTransType = transType
            addMemoRes = db.addMemo(
                memoType, memo, sentTime, convoId, userId, chatOrTransType)
            if addMemoRes.get("status"):
                if memoType == "chat":
                    s = "message"

                if memoType == "transaction":
                    s = "amount"

                emit("chat",
                     json.dumps({
                         "status": "success",
                         "error": None,
                         "data": {
                             "_id": addMemoRes.get("data"), "memo_type":
                             memoType, "type": chatOrTransType, s: memo, "sent_time": sentTime,
                             "conversation_id": convoId, "sender_id": userId
                         }
                     }, default=json_util.default),
                     namespace="/memo", room=convoId)
            else:
                join_room(userId, request.sid, namespace="/memo")
                emit("chat",
                     json.dumps({
                         "status": "failure",
                         "error": addMemoRes.get("error"),
                         "data": None
                     }, default=json_util.default),
                     namespace="/memo", room=userId)
                close_room(userId, namespace="/memo")

    else:
        raise ConnectionRefusedError('unauthorized!')


@socketio.on("leave", namespace="/memo")
def leaveRoom(data):

    authResponse = authentication()
    print("authResLeave : ", authResponse)
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        convoId = data.get("conversation_id")
        userId = authResponse.get("data").get("user_id")

        if convoId is None:
            join_room(userId, request.sid, namespace="/memo")
            emit("leave",
                 {
                     "status": "failure",
                     "error": "Invalid request"
                 },
                 namespace="/memo", room=userId)
            close_room(userId, namespace="/memo")
        else:
            emit("leave",
                 {
                     "status": "success",
                     "error": None
                 },
                 namespace="/memo", room=userId)
            leave_room(convoId, request.sid, namespace="/memo")

    else:
        raise ConnectionRefusedError('unauthorized!')


if __name__ == '__main__':
    #context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    #context.load_cert_chain('domain.crt', 'domain.key')
    #app.run(port = 5000, debug = True, ssl_context = context)
    socketio.run(app, port=5002, debug=True)
    # app.run(port=5002, debug=True)
