

def process_count(process_name): #TODO add MacOS compatability
	
	import platform
	import subprocess
	
	if platform.system() == "Windows":
		return int(subprocess.check_output(f"tasklist | find /I /C \"{process_name}\"", shell=True))
	else:
		return None