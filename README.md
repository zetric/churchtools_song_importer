# Churchtools song importer

Imports two types of "songs" to Churchtools:

- "Gesangbuchlieder" in PPTX format, the metadata comes from the electronic EmK Gesangbuch (exported as textfile, see structure below)
- Songbeamer files including metadata if present in the .sng file

## TL;DR

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

### Manual CSV file changes

To be done in some editor with regex before using in this script

```
Search: (^1\. .*) T:
Replace: $1\nT:
```
```
Search: ^(?!Q:).+(T:.*)
Replace: $1\n$2
```
```
Search: (^[0-9]+[a-z]* .*)
Replace: <END>\n<START>\n$1
```
Plus modifying start and end of file.


### Prepare file `variables` with paths

```bash
#!/bin/bash

export GB_TXT_FILE="gesangbuch.txt"
export GB_PPT_PATH="path/to/Gesangbuch/"
export SB_FILE_PATH="/path/to/SongBeamerFolien/"
export CT_URL="https://mychurch.church.tools/api" 
export CT_API_TOKEN="mysecrettokenhere"
export CT_SONG_CATEGORY_GB="Gesangbuchlieder"
export CT_SONG_CATEGORY_SB="Lobpreislieder"
```

Source the file

```bash
source variables
```

### Run the script

```bash
usage: churchtools_song_importer.py [-h] [-d] [-a] [-t CATEGORY]

options:
  -h, --help   show this help message and exit
  -d           delete mode (deletes all songs of this category!)
  -a           add mode
  -t CATEGORY  gb (Gesangbuch), sb (Songbeamer)
```


## ℹ️ Structure of one entry

```
2 Großer Gott, wir loben dich
1. 2. 3. 4. 5. 6. 7. 8. 9. 10. 11. T: (Nach "Te Deum laudamus" 4. Jh.) Ignaz Franz 1768 / AÖL 1973/1978
M: Wien um 1776 / Leipzig 1819
S: Thomas Wegst 1999
Q: S: Rechte bei den Urhebern
In anderen Gesangbüchern: EG331 ö, FL30, GL257 ö, KG175 (ö), RG247 (ö)
```

Can have more or less lines but this is the minimum and preferred structure. Minumum is the title.

