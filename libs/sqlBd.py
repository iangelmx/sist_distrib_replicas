import pymysql

class Bd():

	#Base de datos
	hostname = 'localhost'
	username = 'root'
	password = ''
	database = None

	def __init__(self,database, hostname='localhost', username='root', password=''):
		self.hostname=hostname
		self.username=username
		self.password=password
		self.database=database

	def getAutoIncrement(self, table):
		return self.doQuery('''SELECT `AUTO_INCREMENT`
								FROM  INFORMATION_SCHEMA.TABLES
								WHERE TABLE_SCHEMA = '{}'
								AND   TABLE_NAME   = '{}';'''.format(self.database,table))[0][0]
		
	def insertInDB(self, table, params):#Inserta un nuevo elemento en la BD, los parametros van en forma de lista al igua que los valores regra
		
		myConnection =pymysql.connect( host=self.hostname, user=self.username, passwd=self.password, db=self.database )	#Crear la conexión con la BD
		cur = myConnection.cursor()
		myQuery=self.getInsertQuery(table, params)
		
		cur.execute( myQuery )
		myConnection.commit()
		result=cur.fetchall()
		myConnection.close()
		return True #MEJORA ISSSUE 13
	def insertMany(self, table, inserts):
		#Obtener la query de cada i
		print("----------------*******************----------------")
		queries=[]
		for i in inserts:
			queries.append(self.getInsertQuery(table, i))
		#Mandara realizar todas las transacciones
		#return {'length':len(queries), 'trans':queries}
		return self.doTransaction(queries)

	def getInsertQuery(self, table, params):
		myQuery="INSERT INTO "+table+" ( "
		for key in params:#Agregar la lista de parámetros separada por comas
			myQuery+=key +","
		myQuery = myQuery[:-1] + ") VALUES (" #Quitar la última coma y preparar para los parámetros

		for key in params: #Agregar el listado de valores
			if params[key] is not None:
				myQuery+=" "+self.escapeString(params[key])+","
			else: myQuery+=' NULL ,'
		myQuery = myQuery[:-1] + ");" #Quitar la última coma y preparar para los parámetros
		return myQuery
		
	def updateInDB(self, table,upParams, whereParams=None, limit = None):
		reserved=['=NULL','NOW()']

		myConnection =pymysql.connect( host=self.hostname, user=self.username, passwd=self.password, db=self.database )	#Crear la conexión con la BD
		cur = myConnection.cursor()
		myQuery="UPDATE "+table+" SET "
		for key in upParams:#Agregar la lista de cambios separados por comas
			
			if str(upParams[key]) in reserved:
				myQuery+=key+upParams[key]
			else:
				if upParams[key] is not None:
					myQuery+=key+"="+self.escapeString(upParams[key])+","
				else:
					myQuery+=key+"= NULL,"
		myQuery = myQuery[:-1] #Quitar la última coma

		if whereParams:
			myQuery += " WHERE "
			for key in whereParams:#Agregar la lista de parámetros separada por comas
				
				myQuery+=key+"="+self.escapeString(whereParams[key])+" AND "
			myQuery = myQuery[:-5] #Quitar la última coma y preparar para los parámetros
		
		if limit is not None:
			myQuery += " LIMIT {}".format(limit)
		
		myQuery += " ;" 


		#print("Query de actuailzacion armada:",myQuery)



		cur.execute( myQuery )
		myConnection.commit()
		
		result=cur.fetchall()

		myConnection.close()

		return True #MEJORA ISSSUE 14	
	def doQuery(self,  myQuery, returnAsDict=False) :
		myConnection =pymysql.connect( host=self.hostname, user=self.username, passwd=self.password, db=self.database, charset='utf8' )	#Crear la conexión con la BD
		if returnAsDict == True:
			cur = pymysql.cursors.DictCursor( myConnection )
		else:
			cur = myConnection.cursor()
		#input(myQuery)
		try:
			cur.execute( myQuery )	
			result=cur.fetchall()
			myConnection.commit()
			myConnection.close()
			return result
		except:
			cur.execute( myQuery.replace("''","'") )	
			result=cur.fetchall()
			myConnection.commit()
			myConnection.close()
			return result
	def existsInDB(self, table,params):#Checa si existe un elemento con un valor value en un parametro param dentro de la tabla table. Si existr rgresa True, sino False
	    query="SELECT COUNT(1) FROM "+table +" WHERE "
	    for key in params:#Agregar la lista de cambios separados por comas
	        query+=key+"="+self.escapeString(params[key])+" AND "
	    query=query[:-4]
	    #+param+" = '"+value+"'"#Un query para contar las veces que se repite un param de valor value en table
	    amount=self.doQuery(query)
	    if str(amount[0][0])=="0":#Si no existe
	        return False
	    return True #Si existe
	def escapeString(self, original):#Escapa el string
		myConnection =pymysql.connect( host=self.hostname, user=self.username, passwd=self.password, db=self.database )	#Crear la conexión con la BD
		cur = myConnection.cursor()	
		result=myConnection.escape(str(original))
		myConnection.commit()
		myConnection.close()
		return result
	def insertOrUpdate(self, table, upParams, whereParams): #Regresa [exito, esNuevo]
		try:
			#Si ya existe:
			if self.existsInDB(table,whereParams):
				self.updateInDB(table,upParams, whereParams)
				return [True,False]
			else:#Si hay que agregarlo a la DB
				self.insertInDB(table, upParams)
				return [True, True]
		except Exception as e:
			print(str(e))
			return [False,None]

	def selectAllAsObject(self, table, whereParams=None, sort=None):
		#Obtener los nombres de las columnas
		columns=self.doQuery("SHOW COLUMNS FROM "+table)
		columnNames=[]
		for column in columns:
			columnNames.append(column[0])
		#Agregar todas las collumnas en orden a la Query
		query='SELECT '
		for column in columnNames:
			query+=column+','
		query=query[:-1]
		query+=' FROM '+table
		#Condiciones
		if whereParams:
			query+=' WHERE '
			for key in whereParams:#Agregar la lista de parámetros separada por comas
				query+=key +"="+self.escapeString(whereParams[key])+" AND "
			
			query = query[:-4]  #Quitar la última coma y preparar para los parámetros
		s=' '
		if sort:
			s=' ORDER BY '
			for so in sort:
				s=s+str(so[0])+' '+str(so[1])+','
			s=s[:-1]
		query+=s
		#print(query)
		#Hacer la query
		results=self.doQuery(query)
		#Pasar a objeto
		objects=[]
		for result in results:
			ob={}
			for key, value in zip(columnNames, result):
				ob[key]=value
			objects.append(ob)

		return objects
	def getFields(self, table, fields,whereParams=None, sort=None, limit=None):
		#Se podrían añadir IN(x)... y los operadores >, <=, >=, <, <>
		reservedWhere=['=NOW()', '>NOW()', '<NOW()', 'IS NULL' , 'IS NOT NULL', "IN("]
		#obtener el listado de los valores deseados
		d=''
		for f in fields:
			d=d+str(f)+','
		d=d[:-1]
		w=''
		if whereParams:
			w='WHERE '
			for key in whereParams:#Agregar la lista de parámetros separada por comas
				if whereParams[key] in reservedWhere or whereParams[key][:3] in reservedWhere :
					w+=key+' '+whereParams[key]+" AND "
				else:
					w+=key+"="+self.escapeString(whereParams[key])+" AND "
			w = w[:-5]

		s=''
		if sort:
			s='ORDER BY '
			for so in sort:
				s=s+str(so[0])+' '+str(so[1])+','
			s=s[:-1]
		l=''
		if limit:
				l='LIMIT '+str(int(limit))

		query="SELECT "+d+' FROM '+table+' '+w+' '+s+' '+l+' ;'
		res=self.doQuery(query)

		valores=[]
		for line in res:
			objeto={}
			for v, key in zip(line, fields):
				objeto[key]=v
			valores.append(objeto)
		return valores

	def doTransaction(self,queriesList, traceback=False, charset='utf8'):
		if traceback == True:
			print("Se iniciará la transacción...")
		try:
			myConnection =pymysql.connect( host=self.hostname, user=self.username, passwd=self.password, db=self.database,charset=charset )	#Crear la conexión con la BD
			cur = myConnection.cursor()
			a=0
			for query in queriesList:
				if traceback == True:
					print(query)
				cur.execute(query)
				a+=1
				if a%100 == 0 and traceback==True:
					print("Working in sentence number: "+str(a))
			if traceback == True:
				print("Transacción armada.\nSe ejecutará...")
				print("Longitud:", len(queriesList))
			myConnection.commit()
			myConnection.close()
			result=cur.fetchall()
			print(str(result))
			return "exito"
		except Exception as ex:
			return "Error en transacción: "+str(ex)