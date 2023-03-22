import subprocess
import time

while True:
    subprocess.run(["python", "code.py"])
    time.sleep(60) # Sleep for 60 seconds before running again
