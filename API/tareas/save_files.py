import datetime
import threading

ALLOWED_EXTENSIONS = {'txt', 'json', 'jpg', 'jpeg', 'png', 'tiff', 'gif'}

def to_log(request, error_num, leyenda):
	hilo = threading.Thread(target=write_in_log, name="Escribe en log manual", args=(request, error_num, leyenda))
	hilo.start()

def write_in_log( request, error_num, leyenda ):
	hoy = datetime.datetime.now().strftime("%Y.%m.%d")
	log_manual = open( f"./logs/error_endpoints_{hoy}.log", "a+" )
	ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	cadena =  "{} | {} | {} | {} | {} |\n".format(ahora, request.method,request.host, error_num ,leyenda )
	log_manual.write(cadena)
	log_manual.close()

def allowed_file(filename):
	if '.' in filename:
		return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	else:
		if '' in ALLOWED_EXTENSIONS:
			return True
		


