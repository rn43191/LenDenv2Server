# import ssl
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv
from bson import json_util
from flask.helpers import send_from_directory, url_for

from db import addUser, getEmail, updateEmailVerification, getUser
import json
from auth import (
    authenticateUserCredentials,
    generateAccessToken,
    JWT_LIFE_SPAN,
    authentication,
    serializer,
    allowedFile
)
from werkzeug.utils import secure_filename
import os
from flask import Flask, request, render_template
from flask_mail import Mail, Message

app = Flask(__name__)
app.config.from_pyfile("config.cfg")
mail = Mail(app)
load_dotenv("../lenden.env")

@app.route("/signin", methods=["POST"])
def signIn():
    data = request.get_json()
    userId = data.get("user_id")
    password = data.get("password")

    if None in [userId, password]:
        return json.dumps({"error": "Invalid request", "status": "failure"}), 400

    authUserRes = authenticateUserCredentials(userId, password)
    if not authUserRes.get("status"):
        return json.dumps({"error": authUserRes.get("error"), "status": "unauthorized"}), 401

    access_token = generateAccessToken(userId)
    userDataRes = getUser(userId)
    if not userDataRes.get("status"):
        return app.response_class(response=json.dumps(
            {
                "status": "failure",
                "error": userDataRes.get("error")
            }),
            mimetype="application/json"), 400

    userData = userDataRes.get("data")
    userData.update(
        {
            "access_token": access_token,
            "token_type": "JWT",
            "expires_in": JWT_LIFE_SPAN,
        })

    return (
        app.response_class(
            response=json.dumps(
                {
                    "status": "success",
                    "error": None,
                    "data": userData

                }, default=json_util.default
            ),
            mimetype="application/json",

        ),
        200,
    )


@app.route("/signup", methods=["POST"])
def signUp():
    try:
        
        if "json" not in request.form.keys() or "image_data" not in request.files.keys():
            return (
                app.response_class(
                    response=json.dumps(
                        {
                            "error": "Server cannot understand the request",
                            "status": "failure",
                            "data": None
                        }
                    ),
                    mimetype="application/json",
                ),
                400,
            )

        data = json.loads(request.form.get("json"))
        userId = data.get("user_id")
        password = data.get("password")
        email = data.get("email")
        firstName = data.get("first_name")
        lastName = data.get("last_name")
        phoneNo = data.get("phone")
        image = request.files.get("image_data")

        if None in [userId, password, email, firstName, lastName]:
            return (
                app.response_class(
                    response=json.dumps(
                        {
                            "error": "Invalid Request",
                            "status": "failure",
                            "data": None
                        }
                    ),
                    mimetype="application/json",
                ),
                400,
            )

        allFileRes={"status":True,"error":None}
        imageUrl=""
        if image.filename!="":
            filename=secure_filename(image.filename)
            allFileRes=allowedFile(filename)

            if not allFileRes.get("status"):
                return app.response_class(
                    response=json.dumps(
                        {
                            "error": "Filetype not allowed",
                            "status": "failure",
                            "data": None
                        }
                    ),
                    mimetype="application/json",
                ), 400

        else: imageUrl=None
        
        ext=allFileRes.get("data")
        imageUrl = url_for(
                'getUserImage', filename=f"{userId}.{ext}",_external=True)
        
        addUserRes = addUser(userId, password, email,
                             firstName, lastName, phoneNo,imageUrl)
        if addUserRes.get("status") is not True:
            error = addUserRes.get("error")
            return (
                app.response_class(
                    response=json.dumps(
                        {"error": error, "data": None, "status": "failure"}
                    ),
                    mimetype="application/json",
                ),
                409,
            )
        
        emailToken = serializer.dumps(
            email, salt='auth-server-email-verification')
        link = url_for("verifyEmail", token=emailToken, _external=True)

        mail.send(Message(subject="LenDen-Confirm Email",
                  recipients=[email],
                  html=render_template("verificationMailTemplate.html", link=link,)))
            
   
        image.save(os.path.join(
            app.config['UPLOAD_FOLDER'], f"{userId}.{ext}"))
        

        pilIMg=Image.open(os.path.join(
                app.config['UPLOAD_FOLDER'], f"{userId}.{ext}"))
        pilIMg.resize((200,200))
        pilIMg.save(os.path.join(os.getenv("CACHE_FOLDER"),f"{userId}.{ext}"),quality=10,optimize=True)
        image.close()
        pilIMg.close()
        
        access_token = generateAccessToken(userId)

        return (
            app.response_class(
                response=json.dumps(
                    {
                        "error": None,
                        "status": "success",
                        "data": {
                            "_id": userId,
                            "email": email,
                            "first_name": firstName,
                            "last_name": lastName,
                            "phone": phoneNo,
                            "created_at": datetime.now().timestamp(),
                            "access_token": access_token,
                            "token_type": "JWT",
                            "expires_in": JWT_LIFE_SPAN,
                            "image_url": imageUrl,
                            "email_verified":False
                        }
                    }, default=json_util.default),
                mimetype="application/json",
            ),
            200
        )
    except Exception as e:
        return (
            app.response_class(
                response=json.dumps(
                    {
                        "error": e.__str__(),
                        "status": "failure",
                        "data": None
                    }
                ),
                mimetype="application/json",
            ),
            400,
        )


@app.route("/verify/email", methods=["GET"])
def sendEmail():
    authResponse = authentication()
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:

        userId = authResponse.get("data").get("user_id")
        emailRes = getEmail(userId)
        if not emailRes.get("status"):
            return app.response_class(response=json.dumps(
                {"status": "failure", "error": emailRes.get("error"), "msg": None}),
                mimetype="application/json",), 400

        if emailRes.get("data").get("email_verified"):
            return app.response_class(response=json.dumps(
                {"status": "failure", "error": None, "msg": "Email already verified"}),
                mimetype="application/json",), 200

        email = emailRes.get("data").get("email")
        emailToken = serializer.dumps(
            email, salt='auth-server-email-verification')
        link = url_for("verifyEmail", token=emailToken, _external=True)

        mail.send(Message(subject="LenDen-Confirm Email",
                  recipients=[email],
                  html=render_template("verificationMailTemplate.html", link=link,)))

        return app.response_class(response=json.dumps(
            {"status": "success", "error": None, "msg": f'Verifcation mail sent to {email}'}),
            mimetype="application/json",), 200

    return app.response_class(response=json.dumps({"status": "unauthorized", "error": authResponse.get("error")}), mimetype="application/json",), 401


@app.route("/verify/email/<token>", methods=["GET"])
def verifyEmail(token):
    try:
        email = serializer.loads(
            token, salt='auth-server-email-verification', max_age=600)
        updateEmailRes = updateEmailVerification(email)
        if not updateEmailRes.get("status"):
            return render_template("errorTemplate.html", status="failure", error=updateEmailRes.get("error")), 400
        return render_template("afterVerifiedTemplate.html", userId=updateEmailRes.get("data").get("_id"), email=email), 200
    except Exception as e:
        return render_template("errorTemplate.html", status="unauthorized", error=e.__str__()), 401


@app.route("/reset",methods={"POST"})
def resetPassword():
    pass


@app.route("/logout", methods=["GET"])
def logout():
    pass


@app.route("/user", methods=["GET"])
def user():
    authResponse = authentication()
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        userId = authResponse.get("data").get("user_id")
        userDataRes = getUser(userId)
        if not userDataRes.get("status"):
            return app.response_class(response=json.dumps(
                {
                    "status": "failure",
                    "error": userDataRes.get("error"),

                }),
                mimetype="application/json"), 400

        userData = userDataRes.get("data")
        userData.update({
            "access_token": request.headers.get("Authorization").split(" ")[1],
            "token_type": "JWT",
            "expires_in": JWT_LIFE_SPAN,
        })

        return app.response_class(response=json.dumps(
            {
                "status": "success",
                "error": None,
                "data": userData,
            },
            default=json_util.default), mimetype="application/json"), authResponse["statusCode"]

    return app.response_class(response=json.dumps(
        {
            "status": "unauthorized",
            "data": None,
            "error": authResponse["error"]},
        default=json_util.default), mimetype="application/json"), authResponse["statusCode"]


@app.route("/verify/token", methods=["GET"])
def verifyToken():
    authResponse = authentication()
    if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
        return app.response_class(response=json.dumps({"status": "success", "error": None}), mimetype="application/json"), 200
    if authResponse["statusCode"] == 400 and not authResponse["isVerified"]:
        return app.response_class(response=json.dumps(
            {
                "status": "failure",
                "error": authResponse.get("error")
            }), mimetype="application/json"), 400

    return app.response_class(response=json.dumps(
        {
            "status": "unauthorized",
            "error": authResponse.get("error")
        }), mimetype="application/json"), authResponse.get("statusCode")


@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "image" not in request.files.keys() or "json" not in request.form.keys():
            return "bad request", 400
        image = request.files['image']
        print(request.form.get("json"))
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        return json.dumps({"image": image.filename, "json": request.form.get("json")}, default=json_util.default)
    except Exception as e:
        return e.__str__(), 400


@app.route("/user/profile_pic/<filename>", methods=["GET"])
def getUserImage(filename):
    authResponse = authentication()
    try:
        small=request.args.get('small',default=1,type=int)
        if authResponse["statusCode"] == 200 and authResponse["isVerified"]:
            if small==1:
                readFolderPath=os.getenv('CACHE_FOLDER')
            else:
                readFolderPath=app.config['UPLOAD_FOLDER']
            return send_from_directory(os.path.join(os.getcwd(),readFolderPath), filename)
    
        return app.response_class(response=json.dumps(
            {
                "status": "unauthorized",
                "error": authResponse.get("error")
            }), mimetype="application/json"), authResponse.get("statusCode")

    except Exception as e:
        return app.response_class(response=json.dumps(
            {
                "status": "failure",
                "error": e.__str__()
            }), mimetype="application/json"), 400

if __name__ == "__main__":
    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # context.load_cert_chain('domain.crt', 'domain.key')
    # app.run(port = 5000, debug = True, ssl_context = context)
    app.run(port=5001, debug=True)
