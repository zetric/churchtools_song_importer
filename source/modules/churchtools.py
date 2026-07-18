import requests
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class churchtools:
 
  def __init__(
      self,
      CT_URL,
      CT_API_TOKEN,
      CT_API_PAGE_LIMIT,
      CT_HEADERS_JSON,
      CT_HEADERS_FORM,
      CT_SONG_ARRANGEMENT_NAME
      ):
    self.CT_URL = CT_URL
    self.CT_API_TOKEN = CT_API_TOKEN
    self.CT_API_PAGE_LIMIT = CT_API_PAGE_LIMIT
    self.CT_HEADERS_JSON = CT_HEADERS_JSON
    self.CT_HEADERS_FORM = CT_HEADERS_FORM
    self.CT_SONG_ARRANGEMENT_NAME = CT_SONG_ARRANGEMENT_NAME
 

  def ct_create_song(self,song, category_id, arrangement_name, type):

    # --- Create a new song in CT

    # Check if there is a dedicated song number
    if "number" in song.keys():
      title = f"{song["number"]} - {song["title"]}"
    else:
      title = song["title"]

    body = {
      "author": f"{song["author"]}",
      "categoryId": category_id,
      "copyright": f"{song["copyright"]}",
      "name": title,
      'arrangements': [{
                  'name': arrangement_name,
                  'isDefault': True,
                  'description': f"#DIESE ZEILE NICHT ÄNDERN##{type}{song["internal_id"]}##\n"
      }]
    }

    try:
      (result := requests.post(url = f"{self.CT_URL}/songs", headers = self.CT_HEADERS_JSON, json = body)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete = result_json["data"]
      return result_json_complete
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)
    

  def ct_update_song(self, song_id, song, category_id):

    # --- Update a song in CT

    # Check if there is a dedicated song number
    if "number" in song.keys():
      title = f"{song["number"]} - {song["title"]}"
    else:
      title = song["title"]

    body = {
      "name": title,
      "author": f"{song["author"]}",
      "categoryId": category_id,
      "copyright": f"{song["copyright"]}",
    }

    try:
      (result := requests.put(url = f"{self.CT_URL}/songs/{song_id}", headers = self.CT_HEADERS_JSON, json = body)).raise_for_status()
      return json.loads(result.text)
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)


  def ct_get_song_by_id(self, id):

    # --- Get a song from CT by id

    try:
      (result:= requests.get(url = f"{self.CT_URL}/songs/{id}?include=arrangements&limit={self.CT_API_PAGE_LIMIT}&page=1", headers = self.CT_HEADERS_JSON)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete = result_json["data"]
      while result_json["meta"]["pagination"]["current"] <= result_json["meta"]["pagination"]["lastPage"]:
        (result:= requests.get(url = f"{self.CT_URL}/songs/{id}?include=arrangements&limit={self.CT_API_PAGE_LIMIT}&page={result_json["meta"]["pagination"]["current"] + 1}", headers = self.CT_HEADERS_JSON)).raise_for_status()
        result_json = json.loads(result.text)
        result_json_complete.extend(result_json["data"])
      return result_json_complete
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)


  def ct_get_song_by_name_and_internal_id(self, name, internal_id, arrangement_name, type):

    # --- Get a song from CT by name and internal number

    songs = self.ct_get_songs_by_name(name)

    for song in songs:

      for arrangement in song["arrangements"]:
        if arrangement["name"] == arrangement_name:
          if(description := arrangement["description"]):
            try:
              if description.split(f"##")[1].lstrip(type) == internal_id:
                return song
            except Exception as ex:
              logger.warning(ex)
              logger.warning("Internal song id was not properly found")
    
    return False


  def ct_get_songs_by_name(self, name):

    # --- Get a song from CT by id

    try:
      (result:= requests.get(url = f"{self.CT_URL}/songs?include=arrangements&name={name}&limit={self.CT_API_PAGE_LIMIT}&page=1", headers = self.CT_HEADERS_JSON)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete = result_json["data"]
      while result_json["meta"]["pagination"]["current"] <= result_json["meta"]["pagination"]["lastPage"]:
        (result:= requests.get(url = f"{self.CT_URL}/songs?include=arrangements&name={name}&limit={self.CT_API_PAGE_LIMIT}&page={result_json["meta"]["pagination"]["current"] + 1}", headers = self.CT_HEADERS_JSON)).raise_for_status()
        result_json = json.loads(result.text)
        result_json_complete.extend(result_json["data"])
      return result_json_complete
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)


  def ct_get_songs_by_category_id(self, category_id):

    # --- Get a song from CT by category id

    try:
      (result:= requests.get(url = f"{self.CT_URL}/songs?song_category_ids[]={category_id}&limit={self.CT_API_PAGE_LIMIT}&page=1", headers = self.CT_HEADERS_JSON)).raise_for_status()
      result_json = json.loads(result.text)
      result_json_complete = result_json["data"]
      while result_json["meta"]["pagination"]["current"] <= result_json["meta"]["pagination"]["lastPage"]:
        (result:= requests.get(url = f"{self.CT_URL}/songs?song_category_ids[]={category_id}&limit={self.CT_API_PAGE_LIMIT}&page={result_json["meta"]["pagination"]["current"] + 1}", headers = self.CT_HEADERS_JSON)).raise_for_status()
        result_json = json.loads(result.text)
        result_json_complete.extend(result_json["data"])
      return result_json_complete
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)


  def ct_delete_song_by_id(self, id):

    # --- Delete a song from CT by id

    try:
      (result:= requests.delete(url = f"{self.CT_URL}/songs/{id}", headers = self.CT_HEADERS_JSON)).raise_for_status()
      return result.status_code
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)


  def ct_create_song_arrangement(self, song_id, arrangement_name):

    # --- Update arrangement part of the song in CT

    body = {
      "name": arrangement_name
    }

    try:
      (result := requests.post(url = f"{self.CT_URL}/songs/{song_id}/arrangements", headers = self.CT_HEADERS_JSON, json = body)).raise_for_status()
      return json.loads(result.text)["data"]
    except requests.exceptions.HTTPError as err:
        logging.error(err)
        logging.error(result.text)


  def ct_get_masterdata(self, category):

    # --- Get masterdata from CT (song tags)

    try:
      (result:= requests.get(url = f"{self.CT_URL}/event/masterdata", headers = self.CT_HEADERS_JSON)).raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text)

    if(category):
      retVal = json.loads(result.text)["data"][category]
    else:
      retVal = json.loads(result.text)
    
    return retVal


  def ct_upload_song_file(self, arrangement_id, path):
    
    # --- Upload a file and attach it to a song arrangement

    # Create requets session (workaround for requets module due to non standard "files[]" key in POST)
    ct_session = requests.sessions.Session()
    ct_session.get(f"{self.CT_URL}/whoami", headers=self.CT_HEADERS_JSON)

    # Get CSRF token ad add to new header
    csrf_token_response = ct_session.get(f"{self.CT_URL}/csrftoken", headers=self.CT_HEADERS_FORM)
    headers = dict(ct_session.headers)
    headers.update({"CSRF-Token": json.loads(csrf_token_response.text)["data"]})

    with open(path, 'rb') as source_file:
      
      files = {"files[]": (source_file.name.split("/")[-1], source_file)}

      try:
        (result:= ct_session.post(url = f"{self.CT_URL}/files/song_arrangement/{arrangement_id}", headers = headers, files = files)).raise_for_status()
        return json.loads(result.text)
      except requests.exceptions.HTTPError as err:
          logger.error(err)
          logger.error(result.text) 
      finally:
        ct_session.close()


  def ct_delete_song_file(self, arrangement_id):
    
    # --- Delete a file of a specific arrangement

    # Create requets session (workaround for requets module due to non standard "files[]" key in POST)
    ct_session = requests.sessions.Session()
    ct_session.get(f"{self.CT_URL}/whoami", headers=self.CT_HEADERS_JSON)

    # Get CSRF token ad add to new header
    csrf_token_response = ct_session.get(f"{self.CT_URL}/csrftoken", headers=self.CT_HEADERS_FORM)
    headers = dict(ct_session.headers)
    headers.update({"CSRF-Token": json.loads(csrf_token_response.text)["data"]})

    try:
      ct_session.delete(url = f"{self.CT_URL}/files/song_arrangement/{arrangement_id}", headers = headers).raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(err)
    finally:
      ct_session.close()



  def ct_get_song_file(self, arrangement_id):
    
    # --- Check for existing arrangement file

    # Create requets session (workaround for requets module due to non standard "files[]" key in POST)
    ct_session = requests.sessions.Session()
    ct_session.get(f"{self.CT_URL}/whoami", headers=self.CT_HEADERS_JSON)

    # Get CSRF token ad add to new header
    csrf_token_response = ct_session.get(f"{self.CT_URL}/csrftoken", headers=self.CT_HEADERS_FORM)
    headers = dict(ct_session.headers)
    headers.update({"CSRF-Token": json.loads(csrf_token_response.text)["data"]})

    try:
      (result:= ct_session.get(url = f"{self.CT_URL}/files/song_arrangement/{arrangement_id}", headers = headers)).raise_for_status()
      return json.loads(result.text)["data"]
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        logger.error(result.text) 
    finally:
      ct_session.close()


  # HELPER

  def _ct_get_arrangement_id_by_name(self, song, arrangement_name):

    for arrangement in song["arrangements"]:
      if arrangement["name"] == arrangement_name:
        return arrangement["id"]
    
    return False

  def _ct_check_arrangement_name(self, arrangements):

    for arrangement in arrangements:
      if arrangement["name"] == self.CT_SONG_ARRANGEMENT_NAME:
        return True
      else:
        return False

  def _ct_get_arrangement_file_modification_date(self, arrangements):

    for arrangement in arrangements:
      if arrangement["name"] == self.CT_SONG_ARRANGEMENT_NAME:
        if len(arrangement["files"]) > 0:
          date_remote = datetime.strptime(arrangement["files"][0]["meta"]["modifiedDate"], "%Y-%m-%dT%H:%M:%SZ")
          logger.debug(f"Modification date remote file: {date_remote}")
          return date_remote
        else:
          return False
