import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

class MyHandler(FileSystemEventHandler):
	def on_any_event(self, event):
		print("Got it! Evento: ", event.event_type)
		self.process(event)

	def process(self, event):
		filename, ext = os.path.splitext(event.src_path)
		filename = f"{filename}_thumbnail{ext}"
		print("El archivo nuevo/cambiado/eliminado fue:", filename)


event_handler = MyHandler()
observer = Observer()
observer.schedule(event_handler, path='.', recursive=False)
observer.start()
try:
    while True:
        time.sleep(30)
except KeyboardInterrupt:
    observer.stop()
observer.join()