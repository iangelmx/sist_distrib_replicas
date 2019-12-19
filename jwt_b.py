from flask import Flask, jsonify, request
from tareas.web_tokens import get_secret_key, valida_credenciales_token

from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, create_refresh_token,jwt_refresh_token_required
)

app = Flask(__name__)

# Setup the Flask-JWT-Extended extension
app.config['JWT_SECRET_KEY'] = get_secret_key() 
jwt = JWTManager(app)


# Provide a method to create access tokens. The create_access_token()
# function is used to actually generate the token, and you can return
# it to the caller however you choose.
@app.route('/auth', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"ok":False,"msg": "Missing JSON in request"}), 400

    username = request.json.get('username_inno_tok', None)
    password = request.json.get('password_inno_tok', None)
    if not username:
        return jsonify({"ok":False,"msg": "Missing or bad username parameter"}), 400
    if not password:
        return jsonify({"ok":False,"msg": "Missing or bad password parameter"}), 400

    result = valida_credenciales_token(username, password)

    if result != True:
        return jsonify({"ok":False,"msg": "Bad username or password"}), 401

    # Identity can be any data that is json serializable
    # Use create_access_token() and create_refresh_token() to create our
    # access and refresh tokens
    ret = {
        'ok': True,
        'access_token': create_access_token(identity=username),
        'refresh_token': create_refresh_token(identity=username)
    }
    return jsonify(ret), 200

# The jwt_refresh_token_required decorator insures a valid refresh
# token is present in the request before calling this endpoint. We
# can use the get_jwt_identity() function to get the identity of
# the refresh token, and use the create_access_token() function again
# to make a new access token for this identity.
@app.route('/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
    current_user = get_jwt_identity()
    ret = {
        'access_token': create_access_token(identity=current_user)
    }
    return jsonify(ret), 200

# Protect a view with jwt_required, which requires a valid access token
# in the request to access.
@app.route('/protected', methods=['GET'])
@jwt_required
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200


if __name__ == '__main__':
    print("Key a punto de correr:", app.config['JWT_SECRET_KEY'])
    app.run(debug=True,use_reloader=False)