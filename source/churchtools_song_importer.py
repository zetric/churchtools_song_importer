#!/usr/bin/python3

import os, sys
import logging
import argparse
from datetime import datetime
import asyncio
import shutil
import modules.gesangbuch as gesangbuch
import modules.songbeamer as songbeamer
import modules.churchtools as churchtools
import modules.nextcloud as nextcloud

# Parsing arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--delete', action="store_true", dest="mode_delete", default=None,help="deletes all songs of this category before doing anything else")
parser.add_argument('-a', '--add', action="store_true", dest="mode_add", default=None, help="add mode")
parser.add_argument('-c', '--cleanup', action="store_true", dest="cleanup", default=None, help="Remove all songs that do not contain an internal ID and were therefore not managed by this script (be careful!)")
parser.add_argument('-t', '--type', action="store", dest="type", default=None, help="gb (Gesangbuch), sb (Songbeamer)")
parser.add_argument('-s', '--source', action="store", dest="source", default=None, help="nc (nextcloud), local")
parser.add_argument('-n', '--number', action="store", dest="number", default=None, help="Single song number to add or sync")
parser.add_argument('--skip-update', action="store_true", dest="skip_update", default=None, help="Skip update of existing songs and only crete new ones")
parser.add_argument('--gb-txt-file', action="store", dest="gb_txt_file", default=None, help="Path to the TXT file with the Gesangbuch metadata")
parser.add_argument('--gb-file-path', action="store", dest="gb_file_path", default=None, help="Path to the Gesangbuch slides files")
parser.add_argument('--sb-file-path', action="store", dest="sb_file_path", default=None, help="Path to the Songbeamer song files")
parser.add_argument('--nextcloud-url', action="store", dest="nextcloud_url", default=None, help="URL of the nextcloud instance")
parser.add_argument('--nextcloud-user', action="store", dest="nextcloud_user", default=None, help="User for the nextcloud instance")
parser.add_argument('--nextcloud-pass', action="store", dest="nextcloud_pass", default=None, help="Password for the nextcloud instance")
parser.add_argument('--ct-url', action="store", dest="ct_url", default=None, help="URL of the ChurchTools instance")
parser.add_argument('--ct-api-token', action="store", dest="ct_api_token", default=None, help="API token for the ChurchTools instance")
parser.add_argument('--ct-song-category-gb', action="store", dest="ct_song_category_gb", default=None, help="ChurchTools category for Gesangbuch songs")
parser.add_argument('--ct-song-category-sb', action="store", dest="ct_song_category_sb", default=None, help="ChurchTools category for Songbeamer songs")
parser.add_argument('--ct-song-arrangement-name', action="store", dest="ct_song_arrangement_name", default=None, help="ChurchTools arrangement name to use")
parser.add_argument('--ct-campus-name', action="store", dest="ct_campus_name", default=None, help="Campus name of the congregation to filter for the correct category")
parser.add_argument('--loglevel', action="store", dest="loglevel", default=None, help="Loglevel")

args = parser.parse_args()
# if not (args.mode_delete or args.mode_add) or not args.type or not args.source:
#     parser.error('No action requested, add -d for delete mode, or -a, -c and -s to add or echo file')

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

if (CMD_ADD := args.mode_add if args.mode_add is not None else env_bool("CMD_ADD")) == None or (CMD_DELETE := args.mode_delete if args.mode_delete is not None else env_bool("CMD_DELETE")) == None:
  param_help("CMD_ADD / CMD_DELETE","--add / --delete")
if (CMD_CLEANUP := (args.cleanup if args.cleanup is not None else env_bool("CMD_CLEANUP"))) == None: CMD_CLEANUP = False
if (TYPE := (args.type if args.type is not None else env_text("TYPE"))) == None: param_help("TYPE","--type")
if (SOURCE := (args.source if args.source is not None else env_text("SOURCE"))) == None: param_help("SOURCE","--source")
if TYPE == "gb":
  if (GB_TXT_FILE := (args.gb_txt_file if args.gb_txt_file is not None else env_text("GB_TXT_FILE"))) == None: param_help("GB_TXT_FILE","--gb-txt-file")
  if (GB_FILE_PATH := (args.gb_file_path if args.gb_file_path is not None else env_text("GB_FILE_PATH"))) == None: param_help("GB_FILE_PATH","--gb-file-path")
  if (CT_SONG_CATEGORY_GB := (args.ct_song_category_gb if args.ct_song_category_gb is not None else env_text("CT_SONG_CATEGORY_GB"))) == None: param_help("CT_SONG_CATEGORY_GB","--ct-song-category-gb")
if TYPE == "sb":
  if (SB_FILE_PATH := (args.sb_file_path if args.sb_file_path is not None else env_text("SB_FILE_PATH"))) == None: param_help("SB_FILE_PATH","--sb-file-path")
  if (CT_SONG_CATEGORY_SB := (args.ct_song_category_sb if args.ct_song_category_sb is not None else env_text("CT_SONG_CATEGORY_SB"))) == None: param_help("CT_SONG_CATEGORY_SB","--ct-song-category-sb")
if SOURCE == "nc":
  if (NEXTCLOUD_URL := (args.nextcloud_url if args.nextcloud_url is not None else env_text("NEXTCLOUD_URL"))) == None: param_help("NEXTCLOUD_URL","--nextcloud-url")
  if (NEXTCLOUD_USER := (args.nextcloud_user if args.nextcloud_user is not None else env_text("NEXTCLOUD_USER"))) == None: param_help("NEXTCLOUD_USER","--nextcloud-user")
  if (NEXTCLOUD_PASS := (args.nextcloud_pass if args.nextcloud_pass is not None else env_text("NEXTCLOUD_PASS"))) == None: param_help("NEXTCLOUD_PASS","--nextcloud-pass")
NUMBER = args.number if args.number is not None else env_text("NUMBER")
SKIP_UPDATE = args.skip_update if args.skip_update is not None else env_text("SKIP_UPDATE")
if (CT_URL := (args.ct_url if args.ct_url is not None else env_text("CT_URL"))) == None: param_help("CT_URL","--ct-url")
if (CT_API_TOKEN := (args.ct_api_token if args.ct_api_token is not None else env_text("CT_API_TOKEN"))) == None: param_help("CT_API_TOKEN","--ct-api-token")
if (CT_SONG_ARRANGEMENT_NAME := (args.ct_song_arrangement_name if args.ct_song_arrangement_name is not None else env_text("CT_SONG_ARRANGEMENT_NAME"))) == None: param_help("CT_SONG_ARRANGEMENT_NAME","--ct-song-arrangement-name")
CT_CAMPUS_NAME = args.ct_campus_name if args.ct_campus_name is not None else env_text("CT_CAMPUS_NAME")
if (LOGLEVEL := (args.loglevel if args.loglevel is not None else env_text("LOGLEVEL").upper())) == None: param_help("LOGLEVEL","--loglevel")

CT_HEADERS_JSON =  {"Authorization": f"Login {CT_API_TOKEN}", "Content-Type": "application/json"}
CT_HEADERS_FORM =  {"Authorization": f"Login {CT_API_TOKEN}", "Content-Type": "multipart/form-data"}
CT_API_PAGE_LIMIT = 100
SB_TMP_FOLDER = "sb_tmp"
GB_TMP_FOLDER = "gb_tmp"

logging.basicConfig(level=LOGLEVEL, format='%(asctime)s-%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def copy_files_to_tmp(path, dst):

    for root, dirs, files in os.walk(path):
      for file in files:
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

gb = gesangbuch.gesangbuch()

sb = songbeamer.songbeamer()

ct = churchtools.churchtools(
  CT_URL=CT_URL,
  CT_API_TOKEN=CT_API_TOKEN,
  CT_API_PAGE_LIMIT=CT_API_PAGE_LIMIT,
  CT_HEADERS_JSON=CT_HEADERS_JSON,
  CT_HEADERS_FORM=CT_HEADERS_FORM,
  CT_SONG_ARRANGEMENT_NAME=CT_SONG_ARRANGEMENT_NAME
)

nc = nextcloud.nextcloud(
  nextcloud_url=NEXTCLOUD_URL,
  nc_auth_user=NEXTCLOUD_USER,
  nc_auth_pass=NEXTCLOUD_PASS
)


# Gesangbuch mode
if "gb" in TYPE:

  logger.info("GESANGBUCH SECTION")

  logger.debug(f"Get category id for {CT_SONG_CATEGORY_GB}")
  ct_categories = ct.ct_get_masterdata("songCategories")
  ct_campus_id = ct.ct_get_campus_id_by_name(name=CT_CAMPUS_NAME)
  logger.debug("Campus id: %s", ct_campus_id)
  
  ct_category_id = False
  for ct_category in ct_categories:
    if ct_category["name"] == CT_SONG_CATEGORY_GB and ct_campus_id == ct_category["campusId"]:
      ct_category_id = int(ct_category["id"])
      logger.debug("Category id: %s", ct_category_id)
  if not ct_category_id:
    logger.error(f"Cannot find campus {CT_CAMPUS_NAME} and category id for {CT_SONG_CATEGORY_GB}")

  if CMD_DELETE:

    logger.info("DELETE MODE")

    logger.info("Deleting all songs")
    if input("Are you sure (y/n)??: ") == "y":
      songs_by_category = ct.ct_get_songs_by_category_id(ct_category_id)
      for song in songs_by_category:
        logger.info(f"Deleting song {song["name"]}")
        ct.ct_delete_song_by_id(song["id"])
    else:
      logger.info("Canceled...")

  if CMD_CLEANUP:

    logger.info("CLEANUP MODE")

    logger.info("Cleaning up all songs without an internal id")
    songs_by_category = ct.ct_get_songs_by_category_id(category_id=ct_category_id)

    for song in songs_by_category:
      arrangement_id = ct._ct_get_arrangement_id_by_name(song=song, arrangement_name=CT_SONG_ARRANGEMENT_NAME)
      if not arrangement_id:
        ct.ct_delete_song_by_id(song["id"])
      else:
        for arrangement in song["arrangements"]:
          if arrangement['description']:
            if arrangement["id"] == arrangement_id and "#DIESE ZEILE NICHT ÄNDERN##" not in arrangement['description']:
              ct.ct_delete_song_by_id(song["id"])
          else:
            ct.ct_delete_song_by_id(song["id"])  
  
  if CMD_ADD:

    logger.info("ADD MODE")

    logger.info("Reading song txt file")
    songs = gb.read_gb_songs(file=GB_TXT_FILE)
    logger.info("Filter songs file for needed data")
    songs_filtered = gb.filter_gb_songs(songs=songs)

    if NUMBER:
      logger.info(f"Dedicated song number {NUMBER} provided. Reducing list to this one song.")
      single_song = songs_filtered[f"{NUMBER}"]
      songs_filtered = {}
      songs_filtered[str(NUMBER)] = {}
      songs_filtered[str(NUMBER)].update(single_song)

    if SOURCE == "nc":

      logger.info("Listing files from remote nextcloud path")
      file_list = asyncio.run(nc.list_dir(path=GB_FILE_PATH))

    logger.info("Go over every song")
    logger.info("------------------")
    for song in songs_filtered:

      logger.info("#####################################################")
      logger.info("Current song: %s - %s", song, songs_filtered[song]["title"])
      logger.info("#####################################################")
      
      file_path = get_file_path(number=songs_filtered[song]["number"], list=file_list)
      logger.debug(f"Updating song dict with file path {file_path}")
      songs_filtered[song].update({'source_path': file_path})
      songs_filtered[song].update({'tmp_path': f"{GB_TMP_FOLDER}/{file_path.split('/')[-1]}"})

      if ct_song := ct.ct_get_song_by_name_and_internal_id(name=f"{songs_filtered[song]["number"]} - {songs_filtered[song]["title"]}", internal_id=songs_filtered[song]["internal_id"], arrangement_name=CT_SONG_ARRANGEMENT_NAME, type="GB"):
                
        logger.info("Song with this name and internal id already existing. Updating (in case there are diffs)...")
       
        if not SKIP_UPDATE:
          ct.ct_update_song(song_id=ct_song["id"], song=songs_filtered[song], category_id=ct_category_id)

          logger.info("Get arrangement")
          if(ct._ct_check_arrangement_name(arrangements=ct_song["arrangements"])):

            arrangement_id = ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CT_SONG_ARRANGEMENT_NAME)
          
          else:
            
            logger.info("Arrangement not found. Creating.")
            arrangement_id = ct.ct_create_song_arrangement(song_id=ct_song["id"], arrangement_name=CT_SONG_ARRANGEMENT_NAME)["id"]

          logger.info("Creating or updating song file")
          if (date_remote := ct._ct_get_arrangement_file_modification_date(arrangements=ct_song["arrangements"])):

            logger.debug("Checking if local file is newer")
            date_local = asyncio.run(nc.get_file_modified_timestamp(songs_filtered[song]["source_path"]))
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
                asyncio.run(nc.download_files(list=list([songs_filtered[song]["source_path"]]), destination=GB_TMP_FOLDER))
                ct.ct_delete_song_file(arrangement_id=arrangement_id)
                ct.ct_upload_song_file(arrangement_id=arrangement_id, path=songs_filtered[song]["tmp_path"])
          
          else:

            logger.info("No file existing in ChurchTools. Uploading")
            if songs_filtered[song]["source_path"]:
              asyncio.run(nc.download_files(list=list([songs_filtered[song]["source_path"]]), destination=GB_TMP_FOLDER))
              ct.ct_upload_song_file(arrangement_id=arrangement_id, path=songs_filtered[song]["tmp_path"])
            else:
              logger.warning("No file existing locally. Nothing to upload.")
          
        else:
          logger.info("Skipping update")

      else:

        logger.info("Song is not yet existing. Creating...")
        ct_song = ct.ct_create_song(songs_filtered[song], ct_category_id, CT_SONG_ARRANGEMENT_NAME, type="GB")
        logger.info("Uploading arrangement file")
        if songs_filtered[song]["source_path"]:
          if(arrangement_id := ct._ct_get_arrangement_id_by_name(ct_song, CT_SONG_ARRANGEMENT_NAME)):
            asyncio.run(nc.download_files(list=list([songs_filtered[song]["source_path"]]), destination=GB_TMP_FOLDER))
            ct.ct_upload_song_file(arrangement_id=arrangement_id, path=songs_filtered[song]["tmp_path"])
          else:
            logger.error("Arrangement not found.")
        else:
          logger.warning("No file existing locally. Nothing to upload.")


# SongBeamer mode
elif "sb" in TYPE:

  logger.info("SONGBEAMER SECTION")

  logger.debug(f"Get category id for {CT_SONG_CATEGORY_SB}")
  ct_categories = ct.ct_get_masterdata("songCategories")
  ct_campus_id = ct.ct_get_campus_id_by_name(name=CT_CAMPUS_NAME)
  logger.debug("Campus id: %s", ct_campus_id)
  
  ct_category_id = False
  for ct_category in ct_categories:
    if ct_category["name"] == CT_SONG_CATEGORY_SB and ct_campus_id == ct_category["campusId"]:
      ct_category_id = int(ct_category["id"])
      logger.debug("Category id: %s", ct_category_id)
  if not ct_category_id:
    logger.error(f"Cannot find campus {CT_CAMPUS_NAME} and category id for {CT_SONG_CATEGORY_SB}")

  if CMD_DELETE:

    logger.info("DELETE MODE")

    logger.info("Deleting all songs")
    if input("Are you sure (y/n)??: ") == "y":
      songs_by_category = ct.ct_get_songs_by_category_id(ct_category_id)
      for song in songs_by_category:
        logger.info(f"Deleting song {song["name"]}")
        ct.ct_delete_song_by_id(song["id"])
    else:
      logger.info("Canceled...")

  if CMD_CLEANUP:

    logger.info("CLEANUP MODE")

    logger.info("Cleaning up all songs without an internal id")
    songs_by_category = ct.ct_get_songs_by_category_id(category_id=ct_category_id)

    for song in songs_by_category:
      arrangement_id = ct._ct_get_arrangement_id_by_name(song=song, arrangement_name=CT_SONG_ARRANGEMENT_NAME)
      if not arrangement_id:
        ct.ct_delete_song_by_id(song["id"])
      else:
        for arrangement in song["arrangements"]:
          if arrangement['description']:
            if arrangement["id"] == arrangement_id and "#DIESE ZEILE NICHT ÄNDERN##" not in arrangement['description']:
              ct.ct_delete_song_by_id(song["id"])
          else:
            ct.ct_delete_song_by_id(song["id"])  

  if CMD_ADD:

    logger.info("ADD MODE")

    logger.info("Reading SongBeamer song files")

    if SOURCE == "local":

      logger.info("Copying files from local path")
      if os.path.exists(SB_TMP_FOLDER):
        shutil.rmtree(SB_TMP_FOLDER)
        os.makedirs(SB_TMP_FOLDER)
      else:
        os.makedirs(SB_TMP_FOLDER)
      copy_files_to_tmp(path=SB_FILE_PATH, dst=SB_TMP_FOLDER)
      logger.debug("Reading local files")
      sb_songs = sb.read_sb_songs(path=SB_TMP_FOLDER)

    elif SOURCE == "nc":

      logger.debug("Downloading from remote nextcloud path")
      file_list = asyncio.run(nc.list_dir(path=SB_FILE_PATH))

      if NUMBER:
        logger.info(f"Dedicated sone number {NUMBER} provided. Reducing list to this one song.")
        for song_entry in file_list:
          if song_entry.split('/')[-1].split('-')[0] == NUMBER:
            file_list = list([song_entry])
            break

      asyncio.run(nc.download_files(list=file_list, destination=SB_TMP_FOLDER))
      logger.debug("Reading local files")
      sb_songs = sb.read_sb_songs(path=SB_TMP_FOLDER)
      # Fix files where the title is not set
      sb._fix_missing_title(sb.files_without_title)

    else:

      logger.error("No valid file source provided")

    

    logger.info("Go over every song")
    logger.info("------------------")
    for song in sb_songs:

      logger.info("#####################################################")
      logger.info(f"Current song: {song["title"]}")
      logger.info("#####################################################")
      
      if ct_song := ct.ct_get_song_by_name_and_internal_id(name=song["title"], internal_id=song["internal_id"], arrangement_name=CT_SONG_ARRANGEMENT_NAME, type="SB"):
        
        logger.info("Song with this name and internal id already existing. Updating (in case there are diffs)...")

        if not SKIP_UPDATE:
          ct.ct_update_song(song_id=ct_song["id"], song=song, category_id=ct_category_id)

          logger.info("Get arrangement")
          if(ct._ct_check_arrangement_name(arrangements=ct_song["arrangements"])):

            arrangement_id = ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CT_SONG_ARRANGEMENT_NAME)
          
          else:
            
            logger.info("Arrangement not found. Creating.")
            arrangement_id = ct.ct_create_song_arrangement(song_id=ct_song["id"], arrangement_name=CT_SONG_ARRANGEMENT_NAME)["id"]

          logger.info("Creating or updating song file")
          if (date_remote := ct._ct_get_arrangement_file_modification_date(arrangements=ct_song["arrangements"])):

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
        ct_song = ct.ct_create_song(song=song, category_id=ct_category_id, arrangement_name=CT_SONG_ARRANGEMENT_NAME, type="SB")
        logger.debug(ct_song)
        logger.info(f"Uploading arrangement file {song["filename"]}")

        if os.path.isfile(song["path"]):

          if(arrangement_id := ct._ct_get_arrangement_id_by_name(song=ct_song, arrangement_name=CT_SONG_ARRANGEMENT_NAME)):
          
            ct.ct_upload_song_file(arrangement_id=arrangement_id, path=song["path"])
        
        else:
        
            logger.error("No file existing for the song")
          


  logger.debug("Cleaning up...")
  if os.path.exists(SB_TMP_FOLDER):
    shutil.rmtree(SB_TMP_FOLDER)
  if os.path.exists(GB_TMP_FOLDER):
    shutil.rmtree(GB_TMP_FOLDER)
