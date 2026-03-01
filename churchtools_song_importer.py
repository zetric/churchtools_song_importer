#!/usr/bin/python3

import os
import requests
import re
import json
import logging
import argparse

# Parsing arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', action="store_true", dest="mode_delete", help="delete mode", default=False)
parser.add_argument('-a', action="store_true", dest="mode_add", help="add mode", default=False)
args = parser.parse_args()
if not (args.mode_delete or args.mode_add):
    parser.error('No action requested, add -d or -a')

GB_TXT_FILE = os.environ["GB_TXT_FILE"]
GB_PPT_PATH = os.environ["GB_PPT_PATH"]
CT_URL = os.environ["CT_URL"]
CT_API_TOKEN = os.environ["CT_API_TOKEN"]
CT_SONG_CATEGORY = os.environ["CT_SONG_CATEGORY"]

CT_HEADERS_JSON =  {"Authorization": f"Login {CT_API_TOKEN}", "Content-Type": "application/json"}
CT_HEADERS_FORM =  {"Authorization": f"Login {CT_API_TOKEN}", "Content-Type": "multipart/form-data"}
CT_API_PAGE_LIMIT = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s-%(levelname)s - %(message)s')

logging.info("START")

def find_files(pattern, path):

  # --- Find a file starting with a pattern

  for root, dirs, files in os.walk(path):
      for name in files:
          if name.startswith(pattern):
              return os.path.join(root, name)


def get_file_path(number, path):
    
    # --- Get the full file path of file starting with pattern
   
    file_path = find_files(number, path)

    if file_path != None:
        return file_path
    else:
       return ""


def filter_songs(songs):

  # --- Harmonize different languages and sets         

  # Check for all numbers without tailing character
  # Remove other variants
  songs_result_1 = dict(songs)
  for song in songs:   
    if re.findall(r'^[0-9]+$', song):
       for song_next in songs:
          if re.findall(r'^' + f"{song}" + r'[a-z]+', song_next):
             songs_result_1.pop(song_next)

  # Check for all numbers with tailing "d" character
  # Remove other variants
  songs_result_2 = dict(songs_result_1)
  for song in songs_result_1:   
    if re.findall(r'^[0-9]+d$', song):
       songs_result_2[song[:-1]] = songs_result_2.pop(song)
       songs_result_2[song[:-1]].update({'number': song[:-1]})
       for song_next in songs_result_1:
          if re.findall(r'^' + f"{song[:-1]}" + r'(?!d)[a-z]+', song_next):
             songs_result_2.pop(song_next)

  # Check for all numbers with any tailing character
  # Remove other variants
  songs_result_3 = dict(songs_result_2)
  for song in songs_result_2:   
    if re_result := re.findall(r'^[0-9]+([a-z]+)$', song):
       if song in songs_result_3:
        songs_result_3[song[:-1]] = songs_result_3.pop(song)
        songs_result_3[song[:-1]].update({'number': song[:-1]})
        for song_next in songs_result_2:
            if re.findall(r'^' + f"{song[:-1]}" + r'(?!' + re_result[0] + r')[a-z]+', song_next):
              songs_result_3.pop(song_next)

  return songs_result_3


def read_songs(file):

  # --- Read a txt file that is an export from "EM elektronisch"
  # 
  # Structure of one entry:
  #
  # 2 Großer Gott, wir loben dich
  # 1. 2. 3. 4. 5. 6. 7. 8. 9. 10. 11. T: (Nach "Te Deum laudamus" 4. Jh.) Ignaz Franz 1768 / AÖL 1973/1978
  # M: Wien um 1776 / Leipzig 1819
  # S: Thomas Wegst 1999
  # Q: S: Rechte bei den Urhebern
  # In anderen Gesangbüchern: EG331 ö, FL30, GL257 ö, KG175 (ö), RG247 (ö)
  #
  # Can have more or less lines but this is the minimum and preferred structure. Minumum is the title.
  #
  # Manual CSV file changes do be done in some editor with regex before using in this script:
  #
  # Search: (^1\. .*) T:
  # Replace: $1\nT:
  #
  # Search: ^(?!Q:).+(T:.*)
  # Replace: $1\n$2
  #
  # Search: (^[0-9]+[a-z]* .*)
  # Replace: <END>\n<START>\n$1
  # Plus modifying start and end of file

  txt_data = {}

  with open(file) as source:

    file_content = source.read()

    data = re.findall(r'(?:<START>)(.*?)(?:<END>)', file_content, re.DOTALL)

    for entry in data:

      entry_set = {}

      entry = str(entry).strip()

      number = str(re.findall(r'(^[0-9]+[a-z]*) ', entry, re.DOTALL)[0]).strip()
      txt_data[number] = {}
      entry_set.update({'number': number})
      entry_set.update({'title': str(re.findall(r'(?:^[0-9]+[a-z]*) (.*)(?:\n)', entry)[0]).strip()})
      if re.findall(r'(?:T: )(.*)(?:\n)', entry):
        entry_set.update({'cr_text': str(re.findall(r'(?:T: )(.*)(?:\n)', entry)[0]).strip()})
      else:
          entry_set.update({'cr_text':""})
      if re.findall(r'(?:M: )(.*)(?:\n)', entry):
        entry_set.update({'cr_music': str(re.findall(r'(?:M: )(.*)(?:\n)', entry)[0]).strip()})
      else:
          entry_set.update({'cr_music':""})
      if re.findall(r'(?:S: )(.*)(?:\n)', entry):
        entry_set.update({'cr_set': str(re.findall(r'(?:S: )(.*)(?:\n)', entry)[0]).strip()})
      else:
          entry_set.update({'cr_set':""})
      if re.findall(r'(?:Q: )(.*)(?:\n)', entry):
        entry_set.update({'cr_source': str(re.findall(r'(?:Q: )(.*)(?:\n)', entry)[0]).strip()})
      else:
          entry_set.update({'cr_source':""})

      txt_data[number].update(entry_set)

  return txt_data


def ct_create_song(song, category_id):

  # --- Create a new song in CT

  body = {
    "author": f"{song["cr_text"]}",
    "categoryId": category_id,
    "copyright": f"{song["cr_source"]}",
    "name": f"{song["number"]} - {song["title"]}",
    'arrangements': [{
                'name': 'Standard',
                'isDefault': True
    }]
  }

  try:
    (result := requests.post(url = f"{CT_URL}/songs", headers = CT_HEADERS_JSON, json = body)).raise_for_status()
    return json.loads(result.text)
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text)
  

def ct_get_song_by_id(id):

  # --- Get a song from CT by id

  try:
    (result:= requests.get(url = f"{CT_URL}/songs/{id}?include=arrangements&limit={CT_API_PAGE_LIMIT}&page=1", headers = CT_HEADERS_JSON)).raise_for_status()
    result_json = json.loads(result.text)
    result_json_complete = result_json["data"]
    while result_json["meta"]["pagination"]["current"] <= result_json["meta"]["pagination"]["lastPage"]:
      (result:= requests.get(url = f"{CT_URL}/songs/{id}?include=arrangements&limit={CT_API_PAGE_LIMIT}&page={result_json["meta"]["pagination"]["current"] + 1}", headers = CT_HEADERS_JSON)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete.extend(result_json["data"])
    return result_json_complete
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text)

def ct_get_song_by_name(name):

  # --- Get a song from CT by id

  try:
    (result:= requests.get(url = f"{CT_URL}/songs?include=arrangements&name={name}&limit={CT_API_PAGE_LIMIT}&page=1", headers = CT_HEADERS_JSON)).raise_for_status()
    result_json = json.loads(result.text)
    result_json_complete = result_json["data"]
    while result_json["meta"]["pagination"]["current"] <= result_json["meta"]["pagination"]["lastPage"]:
      (result:= requests.get(url = f"{CT_URL}/songs?include=arrangements&name={name}&limit={CT_API_PAGE_LIMIT}&page={result_json["meta"]["pagination"]["current"] + 1}", headers = CT_HEADERS_JSON)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete.extend(result_json["data"])
    return result_json_complete
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text)


def ct_get_songs_by_category_id(category_id):

  # --- Get a song from CT by category id

  try:
    (result:= requests.get(url = f"{CT_URL}/songs?song_category_ids[]={category_id}&limit={CT_API_PAGE_LIMIT}&page=1", headers = CT_HEADERS_JSON)).raise_for_status()
    result_json = json.loads(result.text)
    result_json_complete = result_json["data"]
    while result_json["meta"]["pagination"]["current"] <= result_json["meta"]["pagination"]["lastPage"]:
      (result:= requests.get(url = f"{CT_URL}/songs?song_category_ids[]={category_id}&limit=1&page={result_json["meta"]["pagination"]["current"] + 1}", headers = CT_HEADERS_JSON)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete.extend(result_json["data"])
    return result_json_complete
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text)


def ct_delete_song_by_id(id):

  # --- Delete a song from CT by id

  try:
    (result:= requests.delete(url = f"{CT_URL}/songs/{id}", headers = CT_HEADERS_JSON)).raise_for_status()
    return result.status_code
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text)  


def ct_get_masterdata(category):

  # --- Get masterdata from CT (song tags)

  try:
    (result:= requests.get(url = f"{CT_URL}/event/masterdata", headers = CT_HEADERS_JSON)).raise_for_status()
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text)

  if(category):
     retVal = json.loads(result.text)["data"][category]
  else:
     retVal = json.loads(result.text)
  
  return retVal



def ct_upload_song_file(arrangement_id, path):
   
  # --- Upload a file and attach it to a song arrangement

  # Create requets session (workaround for requets module due to non standard "files[]" key in POST)
  ct_session = requests.sessions.Session()
  ct_session.get(f"{CT_URL}/whoami", headers=CT_HEADERS_JSON)

  # Get CSRF token ad add to new header
  csrf_token_response = ct_session.get(f"{CT_URL}/csrftoken", headers=CT_HEADERS_FORM)
  headers = dict(ct_session.headers)
  headers.update({"CSRF-Token": json.loads(csrf_token_response.text)["data"]})

  with open(path, 'rb') as source_file:
    
    files = {"files[]": (source_file.name.split("/")[-1], source_file)}

    try:
      (result:= ct_session.post(url = f"{CT_URL}/files/song_arrangement/{arrangement_id}", headers = headers, files = files)).raise_for_status()
      return json.loads(result.text)
    except requests.exceptions.HTTPError as err:
        logging.error(err)
        logging.error(result.text) 
    finally:
      ct_session.close()


def ct_get_song_file(arrangement_id):
   
  # --- Check for existing arrangement file

  # Create requets session (workaround for requets module due to non standard "files[]" key in POST)
  ct_session = requests.sessions.Session()
  ct_session.get(f"{CT_URL}/whoami", headers=CT_HEADERS_JSON)

  # Get CSRF token ad add to new header
  csrf_token_response = ct_session.get(f"{CT_URL}/csrftoken", headers=CT_HEADERS_FORM)
  headers = dict(ct_session.headers)
  headers.update({"CSRF-Token": json.loads(csrf_token_response.text)["data"]})

  try:
    (result:= ct_session.get(url = f"{CT_URL}/files/song_arrangement/{arrangement_id}", headers = headers)).raise_for_status()
    return json.loads(result.text)["data"]
  except requests.exceptions.HTTPError as err:
      logging.error(err)
      logging.error(result.text) 
  finally:
    ct_session.close()



# MAIN FUNCTIONS

logging.info("Reading song txt file")
songs = read_songs(GB_TXT_FILE)
logging.info("Filter songs file for needed data")
songs_filtered = filter_songs(songs)

logging.debug("Get category id")
ct_categories = ct_get_masterdata("songCategories")
for ct_category in ct_categories:
  
  if ct_category["name"] == CT_SONG_CATEGORY:
     ct_category_id = int(ct_category["id"])
     logging.debug("Categotry id: %s", ct_category_id)

if args.mode_delete:

  logging.info("Deleting all songs")
  songs_by_category = ct_get_songs_by_category_id(ct_category_id)
  for song in songs_by_category:
    ct_delete_song_by_id(song["id"])

if args.mode_add:

  logging.info("Go over every song")
  logging.info("------------------")
  for song in songs_filtered:

    logging.info("Current song: %s - %s", song, songs_filtered[song]["title"])
    logging.info("########################")
    
    logging.debug("Get file path")
    file_path = get_file_path(song, GB_PPT_PATH)
    logging.debug("File path: %s", file_path)
    logging.debug("Updating song dict with file path")
    songs_filtered[song].update({'path': file_path})


    logging.info("Creating song")
    if len(ct_song := ct_get_song_by_name(f"{songs_filtered[song]["number"]} - {songs_filtered[song]["title"]}")) == 0:
      
      ct_song = ct_create_song(songs_filtered[song], ct_category_id)
      ct_song = ct_get_song_by_name(f"{songs_filtered[song]["number"]} - {songs_filtered[song]["title"]}")

    else:
       
       logging.warning("Song with this name already existing")

    arrangement_id = ct_song[0]["arrangements"][0]["id"]
    
    if ct_get_song_file(arrangement_id) == []:
    
      logging.info("Uploading arrangement file")
      if os.path.isfile(songs_filtered[song]["path"]):
        ct_upload_song_file(arrangement_id, songs_filtered[song]["path"])
      else:
         logging.error("No file existing for the song")
    
    else:

      logging.warning("Song file already existing. Not uploading")


