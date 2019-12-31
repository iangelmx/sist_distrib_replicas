# -*- coding: utf-8 -*-
import flask
import json
import sys
import pdfkit
import os
import ssl

from werkzeug.utils import secure_filename
from flask_jwt_extended import (
	JWTManager, jwt_required, create_access_token,
	get_jwt_identity, create_refresh_token,jwt_refresh_token_required, get_jwt_claims
)
from flask import Flask, jsonify, send_file, request, render_template
from flask import render_template_string, make_response, send_from_directory, redirect
from flask_cors import CORS, cross_origin

from tareas.web_tokens import get_secret_key, valida_credenciales_token
from tareas.save_files import allowed_file

#Carga ajustes de entorno
settings = json.loads( open("./settings.json", "r").read() )

#Setea certificados de seguridad SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
###context.load_cert_chain( settings['wildcard'], settings['private_key'])

#Donde se guardarán de forma predeterminada los archivos
#Debe ser en rutas donde www-data tenga acceso
UPLOAD_FOLDER = settings['destination']['folder']
SECRET_KEY = settings['secret_key']
PREFIX_API_PATH = settings['prefix_api_path']

# Setup the Flask-JWT-Extended extension
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = SECRET_KEY
app.config['JWT_SECRET_KEY'] = get_secret_key() 
jwt = JWTManager(app)
CORS(app)

''' -------------------------------------------------------------------------------------- '''
''' ------------------------------------ NO TOCAR:  ------------------------------------'''
#Permite la comunicación entre distintos dominios
@app.after_request
def after_request(response):
  #response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,From,forceToDo,Auth')
  response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
  return response

@app.route('/flask/favicon.ico')
def favicon():
	return send_from_directory(os.path.join(app.root_path, 'static'),
								'favicon.ico', mimetype='image/vnd.microsoft.icon')

def validaOrigen(request, sitiosPermitidos):
	#Valida que se estén haciendo peticiones desde sitios de confianza
	for a in request.environ:
		pass#print(a,":",request.environ[a])
	if 'HTTP_ORIGIN' in request.environ:
		if request.environ['HTTP_ORIGIN'] in sitiosPermitidos:
			return True
	elif 'HTTP_FROM' in request.environ:
		if request.environ['HTTP_FROM'] in sitiosPermitidos:
			return True
	elif 'HTTP_REFERER' in request.environ:
		if request.environ['HTTP_REFERER'] in sitiosPermitidos:
			return True
	return False

# Provide a method to create access tokens. The create_access_token()
# function is used to actually generate the token, and you can return
# it to the caller however you choose.
@app.route(PREFIX_API_PATH+'/auth', methods=['POST'])
def login_with_tokens():
	peticion = request
	if not peticion.is_json:
		return jsonify({"ok":False,"msg": "Missing JSON in request"}), 400
	
	json_req = peticion.json

	username = json_req.get('username_inno_tok', None)
	password = json_req.get('password_inno_tok', None)
	platform = json_req.get('platform_inno_tok', None)
	
	if not username:
		return jsonify({"ok":False,"msg": "Missing or bad username parameter"}), 400
	if not password:
		return jsonify({"ok":False,"msg": "Missing or bad password parameter"}), 400
	if not platform:
		return jsonify({"ok":False,"msg": "Missing or bad platform parameter"}), 400

	result = valida_credenciales_token(username, password, platform)
	
	if result['ok'] != True:
		return jsonify({"ok":False,"msg": "Bad credentials for specified platform (username or password)"}), 401

	# Identity can be any data that is json serializable
	# Use create_access_token() and create_refresh_token() to create our
	# access and refresh tokens
	ret = {
		'ok': True,
		'access_token': create_access_token(identity=username, user_claims={'rol':result['claim']}),
		'refresh_token': create_refresh_token(identity=username)
	}
	return jsonify(ret), 200

# The jwt_refresh_token_required decorator insures a valid refresh
# token is present in the request before calling this endpoint. We
# can use the get_jwt_identity() function to get the identity of
# the refresh token, and use the create_access_token() function again
# to make a new access token for this identity.
@app.route(PREFIX_API_PATH+'/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
	current_user = get_jwt_identity()
	ret = {
		'access_token': create_access_token(identity=current_user)
	}
	return jsonify(ret), 200

# Protect a view with jwt_required, which requires a valid access token
# in the request to access.
@app.route(PREFIX_API_PATH+'/protected', methods=['GET'])
@jwt_required
def protected():
	# Access the identity of the current user with get_jwt_identity
	current_user = get_jwt_identity()
	claims = get_jwt_claims()
	if claims['rol'] not in ['no-access']:
		return flask.abort(403)
	print(claims)
	return jsonify(logged_in_as=current_user), 200


@app.errorhandler(404)
def not_found(error):
	return render_template('/ErrorPages/40X.html', number_err=404, label_err="Not Found", text_error="El recurso solicitado no se ha encontrado."),404
@app.errorhandler(403)
def forbidden(error):
	return render_template('/ErrorPages/40X.html', number_err=403, label_err="Forbidden", text_error="Acceso prohibido."),403
@app.errorhandler(405)
def method_not_allowed(error):
	return render_template('/ErrorPages/40X.html', number_err=405, label_err="Method Not Allowed", text_error="La ruta estipulada no tolera el método solicitado."),405
@app.errorhandler(410)
def gone(error):
	return render_template('/ErrorPages/40X.html', number_err=410, label_err="Gone", text_error="El recurso solicitado ya no existe."),410
@app.errorhandler(500)
def intServErr(error):
	return render_template('./ErrorPages/500.html',errorInfo=error),500


''' ------------------------------------ Fin NO TOCAR ------------------------------------ '''
''' -------------------------------------------------------------------------------------- '''


''' ----------------- Endpoints ----------------- '''

@app.route(PREFIX_API_PATH+"/receive-files", methods=['POST', 'PUT', 'DELETE'])
@jwt_required
def receive_files():
	#Declaramos los claims que no podrán ejecutar el procedimiento del endpoint
	claims_no_permitidos = [ 'no-access', 'no-execution', 'only-view' ]
	#Obtenemos los claims el Web token de la petición
	claims = get_jwt_claims()
	#Se valida si el claim de la petición no está en la lista de los que se excluirán
	if claims['rol'] in claims_no_permitidos:
		#Interrumpe la petición y regresa un error 403
		return flask.abort(403)

	#Se hizo la distinción de los métodos:
	# POST	 -> Crea un recurso en el server
	# PUT	 -> Actualiza un recurso en el server
	# DELETE -> Elimina un recurso del servidor
	
	if request.method in ['POST', 'PUT']:
		archivo = request.files.get('nuevo_archivo')
		if archivo and allowed_file(archivo.filename):
			filename = secure_filename(archivo.filename)
			try:
				archivo.save(os.path.join( UPLOAD_FOLDER , filename))
				return jsonify(ok=True, description="File saved")
			except Exception as ex:
				return jsonify(ok=False, description={"error":str(ex), "details":"Exception while saving file"})
		else:
			return jsonify(ok=False, description={"Missing file to upload"})
	elif request.method == 'DELETE':
		try:
			os.remove(os.path.join( UPLOAD_FOLDER , filename))
			return jsonify(ok=True, description="File removed")
		except Exception as ex:
				return jsonify(ok=False, description={"error":str(ex), "details":"Exception while deleting file"})


if __name__ == '__main__':
	app.run(debug=True, use_reloader=False, port=90)