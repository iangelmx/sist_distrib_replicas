# -*- coding: utf-8 -*-
from flask import Flask, jsonify, send_file, request, render_template
from flask import render_template_string, make_response, send_from_directory, redirect
from flask_cors import CORS, cross_origin
import flask
import json
import sys
import pdfkit
import os
import ssl

#Carga ajustes de entorno
settings = json.loads( open("./settings.json", "r").read() )

#Setea certificados de seguridad SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain( settings['wildcard'], settings['private_key'])

#Donde se guardarán de forma predeterminada los archivos
#Debe ser en rutas donde www-data tenga acceso
UPLOAD_FOLDER = settings['default_upload_folder']
SECRET_KEY = settings['secret_key']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)

''' NO TOCAR:  '''
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

''' ----------------- Endpoints ----------------- '''

@app.route("/api/replicas/v1.0/receive-files")
def receive_files():
    #Verificar token hashee la frase secreta de cabecera
    #Obtener el archivo de la petición
    #Verificar que el archivo tenga un nombre valido
    #Guardar/sobreescribir archivo en ruta definida
    pass

