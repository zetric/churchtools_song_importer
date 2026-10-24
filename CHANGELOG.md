# 1.4.1

- 🆕 FILE ONLY mode: Add support for song files where no number should be parsed

# 1.4

- 🆕 Add workload type "file" for workloads where only files are echoed by their file names without any metadata
- 🔁 Songbeamer song files in the source must now use a whitespace instead of an hyphen as separator between song number and title

# 1.3.3

- 🐞 Fix gesangbuch.txt mount

# 1.3.2

- 🐞 Fix Dockerfile command

# 1.3.1

- 🐞 Fix secret config mount

# 1.3

- 🔁 Change from env vars to config file logic
- 🆕 Add support for multiple workloads
- Sources and types are now written as full word for better understanding

# 1.2.2

- 🆕 Add cleanup mode to always represent the state of the source in ChurchTools
- 🐞 Fix handling of missing local file for GB songs (title gets extension)

# 1.0

Initial release
