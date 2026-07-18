import re

class gesangbuch:

  def __init__(self):
    pass

  def read_gb_songs(self, file):

    # --- Read a txt file that is an export from "EM elektronisch"
    # 
    # Structure of one entry:
    #
    # 2 Großer Gott, wir loben dich
    # 1. 2. 3. 4. 5. 6. 7. 8. 9. 10. 11.
    # T: (Nach "Te Deum laudamus" 4. Jh.) Ignaz Franz 1768 / AÖL 1973/1978
    # M: Wien um 1776 / Leipzig 1819
    # S: Thomas Wegst 1999
    # Q: S: Rechte bei den Urhebern
    # In anderen Gesangbüchern: EG331 ö, FL30, GL257 ö, KG175 (ö), RG247 (ö)
    #
    # Can have more or less lines but this is the minimum and preferred structure. Minumum is the title.
    #
    # Manual file changes do be done in some editor with regex before using in this script:
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
        entry_set.update({'internal_id': number})
        entry_set.update({'title': str(re.findall(r'(?:^[0-9]+[a-z]*) (.*)(?:\n)', entry)[0]).strip()})
        if re.findall(r'(?:T: )(.*)(?:\n)', entry):
          entry_set.update({'author': str(re.findall(r'(?:T: )(.*)(?:\n)', entry)[0]).strip()})
        else:
            entry_set.update({'author':""})
        if re.findall(r'(?:M: )(.*)(?:\n)', entry):
          entry_set.update({'cr_music': str(re.findall(r'(?:M: )(.*)(?:\n)', entry)[0]).strip()})
        else:
            entry_set.update({'cr_music':""})
        if re.findall(r'(?:S: )(.*)(?:\n)', entry):
          entry_set.update({'cr_set': str(re.findall(r'(?:S: )(.*)(?:\n)', entry)[0]).strip()})
        else:
            entry_set.update({'cr_set':""})
        if re.findall(r'(?:Q: )(.*)(?:\n)', entry):
          entry_set.update({'copyright': str(re.findall(r'(?:Q: )(.*)(?:\n)', entry)[0]).strip()})
        else:
            entry_set.update({'copyright':""})

        txt_data[number].update(entry_set)

    return txt_data


  def filter_gb_songs(self, songs):

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