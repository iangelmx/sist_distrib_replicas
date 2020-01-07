import random
import json
from libs.sqlBd import Bd
from libs.hashing import Hasher

alfabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz01234567890@#$_.*?=&%:<>+-[]"
settings = json.loads( open("settings_endpoints.json", "r").read() )

def connectDB():
	db_data= settings['databases']['tokens']
	#La conexión conla BD
	return Bd(	
		hostname = db_data['host'],
		username = db_data['username'],
		password = db_data['password'],
		database = db_data['db_name']
	)


def get_secret_key():
	shuffled = list(alfabet)
	random.shuffle(shuffled)
	shuffled = ''.join(shuffled)[10:-9]
	print("Secret Key:\n",shuffled)
	return shuffled

def valida_credenciales_token(usuario, password, plataforma):
	bd = connectDB()
	queryUsers = """
	SELECT a.email AS email, password, id_platform, nivel_acceso 
	FROM permiso_accesos a
	INNER JOIN usuarios u
		ON u.email = a.email
	INNER JOIN plataformas p
		ON a.id_platform  = p.id
	WHERE a.status = 'activo' AND p.nombre = '{}' AND
			u.status_account = 'activo' AND a.email = '{}' AND
			a.fecha_expiracion >= CURRENT_DATE();""".format(
				plataforma, usuario
			)
	#print("Query armada:", queryUsers)
	result = bd.doQuery( queryUsers	, returnAsDict=True)

	respuesta = {'ok':False, 'claim':'no-access'}

	#print("Resultado de BD:", result)

	if len(result)>0:
		result = result[0]
		hash_obj = Hasher('sha512')
		if hash_obj.matchString(result['password'], password) == True:
			respuesta['ok'] = True
			respuesta['claim'] = result['nivel_acceso']
			return respuesta
		return respuesta
	return respuesta