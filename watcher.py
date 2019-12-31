import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import requests
import json


settings = json.loads( open("./settings.json", "r").read() )

PREFIX_API_PATH = settings['prefix_api_path']
DESTINATION_HOST = settings['destination']['host']
FOLDER_TO_WATCH = settings['watch_folder']

username_watcher = settings['username_api_token']
password_watcher = settings['password_api_token']
access_token = ""
refresh_token = ""

ADMIN_REPLICAS = DESTINATION_HOST+'/'+PREFIX_API_PATH

def get_access_token():
	global access_token, refresh_token
	print("Se obtendrá un nuevo token")
	data = {
		'username_inno_tok':username_watcher,
		'password_inno_tok':password_watcher
	}

	if access_token is None or access_token == "":
		r = requests.post(ADMIN_REPLICAS+"/auth", json=data)
		while(r is None or r.status_code != 200):
			r = requests.post(ADMIN_REPLICAS+"/auth", json=data)
			time.sleep(1)
		
		response = json.loads( r.text )
		# response['ok'] Si no existe o no se puede obtener, será None.
		if response.get('ok', None) == True: 
			token = response['access_token']
			refresh_token = response['refresh_token']
		
	return ( access_token, refresh_token )

def refresh_access_token():
	global access_token, refresh_token
	print("Se hará un refresh token")
	headersRefresh = {
		'Authorization':'Bearer '+refresh_token
	}
	r = requests.post(ADMIN_REPLICAS+"/refresh", headers=headersRefresh)
	while r.status_code != 200:
		r = requests.post(ADMIN_REPLICAS+"/refresh", headers=headersRefresh)
		time.sleep(1)
	
	response = json.loads( r.text )
	if response.get('ok', None) == True:
		token = response['access_token']
		refresh_token = response['refresh_token']
	
	return ( token, refresh_token )
	

def envia_archivo(event):
	global access_token, refresh_token

	access_token, refresh_token = get_access_token()

	headers = {
		'Authorization':'Bearer '+access_token
	}

	filename, ext = os.path.splitext(event.src_path)
	filename = f"{filename}{ext}"

	#Abre y prepara el archivo para enviarlo
	archivo_a_enviar = {'nuevo_archivo': open('./'+filename, 'rb')}

	#Intenta enviar el archivo con el token que se tiene actualmente.
	sent = requests.post(ADMIN_REPLICAS+"receive-files", files=archivo_a_enviar, headers=headers)
	response = json.loads(sent.text)
	while sent is None or sent.status_code == 422 or response.get('msg', None) == "Token has expired":
		access_token, refresh_token = refresh_access_token()
		headers = {
			'Authorization':'Bearer '+access_token
		}
		
		sent = requests.post(ADMIN_REPLICAS+"receive-files", files=archivo_a_enviar, headers=headers)
		time.sleep(1)
	
	response_sent = json.loads(sent.text)
	return response_sent['ok']

def elimina_archivo(event):
	global access_token, refresh_token

	access_token, refresh_token = get_access_token()
	token = access_token

	headers = {
		'Authorization':'Bearer '+token
	}

	filename, ext = os.path.splitext(event.src_path)
	filename = f"{filename}{ext}"

	archivo_a_eliminar = filename
	
	payload = {
		'archivo':archivo_a_eliminar
	}

	sent = requests.delete(ADMIN_REPLICAS+"receive-files", data=payload, headers=headers)
	response = json.loads(sent.text)
	while sent is None or sent.status_code == 422 or response.get('msg', None) == "Token has expired":
		access_token, refresh_token = refresh_access_token()
		token = access_token
		
		headers = {
			'Authorization':'Bearer '+token
		}
		
		sent = requests.delete(ADMIN_REPLICAS+"receive-files", data=payload, headers=headers)
	
	response_sent = json.loads(sent.text)
	return response_sent['ok']


class Observador(FileSystemEventHandler):
	def on_any_event(self, event):
		print("Got it! Evento: ", event.event_type)
		self.process(event)
		if event.event_type in ['modified','created']:
			envia_archivo(event)
		elif event.event_type == 'deleted':
			elimina_archivo(event)

	def process(self, event):
		filename, ext = os.path.splitext(event.src_path)
		filename = f"{filename}{ext}"
		print("El archivo nuevo/cambiado/eliminado fue:", filename)


event_handler = Observador()
observer = Observer()
observer.schedule(event_handler, path=FOLDER_TO_WATCH, recursive=False)
observer.start()

try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    observer.stop()
observer.join()