# -*- coding: utf-8 -*-
import flask
import json
import sys
import os
import ssl
import datetime
import threading

from werkzeug.utils import secure_filename
from flask_jwt_extended import (
	JWTManager, jwt_required, create_access_token,
	get_jwt_identity, create_refresh_token,jwt_refresh_token_required, get_jwt_claims
)
from flask import Flask, jsonify, send_file, request, render_template
from flask import render_template_string, make_response, send_from_directory, redirect
from flask_cors import CORS, cross_origin
from logging.config import dictConfig

from tareas.web_tokens import get_secret_key, valida_credenciales_token
from tareas.save_files import *

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

#Carga ajustes de entorno
settings = json.loads( open("./settings_endpoints.json", "r").read() )

#Setea certificados de seguridad SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
###context.load_cert_chain( settings['wildcard'], settings['private_key'])

#Donde se guardarán de forma predeterminada los archivos
#Debe ser en rutas donde www-data tenga acceso
UPLOAD_FOLDER = settings['default_upload_folder']
print("El upload folder es:", UPLOAD_FOLDER)
SECRET_KEY = settings['secret_key']
PREFIX_API_PATH = settings['prefix_api_path']

ALLOWED_DIRECTORIES = settings['allowed_directories']

# Setup the Flask-JWT-Extended extension
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = settings['max_file_size_to_receive_MB'] * 1024 * 1024
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
		error_dict = {"ok":False,"msg": "Missing JSON in request"}
		to_log( request, 400, "Missing JSON in request" )
		return jsonify(error_dict), 400
	
	json_req = peticion.json

	username = json_req.get('username_inno_tok', None)
	password = json_req.get('password_inno_tok', None)
	platform = json_req.get('platform_inno_tok', None)
	
	if not username:
		to_log( request, 400, "Missing or bad username parameter" )
		return jsonify({"ok":False,"msg": "Missing or bad username parameter"}), 400
	if not password:
		to_log( request, 400, "Missing or bad password parameter" )
		return jsonify({"ok":False,"msg": "Missing or bad password parameter"}), 400
	if not platform:
		to_log( request, 400, "Missing or bad platform parameter" )
		return jsonify({"ok":False,"msg": "Missing or bad platform parameter"}), 400

	result = valida_credenciales_token(username, password, platform)
	
	if result['ok'] != True:
		to_log( request, 401, "Bad credentials for specified platform (username or password)" )
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
	if claims['rol'] in ['no-access']:
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
		to_log( request, 403, "claim no permitido:"+str( claims['rol'] ) )
		return flask.abort(403)
	
	destination_platf = request.form.get('destination_path', None)
	destination_os = request.form.get('os', None)
	relative_path = request.form.get('relative_path', None)
	
	if destination_platf is None or destination_os is None or relative_path is None:
		desc ={ 'details':"Missing upload application details", 'error':"Destination values (DestP, Os, rel path): {}".format(request.json) }
		app.logger.info('%s ERROR', desc)
		to_log(request,400, desc)
		return jsonify(ok=False, description=desc), 400
	
	#Se obtiene la raíz del directorio en donde se harán las réplicas.
	root_directory = ALLOWED_DIRECTORIES.get( destination_platf, '' ).get( destination_os, "" )
	# Si no se puede obtener, la guarda en la ruta predeterminada de Flask. Esta ruta está indicada en el
	# archivo settings_endpoints.json -> 'default_upload_folder'
	if root_directory == "" : root_directory = UPLOAD_FOLDER

	#Se concatena la ruta relativa a partir de la raíz.
	destination_dir= os.path.join( root_directory, relative_path )

	#Se hizo la distinción de los métodos:
	# POST	 -> Crea un recurso en el server
	# PUT	 -> Actualiza un recurso en el server
	# DELETE -> Elimina un recurso del servidor
	
	if request.method in ['POST', 'PUT']:
		archivo = request.files.get('nuevo_archivo', None)
		
		#Validamos que la extensión del archivo esté tolerada por la API
		if archivo is not None and allowed_file(archivo.filename):
			filename = secure_filename(archivo.filename)
			try:
				archivo.save(os.path.join( destination_dir , filename))
				to_log(request, 200, f"{os.path.join( destination_dir , filename)} File saved", "success")
				return jsonify(ok=True, description="File saved")
			except Exception as ex:
				#Si se llega a una excepción, probablemente es porque no existían los directorios en donde se está
				#queriendo guardar el archivo. Este bloque trata de construir el árbol de directorios
				try:
					#Se obtiene en una lista los directorios que se tienen que construir a partir del raíz
					rutas_relativas = relative_path.split("\\")
					#Se mueve la consola del sistema al directorio raíz de subida
					os.chdir("{}".format( root_directory ))

					for directorio in rutas_relativas:
						if directorio in ["", " "]:
							continue
						#print("Contruyendo directorio:", directorio)
						result = os.system(f"mkdir {directorio}") #Si result == 1 -> Ya exitía el directorio
						os.chdir(f"{directorio}") #Entramos en el directorio que acabamos de crear
					#Tratamos finalmente de guardar el archivo
					archivo.save(os.path.join( destination_dir , filename))


					#Si todo sale bien, se regresaría un resultado de éxito, sino, imprime la excepción
					#en consola y regresa el json con la excepción inicial
					return jsonify(ok=True, description="File saved") 
				except Exception as ix:
					print("Eso no lo arregló... :v ->", ix)

				error_dict = {"error":str(ex), "details":"Exception while saving file"}
				to_log(request, 500, desc)
				return jsonify(ok=False, description=error_dict), 500
		else:
			#La API no tolera ese tipo de archivos y regresa el error
			try:
				filename = archivo.filename
			except:
				filename = None
			error_dict={'ok':False, 'description':{'details':"Missing file to upload or extension not allowed", 'error':{'archivo':filename, 'allowed_file':allowed_file(str(filename))} } }
			app.logger.info('%s Error al subir archivo', error_dict)
			to_log(request, 400, error_dict)
			return jsonify(error_dict), 400
	elif request.method == 'DELETE':
		archivo = request.form.get('archivo', None)

		if archivo is not None:
			try:
				os.remove(os.path.join( destination_dir , archivo))
				return jsonify(ok=True, description="File removed")
			except Exception as ex:
				error_dict = {"error":str(ex), "details":"Exception while deleting file"}
				to_log(request, 500, error_dict)
				return jsonify(ok=False, description=error_dict), 500
		else:
			error_dict = {'details':'Bad request', 'error':'File not found in request'}
			to_log(request, 400, error_dict)
			return jsonify(ok=False, description=error_dict), 400


if __name__ == '__main__':
	import logging
	logging.basicConfig(filename="./logs/general.log", level=logging.DEBUG)
	app.run(debug=True, use_reloader=False, port=90)