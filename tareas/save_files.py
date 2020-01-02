ALLOWED_EXTENSIONS = {'txt', 'json', ''}

def allowed_file(filename):
	if '.' in filename:
		return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	else:
		if '' in ALLOWED_EXTENSIONS:
			return True
		


