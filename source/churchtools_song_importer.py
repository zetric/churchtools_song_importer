#!/usr/bin/python3

import os, sys
import logging
import argparse
from datetime import datetime
import asyncio
import shutil
import yaml
import re
import modules.gesangbuch as gesangbuch
import modules.songbeamer as songbeamer
import modules.churchtools as churchtools
import modules.nextcloud as nextcloud

# Parsing arguments
parser = argparse.ArgumentParser()
parser.add_argument('--loglevel', action="store", dest="loglevel", default=None, help="Loglevel")
parser.add_argument('--configfile', action="store", dest="configfile", default=None, help="Configfile")
parser.add_argument('--workload', action="store", dest="workload", default=None, help="Workload name for single execution mode")

args = parser.parse_args()

# Parameter handling

def param_help(env, param):
  print(f"ERROR: Missing {env} variable or {param} command line parameter\n")
  parser.print_help(sys.stderr)
  sys.exit(1)

def env_bool(name):
    value = os.environ.get(name)
    if value in (None, ""):
        return None
    
    return value.lower() in ("1", "true", "yes", "on")

def env_text(name):
    value = os.environ.get(name)
    if value in (None, ""):
        return None
    
    return value
    
if (CONFIGFILE := (args.configfile if args.configfile is not None else env_text("CONFIGFILE"))) == None: param_help("CONFIGFILE","--configfile")

CONFIG = None

try:
  with open(CONFIGFILE, 'r') as configfile:
    CONFIG = yaml.safe_load(configfile)
except Exception as ex:
  print("Config file could not be loaded.")

if (LOGLEVEL := CONFIG['global']['LOGLEVEL']) == None:
  if (LOGLEVEL := (args.loglevel if args.loglevel is not None else env_bool("LOGLEVEL"))) == None: param_help("LOGLEVEL","--loglevel")

CT_HEADERS_JSON =  {"Authorization": f"Login {CONFIG['global']['CT_API_TOKEN']}", "Content-Type": "application/json"}
CT_HEADERS_FORM =  {"Authorization": f"Login {CONFIG['global']['CT_API_TOKEN']}", "Content-Type": "multipart/form-data"}
CT_API_PAGE_LIMIT = 100
TMP_FOLDER = "tmp"

logging.basicConfig(level=CONFIG['global']['LOGLEVEL'], format='%(asctime)s-%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def copy_files_to_tmp(path, dst):

  for file in os.listdir(path):
    if os.path.isfile(os.path.join(path, file)):
      shutil.copy2(src=f"{path}/{file}", dst=dst)


def get_file_path(number, list):
    
    # --- Get the full file path of file starting with pattern
   
    for file in list:
        if file.split('/')[-1].split(' ')[0] == number:
          return file
    else:
      return ""

# MAIN FUNCTIONS

logger.info("START")

ct = churchtools.churchtools(
  CT_URL=f"{CONFIG['global']['CT_URL']}/api",
  CT_API_TOKEN=CONFIG['global']['CT_API_TOKEN'],
  CT_API_PAGE_LIMIT=CT_API_PAGE_LIMIT,
  CT_HEADERS_JSON=CT_HEADERS_JSON,
  CT_HEADERS_FORM=CT_HEADERS_FORM,
  CT_SONG_ARRANGEMENT_NAME=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'],
  loglevel=LOGLEVEL
)

for workload in CONFIG['workloads']:

  logger.debug("Cleaning up...")
  if os.path.exists(TMP_FOLDER):
    shutil.rmtree(TMP_FOLDER)
  logger.debug("Creating TMP folder")
  os.makedirs(TMP_FOLDER)

  if args.workload is not None and args.workload != workload['name']:
    continue

  if workload['SOURCE'] == "nextcloud":
    nc = nextcloud.nextcloud(
      nextcloud_url=workload['NEXTCLOUD_URL'],
      nc_auth_user=workload['NEXTCLOUD_USER'],
      nc_auth_pass=workload['NEXTCLOUD_PASS'],
      loglevel=LOGLEVEL
  )

  # Gesangbuch mode
  if "gesangbuch" in workload['TYPE']:

    logger.info(f"WORKLOAD: {workload['name']} - TYPE GESANGBUCH")

    gb = gesangbuch.gesangbuch(loglevel=LOGLEVEL)

    logger.debug(f"Get category id for {workload['CT_SONG_CATEGORY']}")
    ct_categories = ct.ct_get_masterdata("songCategories")
    ct_campus_id = ct.ct_get_campus_id_by_name(name=workload['CT_CAMPUS_NAME'])
    logger.debug("Campus id: %s", ct_campus_id)
    
    ct_category_id = False
    for ct_category in ct_categories:
      if ct_category["name"] == workload['CT_SONG_CATEGORY'] and ct_campus_id == ct_category["campusId"]:
        ct_category_id = int(ct_category["id"])
        logger.debug("Category id: %s", ct_category_id)
    if not ct_category_id:
      logger.error(f"Cannot find campus {workload['CT_CAMPUS_NAME']} and category id for {workload['CT_SONG_CATEGORY']}")
      sys.exit(1)

    logger.info("Reading song txt file")
    songs = gb.read_gb_songs(file=workload['GB_TXT_FILE'])
    logger.info("Filter songs file for needed data")
    songs_filtered = gb.filter_gb_songs(songs=songs)

    if workload['CMD_DELETE_ALL']:

      logger.info("DELETE MODE")

      logger.info("Deleting all songs")
      if input("Are you sure (y/n)??: ") == "y":
        songs_by_category = ct.ct_get_songs_by_category_id(ct_category_id)
        for song in songs_by_category:
          logger.info(f"Deleting song {song["name"]}")
          ct.ct_delete_song_by_id(song["id"])
      else:
        logger.info("Canceled...")  

    if workload['SOURCE'] == "nextcloud":

      logger.info("Listing files from remote nextcloud path")
      file_list = asyncio.run(nc.list_dir(path=workload['FILE_PATH']))
    
    elif workload['SOURCE'] == "local":

      logger.info("Listing files from local path")
      file_list_local = os.listdir(workload['FILE_PATH'])
      file_list = []
      for file in file_list_local:
        file_list.append(f"{workload['FILE_PATH']}/{file}")
    

    if workload['CMD_CLEANUP']:

      logger.info("CLEANUP MODE")

      logger.info("Cleaning up all songs without an arrangement, an internal id or who are not in the Gesangbuch source")
      songs_by_category = ct.ct_get_songs_by_category_id(category_id=ct_category_id)

      for song in songs_by_category:
        arrangement_id = ct._ct_get_arrangement_id_by_name(song=song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
        if not arrangement_id:
          logger.info(f"Deleting song {song["name"]} - no arrangement")
          ct.ct_delete_song_by_id(song["id"])
        else:
          for arrangement in song["arrangements"]:
            if arrangement['description']:
              if arrangement["id"] == arrangement_id and "#DIESE ZEILE NICHT ÄNDERN##" not in arrangement['description']:
                logger.info(f"Deleting song {song["name"]} - no ID field")
                ct.ct_delete_song_by_id(song["id"])
              else:
                song_found = False
                for song_filtered in songs_filtered:
                  if arrangement["description"].split(f"##")[1].lstrip(workload['CT_SONG_IDENTIFIER']) == songs_filtered[song_filtered]["internal_id"]:
                    song_found = True
                if not song_found:
                  logger.info(f"Deleting song {song["name"]} - non of internal ids found in ID filed")
                  ct.ct_delete_song_by_id(song["id"])
            else:
              logger.info(f"Deleting song {song["name"]} - else")
              ct.ct_delete_song_by_id(song["id"])

    if workload['CMD_ADD']:

      logger.info("ADD MODE")

      if 'NUMBER' in workload:
        logger.info(f"Dedicated song number {workload['NUMBER']} provided. Reducing list to this one song.")
        single_song = songs_filtered[f"{workload['NUMBER']}"]
        songs_filtered = {}
        songs_filtered[str(workload['NUMBER'])] = {}
        songs_filtered[str(workload['NUMBER'])].update(single_song)


      logger.info("Go over every song")
      logger.info("------------------")
      for song in songs_filtered:

        logger.info("#####################################################")
        logger.info("Current song: %s - %s", song, songs_filtered[song]["title"])
        logger.info("#####################################################")
        
        file_path = get_file_path(number=songs_filtered[song]["number"], list=file_list)
        if file_path == "":
          logger.warning("No file existing for the song. Adding extension to title.")
          songs_filtered[song].update({'title': f"{songs_filtered[song]["title"]} - KEINE LOKALE SONG DATEI"})
        else:
          logger.debug(f"Updating song dict with file path {file_path}")
          songs_filtered[song].update({'source_path': file_path})
          songs_filtered[song].update({'tmp_path': f"{TMP_FOLDER}/{file_path.split('/')[-1]}"})

        if ct_song := ct.ct_get_song_by_name_and_internal_id(name=f"{songs_filtered[song]["number"]} - ", internal_id=songs_filtered[song]["internal_id"], arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'], type=workload['CT_SONG_IDENTIFIER']):
                  
          logger.info("Song with this name and internal id already existing. Updating (in case there are diffs)...")
        
          if not workload['SKIP_UPDATE']:
            ct.ct_update_song_by_id(song_id=ct_song["id"], song=songs_filtered[song], category_id=ct_category_id)

            logger.info("Get arrangement")
            if(ct._ct_check_arrangement_name(arrangements=ct_song["arrangements"])):

              arrangement_id = ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
            
            else:
              
              logger.info("Arrangement not found. Creating.")
              arrangement_id = ct.ct_create_song_with_id_arrangement(song_id=ct_song["id"], arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])["id"]

            if (date_remote := ct._ct_get_arrangement_file_modification_date(arrangements=ct_song["arrangements"])):

              logger.debug(f"Modification date remote file: {date_remote}")

              logger.info("Creating or updating song file if newer")
              logger.debug("Checking if local file is newer")
              
              if "source_path" in songs_filtered[song]:
                if workload['SOURCE'] == "nextcloud":
                  date_local = asyncio.run(nc.get_file_modified_timestamp(songs_filtered[song]["source_path"]))
                elif workload['SOURCE'] == "local":
                  date_local = datetime.fromtimestamp(os.path.getmtime(songs_filtered[song]["source_path"]))
                date_local = date_local.replace(tzinfo=None)
                logger.debug(f"Modification date local file {date_local}")
                date_diff = date_local - date_remote
                logger.debug(f"Date diff: {date_diff.total_seconds()}")
                
                if date_diff.total_seconds() <= 0:

                  logger.debug("Remote file is newer than the local one. Skipping.")

                else:

                  logger.info("Local song file is newer. Replacing the remote")
                  if songs_filtered[song]["source_path"] == "":
                    logger.warning("No file existing at the source. Not changing anything.")
                  else:
                    if workload['SOURCE'] == "nextcloud":
                      asyncio.run(nc.download_files(list=list([songs_filtered[song]["source_path"]]), destination=TMP_FOLDER))
                    elif workload['SOURCE'] == "local":
                      shutil.copyfile(songs_filtered[song]["source_path"], songs_filtered[song]["tmp_path"])
                    ct.ct_delete_song_file(arrangement_id=arrangement_id)
                    ct.ct_upload_song_file(arrangement_id=arrangement_id, path=songs_filtered[song]["tmp_path"])
            
              else:

                logger.warning("No local file existing.")

            else:

              logger.info("No file existing in ChurchTools. Uploading.")
              if "source_path" in songs_filtered[song]:
                if workload['SOURCE'] == "nextcloud":
                  asyncio.run(nc.download_files(list=list([songs_filtered[song]["source_path"]]), destination=TMP_FOLDER))
                elif workload['SOURCE'] == "local":
                  shutil.copyfile(songs_filtered[song]["source_path"], songs_filtered[song]["tmp_path"])
                ct.ct_upload_song_file(arrangement_id=arrangement_id, path=songs_filtered[song]["tmp_path"])
              else:
                logger.warning("No file existing locally. Nothing to upload.")
            
          else:
            logger.info("Skipping update")

        else:

          logger.info("Song is not yet existing. Creating...")
          ct_song = ct.ct_create_song_with_id(song=songs_filtered[song], category_id=ct_category_id, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'], type=workload['CT_SONG_IDENTIFIER'])
          logger.info("Uploading arrangement file")
          if "source_path" in songs_filtered[song]:
            if(arrangement_id := ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])):
              if workload['SOURCE'] == "nextcloud":
                asyncio.run(nc.download_files(list=list([songs_filtered[song]["source_path"]]), destination=TMP_FOLDER))
              elif workload['SOURCE'] == "local":
                shutil.copyfile(songs_filtered[song]["source_path"], songs_filtered[song]["tmp_path"])
              ct.ct_upload_song_file(arrangement_id=arrangement_id, path=songs_filtered[song]["tmp_path"])
            else:
              logger.error("Arrangement not found.")
          else:
            logger.warning("No file existing locally. Nothing to upload.")


  # SongBeamer mode
  if "songbeamer" in workload['TYPE']:

    logger.info(f"WORKLOAD: {workload['name']} - TYPE SONGBEAMER")

    sb = songbeamer.songbeamer(loglevel=LOGLEVEL)

    logger.debug(f"Get category id for {workload['CT_SONG_CATEGORY']}")
    ct_categories = ct.ct_get_masterdata("songCategories")
    ct_campus_id = ct.ct_get_campus_id_by_name(name=workload['CT_CAMPUS_NAME'])
    logger.debug("Campus id: %s", ct_campus_id)
    
    ct_category_id = False
    for ct_category in ct_categories:
      if ct_category["name"] == workload['CT_SONG_CATEGORY'] and ct_campus_id == ct_category["campusId"]:
        ct_category_id = int(ct_category["id"])
        logger.debug("Category id: %s", ct_category_id)
    if not ct_category_id:
      logger.error(f"Cannot find campus {workload['CT_CAMPUS_NAME']} and category id for {workload['CT_SONG_CATEGORY']}")

    if workload['CMD_DELETE_ALL']:

      logger.info("DELETE MODE")

      logger.info("Deleting all songs")
      if input("Are you sure (y/n)??: ") == "y":
        songs_by_category = ct.ct_get_songs_by_category_id(ct_category_id)
        for song in songs_by_category:
          logger.info(f"Deleting song {song["name"]}")
          ct.ct_delete_song_by_id(song["id"])
      else:
        logger.info("Canceled...")

    
    if workload['SOURCE'] == "nextcloud":
    
      logger.info("Listing files from remote nextcloud path")
      file_list = asyncio.run(nc.list_dir(path=workload['FILE_PATH']))
      asyncio.run(nc.download_files(list=file_list, destination=TMP_FOLDER))
      # Fix files where the title is not set
      sb._fix_missing_title(sb.files_without_title)

    elif workload['SOURCE'] == "local":
    
        logger.info("Listing files from local path")
        file_list = os.listdir(workload['FILE_PATH'])
        logger.info("Copying files to TMP folder")
        copy_files_to_tmp(path=workload['FILE_PATH'], dst=TMP_FOLDER)
    
    logger.debug("Reading local files")
    sb_songs = sb.read_sb_songs(path=TMP_FOLDER)
      
    
    if workload['CMD_CLEANUP']:

      logger.info("CLEANUP MODE")

      logger.info("Cleaning up all songs without an arrangement, an internal id or who are not in the Songbeamer source")
      songs_by_category = ct.ct_get_songs_by_category_id(category_id=ct_category_id)

      for song in songs_by_category:
        arrangement_id = ct._ct_get_arrangement_id_by_name(song=song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
        if not arrangement_id:
          logger.info(f"Deleting song {song["name"]} - no arrangement")
          ct.ct_delete_song_by_id(song["id"])
        else:
          for arrangement in song["arrangements"]:
            if arrangement['description']:
              if arrangement["id"] == arrangement_id and "#DIESE ZEILE NICHT ÄNDERN##" not in arrangement['description']:
                logger.info(f"Deleting song {song["name"]} - no ID field")
                ct.ct_delete_song_by_id(song["id"])
              else:
                song_found = False
                for sb_song in sb_songs:
                  #logger.debug(sb_song)
                  if arrangement["description"].split(f"##")[1].lstrip(workload['CT_SONG_IDENTIFIER']) == sb_song["internal_id"]:
                    song_found = True
                if not song_found:
                  logger.info(f"Deleting song {song["name"]} - non of internal ids found in ID filed")
                  ct.ct_delete_song_by_id(song["id"])
            else:
              logger.info(f"Deleting song {song["name"]} - else")
              ct.ct_delete_song_by_id(song["id"])

    if workload['CMD_ADD']:

      logger.info("ADD MODE")

      logger.info("Reading SongBeamer song files")
      
      if 'NUMBER' in workload:
        logger.info(f"Dedicated song number {workload['NUMBER']} provided. Reducing list to this one song.")
        for song_entry in sb_songs:
          if song_entry['internal_id'] == workload['NUMBER']:
            sb_songs = list([song_entry])
            break
      
      logger.info("Go over every song")
      logger.info("------------------")
      for song in sb_songs:

        logger.info("#####################################################")
        logger.info(f"Current song: {song["title"]}")
        logger.info("#####################################################")
        
        if ct_song := ct.ct_get_song_by_name_and_internal_id(name=song["title"], internal_id=song["internal_id"], arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'], type=workload['CT_SONG_IDENTIFIER']):
          
          logger.info("Song with this name and internal id already existing. Updating (in case there are diffs)...")

          if not workload['SKIP_UPDATE']:
            ct.ct_update_song_by_id(song_id=ct_song["id"], song=song, category_id=ct_category_id)

            logger.info("Get arrangement")
            if(ct._ct_check_arrangement_name(arrangements=ct_song["arrangements"])):

              arrangement_id = ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
            
            else:
              
              logger.info("Arrangement not found. Creating.")
              arrangement_id = ct.ct_create_song_with_id_arrangement(song_id=ct_song["id"], arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])["id"]

            
            if (date_remote := ct._ct_get_arrangement_file_modification_date(arrangements=ct_song["arrangements"])):

              logger.debug(f"Modification date remote file: {date_remote}")

              logger.info("Creating or updating song file if newer")
              logger.debug("Checking if local file is newer")

              date_local = datetime.fromtimestamp(os.path.getmtime(song["path"]))
              logger.debug(f"Modification date local file {date_local}")
              date_diff = date_local - date_remote
              logger.debug(f"Date diff: {date_diff.total_seconds()}")
              
              if date_diff.total_seconds() <= 0:

                logger.debug("Remote file is newer than the local one. Skipping.")

              else:

                logger.info("Local song file is newer. Replacing the remote")
                ct.ct_delete_song_file(arrangement_id=arrangement_id)
                ct.ct_upload_song_file(arrangement_id=arrangement_id, path=song["path"])
            
            else:

              logger.info("No file existing in ChurchTools. Uploading")
              ct.ct_upload_song_file(arrangement_id=arrangement_id, path=song["path"])

          else:
            logger.info("Skipping update")
            

        else:

          logger.info("Song is not yet existing. Creating...")
          ct_song = ct.ct_create_song_with_id(song=song, category_id=ct_category_id, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'], type=workload['CT_SONG_IDENTIFIER'])
          logger.debug(ct_song)
          logger.info(f"Uploading arrangement file {song["filename"]}")

          if os.path.isfile(song["path"]):

            if(arrangement_id := ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])):
            
              ct.ct_upload_song_file(arrangement_id=arrangement_id, path=song["path"])
          
          else:
          
              logger.error("No file existing for the song")


  # File only mode
  if "file" in workload['TYPE']:

    logger.info(f"WORKLOAD: {workload['name']} - TYPE FILE ONLY")

    logger.debug(f"Get category id for {workload['CT_SONG_CATEGORY']}")
    ct_categories = ct.ct_get_masterdata("songCategories")
    ct_campus_id = ct.ct_get_campus_id_by_name(name=workload['CT_CAMPUS_NAME'])
    logger.debug("Campus id: %s", ct_campus_id)
    
    ct_category_id = False
    for ct_category in ct_categories:
      if ct_category["name"] == workload['CT_SONG_CATEGORY'] and ct_campus_id == ct_category["campusId"]:
        ct_category_id = int(ct_category["id"])
        logger.debug("Category id: %s", ct_category_id)
    if not ct_category_id:
      logger.error(f"Cannot find campus {workload['CT_CAMPUS_NAME']} and category id for {workload['CT_SONG_CATEGORY']}")
      sys.exit(1)

    if workload['CMD_DELETE_ALL']:

      logger.info("DELETE MODE")

      logger.info("Deleting all songs")
      if input("Are you sure (y/n)??: ") == "y":
        songs_by_category = ct.ct_get_songs_by_category_id(ct_category_id)
        for song in songs_by_category:
          logger.info(f"Deleting song {song["name"]}")
          ct.ct_delete_song_by_id(song["id"])
      else:
        logger.info("Canceled...")  

    if workload['SOURCE'] == "nextcloud":

      logger.info("Listing files from remote nextcloud path")
      file_list = asyncio.run(nc.list_dir(path=workload['FILE_PATH']))
      song_array = []
      for file in file_list:
        if workload['DETECT_SONG_NUMBERS']:
          song_array.append({
            "number": file.split('/')[-1].split(' ')[0], 
            "title": file.split('/')[-1].split(' ', 1)[1].split('.')[0],
            "fullPath": file
        })
        else:
          song_array.append({
            "title": file.split('/')[-1].split('.')[0],
            "fullPath": file
          })


    elif workload['SOURCE'] == "local":

      logger.info("Listing files from local path")
      file_list_local = os.listdir(workload['FILE_PATH'])
      song_array = []
      for file in file_list_local:
        if re.findall(r"^[0-9]* ", file):
          song_array.append({
            "number": file.split(' ')[0],
            "title": file.split('.')[0],
            "fullPath": f"{workload['FILE_PATH']}/{file}"
          })
        else:
          song_array.append({
            "title": file.split('/')[-1].split('.')[0],
            "fullPath": f"{workload['FILE_PATH']}/{file}"
          })
        

    if workload['CMD_CLEANUP']:

      logger.info("CLEANUP MODE")

      logger.info("Cleaning up all songs without an arrangement")
      songs_by_category = ct.ct_get_songs_by_category_id(category_id=ct_category_id)

      for song in songs_by_category:
        arrangement_id = ct._ct_get_arrangement_id_by_name(song=song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
        if not arrangement_id:
          logger.info(f"Deleting song {song["name"]} - no arrangement")
          ct.ct_delete_song_by_id(song["id"])

    if workload['CMD_ADD']:

      logger.info("ADD MODE")

      if 'NUMBER' in workload:
        logger.info(f"Dedicated song number {workload['NUMBER']} provided. Reducing list to this one song.")
        # This can add multiple songs as here there can be more than one song version with the same number
        song_array = []
        for song_entry in song_array:
          if song_entry['number'] == workload['NUMBER']:
            song_array.append(song_entry)

      logger.info("Go over every song")
      logger.info("------------------")
      for song in song_array:

        if 'number' in song:
          title_new = f"{song['number']} - {song['title']}"
        else:
          title_new = song['title']

        logger.info("#####################################################")
        logger.info("Current song: %s", title_new)
        logger.info("#####################################################")
        


        ct_songs = ct.ct_get_songs_by_name_and_category_id(name=title_new, category_id=ct_category_id)
        
        if ct_songs:
          for ct_song in ct_songs:
                    
            logger.info("Song with this name already existing. Updating (in case there are diffs)...")
          
            if not workload['SKIP_UPDATE']:
            
              logger.info("Get arrangement")
              if(ct._ct_check_arrangement_name(arrangements=ct_song["arrangements"])):

                arrangement_id = ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
              
              else:
                
                logger.info("Arrangement not found. Creating.")
                arrangement_id = ct.ct_create_song_with_id_arrangement(song_id=ct_song["id"], arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])["id"]

              if (date_remote := ct._ct_get_arrangement_file_modification_date(arrangements=ct_song["arrangements"])):

                logger.debug(f"Modification date remote file: {date_remote}")

                logger.info("Creating or updating song file if newer")
                logger.debug("Checking if local file is newer")
                
                if workload['SOURCE'] == "nextcloud":
                  date_local = asyncio.run(nc.get_file_modified_timestamp(song["fullPath"]))
                elif workload['SOURCE'] == "local":
                  date_local = datetime.fromtimestamp(os.path.getmtime(song["fullPath"]))
                date_local = date_local.replace(tzinfo=None)
                logger.debug(f"Modification date local file {date_local}")
                date_diff = date_local - date_remote
                logger.debug(f"Date diff: {date_diff.total_seconds()}")
                
                if date_diff.total_seconds() <= 0:

                  logger.debug("Remote file is newer than the local one. Skipping.")

                else:

                  logger.info("Local song file is newer. Replacing the remote")
                  if workload['SOURCE'] == "nextcloud":
                    asyncio.run(nc.download_files(list=list([song["fullPath"]]), destination=TMP_FOLDER))
                  elif workload['SOURCE'] == "local":
                    shutil.copyfile(song["fullPath"], f"{TMP_FOLDER}/{song['fullPath'].split('/')[-1]}")
                  ct.ct_delete_song_file(arrangement_id=arrangement_id)
                  ct.ct_upload_song_file(arrangement_id=arrangement_id, path=f"{TMP_FOLDER}/{song['fullPath'].split('/')[-1]}")

              else:

                logger.info("No file existing in ChurchTools. Uploading.")
                if workload['SOURCE'] == "nextcloud":
                  asyncio.run(nc.download_files(list=list([song['fullPath']]), destination=TMP_FOLDER))
                elif workload['SOURCE'] == "local":
                  shutil.copyfile(song['fullPath'], f"{TMP_FOLDER}/{song['fullPath'].split('/')[-1]}")
                ct.ct_upload_song_file(arrangement_id=arrangement_id, path=f"{TMP_FOLDER}/{song['fullPath'].split('/')[-1]}")
              
            else:
              logger.info("Skipping update")

        else:

          logger.info("Song is not yet existing. Creating...")
          ct_song = ct.ct_create_song(song=song, category_id=ct_category_id, arrangement_name=CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])
          logger.info("Uploading arrangement file")
          if(arrangement_id := ct._ct_get_arrangement_id_by_name(ct_song, CONFIG['global']['CT_SONG_ARRANGEMENT_NAME'])):
            if workload['SOURCE'] == "nextcloud":
              asyncio.run(nc.download_files(list=list([song['fullPath']]), destination=TMP_FOLDER))
            elif workload['SOURCE'] == "local":
              shutil.copyfile(song['fullPath'], f"{TMP_FOLDER}/{song['fullPath'].split('/')[-1]}")
            ct.ct_upload_song_file(arrangement_id=arrangement_id, path=f"{TMP_FOLDER}/{song['fullPath'].split('/')[-1]}")
          else:
            logger.error("Arrangement not found.")
          

  logger.info("✅ Finished")


  logger.debug("Cleaning up...")
  if os.path.exists(TMP_FOLDER):
    shutil.rmtree(TMP_FOLDER)
  if os.path.exists(TMP_FOLDER):
    shutil.rmtree(TMP_FOLDER)
