import requests
import hashlib
import time
import csv
import os
import ssl
from urllib3 import poolmanager
import logging
from variables import *

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class MarvelAPIAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, public_key, private_key):
        self.public_key = public_key
        self.private_key = private_key
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ctx)

    def generate_hash(self, timestamp):
        hash_input = f"{timestamp}{self.private_key}{self.public_key}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()

def get_timestamp():
    return str(int(time.time()))

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)

# Function to retrieve the Thor ID from the Marvel API
def get_character_id(session, timestamp):
    api_adapter = MarvelAPIAdapter(public_key=MARVEL_PUBLIC_API_KEY, private_key=MARVEL_PRIVATE_API_KEY)
    session.mount('https://', api_adapter)

    params = {
        'apikey': MARVEL_PUBLIC_API_KEY,
        'name': MARVEL_CHARACTER_NAME,
        'limit': MARVEL_LIMIT,
        'ts': timestamp,
        'hash': api_adapter.generate_hash(timestamp)
    }

    try:
        # API call | GET request to fetch Thor information
        response = session.get(MARVEL_CHARACTER_URL, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get('data', {}).get('results', [])

        if results:
            return results[0].get('id')
        else:
            log_info(NO_RESULTS_MESSAGE)
    except requests.exceptions.RequestException as e:
        log_error(f'{ERROR_MESSAGE} {str(e)}')
    except Exception as e:
        log_error(f'{ERROR_MESSAGE} {str(e)}')

    return None

# Function to retrieve comics related to Thor from the Marvel API
def get_comics(session, character_id, timestamp):
    api_adapter = MarvelAPIAdapter(public_key=MARVEL_PUBLIC_API_KEY, private_key=MARVEL_PRIVATE_API_KEY)
    session.mount('https://', api_adapter)

    params = {
        'apikey': MARVEL_PUBLIC_API_KEY,
        'characters': character_id,
        'format': MARVEL_FORMAT,
        'ts': timestamp,
        'hash': api_adapter.generate_hash(timestamp)
    }

    try:
        offset = MARVEL_OFFSET
        total = MARVEL_TOTAL
        all_comics = []

        while offset < total:
            params['offset'] = offset

            # API call | GET request to fetch comics related to Thor
            response_comics = session.get(MARVEL_COMICS_URL, params=params)
            response_comics.raise_for_status()

            comics_data = response_comics.json()
            total = comics_data.get('data', {}).get('total', 0)
            comics = []

            for comic in comics_data.get('data', {}).get('results', []):
                title = comic.get('title', '')
                publication_year = comic.get('dates', [{}])[0].get('date', '')[:4]
                cover_url = f"{comic.get('thumbnail', {}).get('path', '')}.{comic.get('thumbnail', {}).get('extension', '')}"
                comics.append([title, publication_year, cover_url])

            all_comics.extend(comics)
            offset += MARVEL_LIMIT

        return all_comics
    except requests.exceptions.RequestException as e:
        log_error(f'{COMICS_ERROR_MESSAGE} {str(e)}')
    except Exception as e:
        log_error(f'{COMICS_ERROR_MESSAGE} {str(e)}')

    return None

def save_comics_to_csv(comics):
    if not comics:
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    csv_filename = os.path.join(OUTPUT_DIR, 'thor_comic_data.csv')
    with open(csv_filename, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Comic Title', 'Publication Year', 'Cover URL'])
        csv_writer.writerows(comics)

    log_info(f'{CSV_GENERATED_MESSAGE} {csv_filename}')

if __name__ == "__main__":
    session = requests.Session()
    timestamp = get_timestamp()
    character_id = get_character_id(session, timestamp)

    if character_id is not None:
        comics_data = get_comics(session, character_id, timestamp)
        if comics_data:
            save_comics_to_csv(comics_data)
