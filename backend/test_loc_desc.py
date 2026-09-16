import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {'X-API-Key': os.environ.get('OPENAQ_API_KEY')}
data = requests.get('https://api.openaq.org/v3/locations', headers=headers, params={'limit': 5, 'sort_order': 'desc'}).json()
for loc in data.get('results', []):
    print(f"ID: {loc['id']}, Last: {loc.get('datetimeLast', {}).get('utc')}")
