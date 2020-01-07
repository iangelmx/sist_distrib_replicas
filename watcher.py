import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.events import *
import os
import requests
import json


settings = json.loads( open("./settings_watcher.json", "r").read() )

PREFIX_API_PATH = settings['prefix_api_path']
DESTINATION_HOST = settings['destination']['host']
FOLDER_TO_WATCH = settings['watch_folder']
OS_DESTINATION = settings['destination']['os']
PLATFORM_TO_WATCH = settings['platform_to_watch']

username_watcher = settings['username_api_token']
password_watcher = settings['password_api_token']
platform_destina = PLATFORM_TO_WATCH
access_token = ""
refresh_token = ""

ADMIN_REPLICAS = DESTINATION_HOST+PREFIX_API_PATH

def get_access_token():
	global access_token, refresh_token
	print("Se obtendrá un nuevo token")
	data = {
		'username_inno_tok':username_watcher,
		'password_inno_tok':password_watcher,
		'platform_inno_tok':platform_destina
	}

	if access_token is None or access_token == "":
		r = requests.post(ADMIN_REPLICAS+"/auth", json=data)
		print(r.text)
		while(r is None or r.status_code != 200):
			r = requests.post(ADMIN_REPLICAS+"/auth", json=data)
			print(r.text)
			time.sleep(5)
		
		response = json.loads( r.text )
		# response['ok'] Si no existe o no se puede obtener, será None.
		if response.get('ok', None) == True: 
			token = response['access_token']
			access_token = token
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

	filename, ext= os.path.splitext(event.src_path)
	ruta_relativa = filename.split(FOLDER_TO_WATCH)[1]
	
	filename = os.path.basename(event.src_path)

	ruta_relativa = f"{ruta_relativa}{ext}".replace(filename,"")
	print("Ruta relativa al archivo:"+ruta_relativa+"<")

	filename = os.path.basename(event.src_path)
	

	#Abre y prepara el archivo para enviarlo
	archivo_a_enviar = None
	while archivo_a_enviar is None:
		try:
			archivo_a_enviar = {'nuevo_archivo': open( os.path.join(FOLDER_TO_WATCH,ruta_relativa,filename) , 'rb')}
		except Exception as ex:
			print("Excepción en envia archivo; al abrir el archivo que se va a enviar:", ex)
			time.sleep(2)

	payload = {
		'destination_platf' : PLATFORM_TO_WATCH,
		'os' : OS_DESTINATION,
		'relative_path' : ruta_relativa
	}

	#Intenta enviar el archivo con el token que se tiene actualmente.
	sent = requests.post(ADMIN_REPLICAS+"/receive-files", files=archivo_a_enviar, headers=headers, data=payload)
	print(sent.text)
	response = json.loads(sent.text)
	while sent is None or sent.status_code == 422 or response.get('msg', None) == "Token has expired":
		access_token, refresh_token = refresh_access_token()
		headers = {
			'Authorization':'Bearer '+access_token
		}
		
		sent = requests.post(ADMIN_REPLICAS+"/receive-files", files=archivo_a_enviar, headers=headers, data=payload)
		time.sleep(1)
	print(sent.text)
	response_sent = json.loads(sent.text)
	return response_sent['ok']

def elimina_archivo(event):
	global access_token, refresh_token

	access_token, refresh_token = get_access_token()
	token = access_token

	headers = {
		'Authorization':'Bearer '+token
	}

	filename = os.path.basename(event.src_path)

	archivo_a_eliminar = filename
	
	payload = {
		'archivo':archivo_a_eliminar
	}

	sent = requests.delete(ADMIN_REPLICAS+"/receive-files", json=payload, headers=headers)
	response = json.loads(sent.text)
	while sent is None or sent.status_code == 422 or response.get('msg', None) == "Token has expired":
		access_token, refresh_token = refresh_access_token()
		token = access_token
		
		headers = {
			'Authorization':'Bearer '+token
		}
		
		sent = requests.delete(ADMIN_REPLICAS+"/receive-files", data=payload, headers=headers)
	
	response_sent = json.loads(sent.text)
	print(sent.text)
	return response_sent['ok']


class Observador(PatternMatchingEventHandler):
	def __init__(self, patterns=None, ignore_patterns=None, ignore_directories=False, case_sensitive=False):
	 super().__init__(patterns=patterns, ignore_patterns=ignore_patterns, ignore_directories=ignore_directories, case_sensitive=case_sensitive)

	def on_any_event(self, event):
		print("Got it! Evento: ", event.event_type)
		self.process(event)
		
		if event.event_type in ['modified','created']:
			print("Archivo enviado:", envia_archivo(event))
		elif event.event_type == 'deleted':
			print("Archivo eliminado:", elimina_archivo(event))

	def process(self, event):
		filename, ext = os.path.splitext(event.src_path)
		filename = f"{filename}{ext}"
		print("El archivo nuevo/cambiado/eliminado fue:", filename)


event_handler = Observador(ignore_directories=True)
observer = Observer()
observer.schedule(event_handler, path=FOLDER_TO_WATCH, recursive=True)
observer.start()

while True:
	try:
		while True:
			time.sleep(10)
			print("Esperará 10 segs")
	except Exception as ex:
		observer.stop()
		event_handler = Observador()
		observer = Observer()
		observer.schedule(event_handler, path=FOLDER_TO_WATCH, recursive=False)
		observer.start()
		print("Reinició el observador...")
	observer.join()