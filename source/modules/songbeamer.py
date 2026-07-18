import os
import logging


logger = logging.getLogger(__name__) 
logger.setLevel(os.environ["LOGLEVEL"])

class songbeamer:

  files_without_title = []

  def __init__(self):
    pass

  def read_sb_songs(self, path):

    sb_songs = []
    
    for file in os.listdir(os.fsencode(path)):

      sb_song = {
        "internal_id": "",
        "title": "",
        "author":"",
        "copyright": "",
        "filename": ""
      }

      filename = os.fsdecode(file)

      if filename.endswith('.sng'):

        with open(f"{path}/{filename}", mode="r", encoding="Latin-1") as songfile:
            
          content = songfile.readlines()

          sb_song.update({"internal_id": filename.split('-')[0]})
          sb_song.update({"path": f"{path}/{filename}"})

          for line in content:
            
            if line.startswith("#Title="):
              sb_song.update({"title": line.removeprefix("#Title=").rstrip("\n")})
            elif line.startswith("#Author="):
              sb_song.update({"text": line.removeprefix("#Author=").rstrip("\n")})
            elif line.startswith("#Melody="):
              sb_song.update({"melody": line.removeprefix("#Melody=").rstrip("\n")})
            elif line.startswith("#(c)="):
              sb_song.update({"copyright": line.removeprefix("#(c)=").rstrip("\n")})

          
          # Fallback, if there is no title field
          if sb_song["title"] == "":

            logger.debug(f"Title is missing in file {filename}. Adding to fix list.")
            self.files_without_title.append(
              {
                "path": path,
                "filename": filename
              }
            )
            sb_song.update({"title": filename.removesuffix(".sng")})

            
          
          # Combine text and melody
          if "melody" in sb_song.keys() and "text" in sb_song.keys():
            sb_song.update({"author": f"{sb_song["text"]}, {sb_song["melody"]}"})
          elif "text" in sb_song.keys():
            sb_song.update({"author": f"{sb_song["text"]}"})
          else:
            sb_song.update({"author": ""})

          sb_songs.append(sb_song)

    return sb_songs


  def _fix_missing_title(self, files):

    for file in files:

      content = []

      logger.debug(f"Fixing title for {file["filename"]}")

      with open(file["path"] + file["filename"], mode="r", encoding="Latin-1") as songfile:

        content = songfile.readlines()
        content.insert(1, f"#Title={file["filename"].removesuffix(".sng")}\n")

      with open(file["path"] + file["filename"], mode="w", encoding="Latin-1") as songfile:

        songfile.writelines(content)
