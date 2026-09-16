import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {'X-API-Key': os.environ.get('OPENAQ_API_KEY')}
data = requests.get('https://api.openaq.org/v3/locations/13', headers=headers).json()
loc = data['results'][0]
print(f"Location ID 13: First: {loc.get('datetimeFirst')} - Last: {loc.get('datetimeLast')}")
