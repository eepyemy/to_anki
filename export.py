import json
import os
from datetime import datetime
import anki_connect
import kobo_connect
import koreader_connect
import json_connect, csv_connect
import deepl
import copy
from googletrans import Translator
from glob import glob
from pystardict import Dictionary
import traceback



PROPERTIES={}
if not os.path.exists("PROPERTIES.env"):
  print("PROPERTIES.env is not there, creating default one...")
  with open("PROPERTIES.env", "w", encoding="utf-8") as f:
    f.write("//[optional] api key for DeepL translator, Google used by default\nDEEP_L_AUTH_KEY=\n\n//choose between koreader and kobo\nDEVICE=koreader\n\n//[optional]cloud directory on your pc\nCLOUD_DIR=\n\n//name of the anki deck where all imported data will be stored\nMAIN_DECK=Default\n\n//[optional] specify the full name of anki deck, you want this program to import cards from. you can add more lines following the same naming pattern for other languages you are learning. \nEN_IMPORT_FROM=\nNL_IMPORT_FROM=\n\n[optional] name of the field where the word is being stored in your {lang}_IMPORT_FROM deck.\nIMPORT_FIELD=Word\n\n//name of the deck for imported words from koreader\nIMPORT_WORDS_TO=Words_Reading\n\n//name of the deck for imported notes from koreader\nIMPORT_NOTES_TO=Notes_Reading\n\n//name of the deck for imported study questions from koreader\nIMPORT_STUDY_TO=Study\n\n//language to which you want things to be translated. change to your native language\nTO_LANGUAGE=EN\n\n//Marker folders in koreader, that will signal that a book in that folder has a purpose of learning particular language or just study folder. List all such folders for every lang you are willing to import using ,(comma)\n\nEN=Learn_EN,Other_Learn_EN\nNL=Learn_NL\nSTUDY=Study\n\n//Names of the anki cards models for words and for notes, change if using non default anki model\n\nNOTE_MODEL_NAME=Anki Learn sentences\nWORD_MODEL_NAME=Anki Learn words\nSTUDY_MODEL_NAME=Anki Learn sentences\n\n//Names of the anki cards front and back fields for words, notes and study cards, change if using non default anki model\n\nNOTE_FRONT_FIELD=Question\nNOTE_BACK_FIELD=Answer\n\nWORD_FRONT_FIELD=Word\nWORD_BACK_FIELD=Definitions\n\nSTUDY_FRONT_FIELD=Question\nSTUDY_BACK_FIELD=Answer\n\n")

with open("PROPERTIES.env", "r", encoding="utf-8") as f:
  PROPERTIES = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in 
  x and x.strip("\n")[-1]!="="}

print(PROPERTIES)



def str_to_date(str):
  return datetime.strptime(str, '%Y-%m-%dT%H:%M:%SZ')

def get_param(param_name, default=None):
  return PROPERTIES.get(param_name, default)

FROM_LANGS = [x for x in PROPERTIES if len(x)==2]

FROM_LANGS = {x:get_param(f"{x}_IMPORT_FROM") for x in FROM_LANGS}

MAIN_DECK = get_param("MAIN_DECK", "Default")
IMPORT_WORDS_TO = get_param("IMPORT_WORDS_TO", "Words_Reading")
IMPORT_NOTES_TO = get_param("IMPORT_NOTES_TO", "Notes_Reading")
IMPORT_FIELD = get_param("IMPORT_FIELD", "Front")

NOTE_MODEL_NAME = get_param("NOTE_MODEL_NAME", "Basic")
WORD_MODEL_NAME = get_param("WORD_MODEL_NAME", "Basic")

WORD_FRONT_FIELD = get_param("WORD_FRONT_FIELD", "Front")
WORD_BACK_FIELD = get_param("WORD_BACK_FIELD", "Back")
NOTE_FRONT_FIELD = get_param("NOTE_FRONT_FIELD", "Front")
NOTE_BACK_FIELD = get_param("NOTE_BACK_FIELD", "Back")

TO_LANG = get_param("TO_LANGUAGE")
USE_GOOGLE=get_param("USE_GOOGLE", False)
USE_DICTS=get_param("USE_DICTS", True)
TRY_DOWNLOAD=False

def get_dicts():
  dicts = []
  dicts = glob("dict/**/*.ifo") + glob("dict/**/**/*.ifo")
  return dicts


dicts = get_dicts()
# print(dicts)
if not dicts and USE_DICTS:
  print(os.getcwd())
  print("Didnt find any dicts in working directory, trying to download...")
  TRY_DOWNLOAD=True


translator = None
google_translator = None


def check_reqs(list_params, raise_error=True):
  result = True
  for a in list_params:
    if not PROPERTIES.get(a):
      if raise_error:
        raise ValueError(f"Couldn't find {a} in PROPERTIES.env")
      else:
        print(f"Couldn't find {a} in PROPERTIES.env")
      result = False
  return result
  

def main():
  global translator, google_translator, dicts, USE_GOOGLE
  auth_key = PROPERTIES.get("DEEP_L_AUTH_KEY", "")
  try:
    translator = deepl.Translator(auth_key)
  except Exception as e:
    USE_GOOGLE = True
    print(e)
    print("Probably your deepl key is not valid, using Google translator...")
  google_translator = Translator()
  
  device = None
  if "DEVICE" not in PROPERTIES:
    print("Aborting, DEVICE propertiy is not set")
    return None
  if PROPERTIES["DEVICE"] == "koreader":
    device = koreader_connect.Koreader(download_dicts=TRY_DOWNLOAD)
  elif PROPERTIES["DEVICE"] == "kobo":
    device = kobo_connect.Kobo()
  elif PROPERTIES["DEVICE"] == "json":
    device = json_connect.Json()
  elif PROPERTIES["DEVICE"] == "csv":
    device = csv_connect.Csv()
  

  if not device:
    print("Device is not connected")
  
  if not FROM_LANGS:
    print("No language properties are set, need at least one language. Aborting")
    return None

  if not os.path.exists("custom_dicts_order.json"):
    with open("custom_dicts_order.json", "w", encoding="utf-8") as f:
      json.dump({os.path.basename(x):0 for x in get_dicts()}, f)

  custom_dicts_order = {}
  with open("custom_dicts_order.json", "r", encoding="utf-8") as f:
    custom_dicts_order = json.load(f)
  custom_dicts_order = {f"{x}.ifo" if x.split(".")[-1]!="ifo" else x : y for x,y in custom_dicts_order.items()}
  custom_dicts_order = {x:y for x,y in custom_dicts_order.items() if y!=0}

  with open("custom_dicts_order.json", "w", encoding="utf-8") as f:
    a = {os.path.basename(x):0 for x in get_dicts()}
    a.update(custom_dicts_order)
    json.dump(a, f)

  #print(custom_dicts_order)
  dicts = get_dicts()
  #print(dicts)
  dicts = {os.path.basename(x):Dictionary(x[:-4]) for x in dicts}
  dicts_order = device.get_dict_order()
  dicts_order = {os.path.basename(x):y for x,y in dicts_order.items()}
  dicts_order.update(custom_dicts_order)

  #print(dicts_order)
  if dicts_order or dicts:
    temp_len = max(list(dicts_order.values())+[len(dicts)])
  else:
    temp_len = 0
  sorted_dicts = [1]*temp_len
  for dn,d in dicts.items():
    place = dicts_order.get(dn)
    if not place:
      sorted_dicts.append(d)
      continue
    sorted_dicts[place-1] = d
  sorted_dicts = [x for x in sorted_dicts if isinstance(x, Dictionary)]
  #print(sorted_dicts)
  dicts = sorted_dicts
  
  last_time = {}
  try:
    with open("last_sync.json", "r", encoding="utf-8") as f:
      last_time = json.load(f)
  except:
    pass#print("No file last_sync.json....")
  
  dates = []
  for lang in FROM_LANGS:
    print()
    print(f"Exporting from {lang} language...")
    print()
    dates.append(export_lang(device, lang))

  print()
  print(f"Exporting study questions...")
  print()
  study_date = ""
  study_date = export_study(device)
  if study_date:
    last_time['study'] = study_date
  dates_notes = [x.get('notes') for x in dates if x.get('notes',"")!=""]
  dates_words = [x.get('words') for x in dates if x.get('words',"")!=""]
  print(dates_notes, dates_words)
  if dates_notes:
    last_time_notes = max(dates_notes, key=lambda x: str_to_date(x))
    last_time['notes'] = last_time_notes
  if dates_words:
    last_time_words = max(dates_words, key=lambda x: str_to_date(x))
    last_time['words'] = last_time_words
  if not last_time:
    last_time = {}
  print("saving", last_time)
  with open("last_sync.json", "w") as k:
    json.dump(last_time, k)
    print("saving last sync date...")
  
  try:
    if not USE_GOOGLE:
      translator.close()
  except Exception as e:
    print("something wrong with closing translator...", e)

def translate(text, from_lang):
  #print(f"translating: '{text}'...")
  if USE_GOOGLE:
    result = ""
    try:
      result = "[Google]:"+google_translator.translate(text, src=from_lang, dest=TO_LANG).text
    except Exception as e:
      print("There was a problem with Google Translate, ", e)
    return result 
  
  usage = translator.get_usage()
  if text:
    if usage.character.count + len(text) > usage.character.limit:
      print("Out of limit.")
      return None
    else:
      return "[DeepL]:"+translator.translate_text(text, target_lang=TO_LANG, source_lang=from_lang.upper(), formality="less").text

# generate words from dicts or from google translate if dicts are not available
def generate(words, lang, import_words_to):
  fields = anki_connect.invoke("modelFieldNames", modelName=WORD_MODEL_NAME)
  ids = []
  note_blueprint = {"deckName": import_words_to,
                  "modelName": WORD_MODEL_NAME,
                  'fields': {x:'' for x in fields},
                  "options": {
                      "allowDuplicate": False,
                      "duplicateScope": "deck",
                  },
                  }
  notes = []
  
  for i, word in enumerate(words):
    note = copy.deepcopy(note_blueprint)
    note['fields'][WORD_FRONT_FIELD] = word
    if USE_DICTS:
      definitions = []
      for dictionary in dicts:
        result = dictionary.get(word)
        if result:
          definitions.append(result)
      if definitions:
        note['fields'][WORD_BACK_FIELD] = ''.join('<div class="definition">'+x+'</div>' for x in definitions)
      else:
        note['fields'][WORD_BACK_FIELD] = f'<div class="definition">{translate(word, lang)}</div>'
    else:
      note['fields'][WORD_BACK_FIELD] = f'<div class="definition">{translate(word, lang)}</div>'
    notes.append(note)

  ids = anki_connect.invoke("addNotes", notes=notes)

def export_study(device):
  
  if not check_reqs(["STUDY_FRONT_FIELD", "STUDY_BACK_FIELD", "STUDY_MODEL_NAME"], raise_error=False):
    return ""

  if type(device).__name__ != "Koreader" or "STUDY" not in PROPERTIES:
    return ""
  
  device.connect()
  
  last_sync = ""
  try:
    with open("last_sync.json", "r", encoding="utf-8") as f:
      last_sync = json.load(f)
  except:
    print("No file last_sync.json....")
  

  if last_sync == "":
    sync_all = True
    study_from_date = datetime(1970, 1, 1, 1, 1, 1, 1)
  else:
    sync_all = False
    study_from_date = last_sync.get("study")
  
    if study_from_date:
      study_from_date = str_to_date(study_from_date)
    else:
      study_from_date = datetime(1970, 1, 1, 1, 1, 1, 1)

  print(f"syncing all study questions... from {study_from_date}")
  
  notes = device.get_notes(study_from_date, "STUDY", study=True)
  notes = [[x[1], x[0], x[2]] for x in notes if x[1] != None and x[1].strip() != '']
  print(f"Got {len(notes)} study questions...")
  
  if len(notes)>0:
    fields = anki_connect.invoke("modelFieldNames", modelName=PROPERTIES.get("STUDY_MODEL_NAME"))
    ids = []
    note_blueprint = {"deckName": "",
                    "modelName": PROPERTIES.get("STUDY_MODEL_NAME"),
                    'fields': {x:'' for x in fields},
                    "options": {
                        "allowDuplicate": False,
                        "duplicateScope": "deck",
                    },
                    }
    decks = []
    for i, note1 in enumerate(notes.copy()):
      note = copy.deepcopy(note_blueprint)
      note['deckName'] = f"{MAIN_DECK}::{PROPERTIES.get('IMPORT_STUDY_TO', 'Study')}::{os.path.basename(note1[2])}"
      decks.append(note["deckName"])
      #print(note['deckName'])
      note['fields'][PROPERTIES.get("STUDY_FRONT_FIELD")] = note1[0]
      note['fields'][PROPERTIES.get("STUDY_BACK_FIELD")] = note1[1]
      notes[i] = note

    decks = list(set(decks))
    for deck in decks:
      anki_connect.invoke("createDeck", deck=deck)
    
    ids = anki_connect.invoke("addNotes", notes=notes)

    date = device.get_latest_date().get("study")
    if date:
      last_sync = date
    
    device.close()

    with open("history.txt", "a") as f:
      if last_sync:
        f.write(f"\n[{last_sync}][STUDY]: {len(ids)} study questions imported.")
    return last_sync

def export_lang(device, lang):

  check_reqs(["WORD_FRONT_FIELD", "WORD_BACK_FIELD", "WORD_MODEL_NAME", "NOTE_FRONT_FIELD", "NOTE_BACK_FIELD", "NOTE_MODEL_NAME"])

  device.connect()
  FROM_LANG=lang
  IMPORT_WORDS_FROM = FROM_LANGS[lang]
  import_notes_to= f"{MAIN_DECK}::{lang}::{IMPORT_NOTES_TO}"
  import_words_to=f"{MAIN_DECK}::{lang}::{IMPORT_WORDS_TO}"
  anki_connect.invoke("createDeck", deck=import_notes_to)
  anki_connect.invoke("createDeck", deck=import_words_to)
  
  last_sync = {}
  try:
    with open("last_sync.json", "r", encoding="utf-8") as f:
      last_sync = json.load(f)
  except:
    print("No file last_sync.json....")
  

  if not last_sync:
    sync_all = True
    notes_from_date = datetime(1970, 1, 1, 1, 1, 1, 1)
    words_from_date = datetime(1970, 1, 1, 1, 1, 1, 1)
  else:
    sync_all = False

    notes_from_date = last_sync.get("notes")
    words_from_date = last_sync.get("words")

    if notes_from_date:
      notes_from_date = str_to_date(notes_from_date)
    else:
      notes_from_date = datetime(1970, 1, 1, 1, 1, 1, 1)
    
    if words_from_date:
      words_from_date = str_to_date(words_from_date)
    else:
      words_from_date = datetime(1970, 1, 1, 1, 1, 1, 1)
  
  print(f"syncing all notes... from {notes_from_date}")
  print(f"syncing all words... from {words_from_date}")
  
  words = device.get_words(words_from_date, FROM_LANG)
  notes = device.get_notes(notes_from_date, FROM_LANG)
  notes = [[x[0], translate(x[0], lang)] for x in notes if x[1] == None or x[1].strip() == '']

  
  

  prev_translations = {}
  try:
    with open("translations.json", "r", encoding="utf-8") as f:
      prev_translations = json.load(f) 
  except Exception as e:
    print("No file for prev translations, creating one...", e)
  prev_translations.update(dict(notes))
  with open("translations.json", "w", encoding="utf-8") as f:
    json.dump(prev_translations, f)


    

  # print(notes)
  ids = []
  left_out_words = words
  amount_words = 0
  if len(words)>0:
    ids = []
    query_words = ''.join(f'"deck:{IMPORT_WORDS_FROM}" AND "{IMPORT_FIELD}:{word}" AND "is:suspended" AND -"deck:{import_words_to}"' + ' OR ' for word in words)[:-4]
    
    if not PROPERTIES.get("SKIP_REPEATS_CHECK"):
      ids = anki_connect.invoke("findCards", query=query_words)
    
    repeats = []
    if len(ids) > 0:
      imported_words = anki_connect.invoke("cardsInfo", cards=ids)
      imported_words = [x['fields'][IMPORT_FIELD]['value'] for x in imported_words]
      amount_words+=len(imported_words)
      print(f"imported words from anki: {imported_words}")
      left_out_words = [item for item in words if item not in imported_words]
      anki_connect.invoke("changeDeck", cards=ids, deck=import_words_to)
      anki_connect.invoke("unsuspend", cards=ids)
    else:
      print("Couldn't find any word to import from anki, gonna try to generate from dicts")
    if left_out_words:
      repeat_ids = []
      query_words = ''.join(f'"deck:{MAIN_DECK}" AND "{IMPORT_FIELD}:{word}" AND -"is:suspended" OR "deck:{MAIN_DECK}" AND "{WORD_FRONT_FIELD}:{word}" AND -"is:suspended"' + ' OR ' for word in left_out_words)[:-4]
      if not PROPERTIES.get("SKIP_REPEATS_CHECK"):
        repeat_ids = anki_connect.invoke("findCards", query=query_words)
      repeats = anki_connect.invoke("cardsInfo", cards=repeat_ids)
      #repeats = [x['fields'][IMPORT_FIELD]['value'] for x in repeats]
      
      reps = []
      for card in repeats:
        imp = card['fields'].get(IMPORT_FIELD)
        gen = card['fields'].get(WORD_FRONT_FIELD)
        if gen:
          reps.append(gen['value'])
        if imp:
          reps.append(imp['value'])
      repeats = reps
      if repeats:
        print(f"avoided generating repeating words: {repeats}")
      left_out_words = [item for item in left_out_words if item not in repeats]
      
      
      if left_out_words:
        print(f"generating words: {left_out_words}")
      else:
        print("Skipping generating, words were already added previously...")
  
  len_words = len(words)
  if left_out_words:
    generate(left_out_words, lang, import_words_to)
  amount_words+=len(left_out_words)
  len_words = amount_words
  print(f"Got {len(notes)} notes...")
  print(f"Got {len_words} words...")

  if len(notes)>0:
    fields = anki_connect.invoke("modelFieldNames", modelName=NOTE_MODEL_NAME)
    ids = []
    note_blueprint = {"deckName": import_notes_to,
                    "modelName": NOTE_MODEL_NAME,
                    'fields': {x:'' for x in fields},
                    "options": {
                        "allowDuplicate": False,
                        "duplicateScope": "deck",
                    },
                    }
    for i, note1 in enumerate(notes.copy()):
      note = copy.deepcopy(note_blueprint)
      note['fields'][NOTE_FRONT_FIELD] = note1[0]
      note['fields'][NOTE_BACK_FIELD] = note1[1]
      notes[i] = note

    ids = anki_connect.invoke("addNotes", notes=notes)
  len_sentences = len(ids)
  latest_date = device.get_latest_date()
  latest_date = {x:y for x,y in latest_date.items() if y}
  last_sync.update(latest_date)
  print(latest_date)
  
  
  
  device.close()

  with open("history.txt", "a") as f:
    if last_sync.get('words'):
      f.write(f"\n[{last_sync.get('words')}][{lang}]: {len_words} words imported.")
    if last_sync.get('notes'):
      f.write(f"\n[{last_sync.get('notes')}][{lang}]: {len_sentences} sentences imported.")
  return last_sync


if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    if "No connection could be made" in str(e):
      e = "[ERROR]: AnkiConnect add-on is not installed or Anki is not running"
    print(traceback.format_exc())
    print(e)
  input("Press Enter to finish...")
