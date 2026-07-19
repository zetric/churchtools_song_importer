# Churchtools song importer

Imports two types of "songs" into ChurchTools:

- "Gesangbuchlieder"
  - the metadata comes from the electronic EmK Gesangbuch (exported as textfile, see structure below)
- Songbeamer files
  - including metadata if present in the .sng file

The source can be a local folder or a Nextcloud folder. When running again, it updates the destination files accordingly.

## TL;DR

For running locally, change to the `source` folder.

### Prerequisites

Requirements: Python 3

Set up a python virtual environment in this folder and activate it

```bash
python3 -m venv venv
source venv/bin/activate
```

Install missing modules

```bash
pip install -r requirements.txt
```

### Manual file changes for Gesangbuch export


Read a txt file that is an export from "EM elektronisch"
 
Structure of one entry:

```
2 Großer Gott, wir loben dich
1. 2. 3. 4. 5. 6. 7. 8. 9. 10. 11.
T: (Nach "Te Deum laudamus" 4. Jh.) Ignaz Franz 1768 / AÖL 1973/1978
M: Wien um 1776 / Leipzig 1819
S: Thomas Wegst 1999
Q: S: Rechte bei den Urhebern
In anderen Gesangbüchern: EG331 ö, FL30, GL257 ö, KG175 (ö), RG247 (ö)
```

Can have more or less lines but this is the minimum and preferred structure. Minumum is the title.

Manual file changes do be done in some editor with regex before using in this script:

```
Search: (^1\. .*) T:
Replace: $1\nT:

Search: ^(?!Q:).+(T:.*)
Replace: $1\n$2

Search: (^[0-9]+[a-z]* .*)
Replace: <END>\n<START>\n$1
Plus modifying start and end of file
```

### Prepare file `variables` with paths

Check `chart/values.yaml` for `environments` and create a file `variables` like this:

```bash
# Delete mode
export CMD_DELETE="False"
# Add mode
export CMD_ADD="True"
# Cleanup songs without an internal ID after running (be careful!)
export CMD_CLEANUP="False"
# Type of songs to handle (gb or sb or both comman separated)
export TYPE="sb"
...
```

Source the file

```bash
source variables
```

### Run the script

When you have set all required environment variables, you can run the script just like this:

```bash
python3 churchtools_song_importer.py
```

In case you want to only use the command line or want to overwrite env vars, you can do so.<br>
Be careful with credentials that might be stored in the shell history!

```bash
usage: churchtools_song_importer.py [-h] [-d] [-a] [-c] [-t TYPE] [-s SOURCE] [-n NUMBER] [--skip-update] [--gb-txt-file GB_TXT_FILE] [--gb-file-path GB_FILE_PATH] [--sb-file-path SB_FILE_PATH] [--nextcloud-url NEXTCLOUD_URL]
                                    [--nextcloud-user NEXTCLOUD_USER] [--nextcloud-pass NEXTCLOUD_PASS] [--ct-url CT_URL] [--ct-api-token CT_API_TOKEN] [--ct-song-category-gb CT_SONG_CATEGORY_GB]
                                    [--ct-song-category-sb CT_SONG_CATEGORY_SB] [--ct-song-arrangement-name CT_SONG_ARRANGEMENT_NAME] [--ct-campus-name CT_CAMPUS_NAME] [--loglevel LOGLEVEL]

options:
  -h, --help            show this help message and exit
  -d, --delete          deletes all songs of this category before doing anything else
  -a, --add             add mode
  -c, --cleanup         Remove all songs that do not contain an internal ID and were therefore not managed by this script (be careful!)
  -t TYPE, --type TYPE  gb (Gesangbuch), sb (Songbeamer)
  -s SOURCE, --source SOURCE
                        nc (nextcloud), local
  -n NUMBER, --number NUMBER
                        Single song number to add or sync
  --skip-update         Skip update of existing songs and only crete new ones
  --gb-txt-file GB_TXT_FILE
                        Path to the TXT file with the Gesangbuch metadata
  --gb-file-path GB_FILE_PATH
                        Path to the Gesangbuch slides files
  --sb-file-path SB_FILE_PATH
                        Path to the Songbeamer song files
  --nextcloud-url NEXTCLOUD_URL
                        URL of the nextcloud instance
  --nextcloud-user NEXTCLOUD_USER
                        User for the nextcloud instance
  --nextcloud-pass NEXTCLOUD_PASS
                        Password for the nextcloud instance
  --ct-url CT_URL       URL of the ChurchTools instance
  --ct-api-token CT_API_TOKEN
                        API token for the ChurchTools instance
  --ct-song-category-gb CT_SONG_CATEGORY_GB
                        ChurchTools category for Gesangbuch songs
  --ct-song-category-sb CT_SONG_CATEGORY_SB
                        ChurchTools category for Songbeamer songs
  --ct-song-arrangement-name CT_SONG_ARRANGEMENT_NAME
                        ChurchTools arrangement name to use
  --ct-campus-name CT_CAMPUS_NAME
                        Campus name of the congregation to filter for the correct category
  --loglevel LOGLEVEL   Loglevel
```

## Running as microservice

If you know how deploy a helm chart, you can run the script in a Kubernetes cluster as cron job. Check out the structure under `chart`.