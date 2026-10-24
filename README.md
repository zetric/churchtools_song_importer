# Churchtools song importer

Imports three types of "songs" into ChurchTools:

- "Gesangbuchlieder"
  - the metadata comes from the electronic EmK Gesangbuch (exported as textfile, see structure below)
- Songbeamer files
  - including metadata if present in the .sng file
- General files ("file only" mode)
  - may be any PPTX or PDF or whatever files that are treated as song files
  - will not carry any metadata by their nature

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

### Handling of files

The Gesangbuch files must start with the song numer and a whitespace (e.g. `1 Mein Mund besinge tausendfach.pptx`)

The Songbeamer files must start with an individual number and a hyphen (e.g. `1 Mein Song.sng`)

Both song type files must be in individual folders.

This number is used as reference that will be stored in the arrangement of the song in ChurchTools.

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

### Prepare file `config.yaml`

Check `config.yaml.example` and create a `config.yaml` file like this


### Run the script

When you have set all required environment variables, you can run the script just like this:

```bash
python3 churchtools_song_importer.py --configfile config.yaml
```

General usage:

```bash
usage: churchtools_song_importer.py [-h] [--loglevel LOGLEVEL] [--configfile CONFIGFILE] [--workload WORKLOAD]

options:
  -h, --help            show this help message and exit
  --loglevel LOGLEVEL   Loglevel
  --configfile CONFIGFILE
                        Configfile
  --workload WORKLOAD   Workload name for single execution mode
```

Environment variables (overwritten by command line options, overwrite config entries):

`CONFIGFILE`<br>
`LOGLEVEL`

## Running as microservice

If you know how deploy a helm chart, you can run the script in a Kubernetes cluster as cron job. Check out the structure under `chart`.

