from time import sleep
import json
import os
import copy
import traceback

import anki_connect
import kobo_connect
import koreader_connect
import json_connect, csv_connect
from utility_funcs import *

from init import *
from translators import TranslatorsHandler

import typer
from rich import print
import inquirer
from inquirer import *

app = typer.Typer()

TRANSLATOR = None
DICTS = None

@app.command()
def main(
  type: str = CONFIG.get("DEVICE", None), 
  filename: str = None, 
  from_langs: str = "".join(f"{x} " for x in list(CONFIG["FROM_LANGS"].keys()))[:-1], 
  to_lang:str = CONFIG['TO_LANG'], 
  notes_deck_name:str = CONFIG['IMPORT_NOTES_TO'], 
  words_deck_name:str = CONFIG['IMPORT_WORDS_TO'], sleep_sec:int = None, 
  use_google: bool = CONFIG["USE_GOOGLE"], 
  skip_import : bool = CONFIG.get("SKIP_REPEATS_CHECK", False), 
  download_dicts : bool = CONFIG["TRY_DOWNLOAD"], 
  use_deepl:bool = CONFIG.get("USE_DEEPL", True),
  use_dicts:bool = CONFIG.get("USE_DICTS", True),
  setup:bool = False
  ):
  
  # intializing config variables
  global CONFIG, TRANSLATOR, DICTS
  CONFIG["SKIP_REPEATS_CHECK"] = skip_import
  CONFIG["USE_GOOGLE"] = use_google
  CONFIG["USE_DEEPL"] = use_deepl
  CONFIG["TO_LANG"] = to_lang
  CONFIG["FROM_LANGS"] = {x:get_param(f"{x}_IMPORT_FROM", "") for x in from_langs.split(" ")}
  CONFIG["FROM_LANGS"].pop("",None)
  CONFIG['IMPORT_WORDS_TO'] = words_deck_name
  CONFIG['IMPORT_NOTES_TO'] = notes_deck_name
  CONFIG["TRY_DOWNLOAD"] = download_dicts
  if filename:
    CONFIG["FILENAME"] = filename
  CONFIG["USE_DICTS"] = use_dicts
  if sleep_sec:
    print("Sleeping until system is stable...")
    sleep(sleep_sec)
  
  # initializing translator
  # TODO migrate translator init to init.py 
  TRANSLATOR = TranslatorsHandler(config=CONFIG)
  codes = TRANSLATOR.get_supported_langs(type="codes")
  a = TRANSLATOR.get_supported_langs(type="names")
  CONFIG["TRANSLATOR"] = TRANSLATOR
  CONFIG["SUPPORTED_LANGS"] = CONFIG["CUSTOM_LANGS"].copy()
  CONFIG["SUPPORTED_LANGS"].update(codes)
  #print(CONFIG["SUPPORTED_LANGS"])
  #CONFIG["SUPPORTED_LANGS"] = dict(sorted(list(set(langs.items())), key=lambda x: x[1])) 
  #print(CONFIG["FROM_LANGS"])
  
  if setup or CONFIG.get("WAS_SETUP","False")=="False":
    user_friendly_setup(save=CONFIG.get("WAS_SETUP","False"))
    type = CONFIG.get("DEVICE", type)
  CONFIG["FROM_LANGS"] = {x.upper():get_param(f"{x.upper()}_IMPORT_FROM", "") for x in CONFIG["FROM_LANGS"]}
  #print(CONFIG["FROM_LANGS"])
  #print(CONFIG)
  TRANSLATOR.update_config(CONFIG)
  TRANSLATOR.setup_translators()
  #print(TRANSLATOR.translate("Hello my name is Emy", "EN", "NL"))
  
  
  # setting device
  device = None
  if "DEVICE" not in CONFIG and type==None:
    print("Aborting, DEVICE propertiy is not set")
    return None
  if type == "koreader":
    device = koreader_connect.Koreader(download_dicts=CONFIG["TRY_DOWNLOAD"], config=CONFIG)
  elif type == "kobo":
    device = kobo_connect.Kobo(config=CONFIG)
  elif type == "json":
    device = json_connect.Json(config=CONFIG)
  elif type == "csv":
    device = csv_connect.Csv(config=CONFIG)
  
  print(device)
  if not device:
    print("Device is not connected")
  
  if not CONFIG["FROM_LANGS"]:
    print("No language properties are set, need at least one language. Aborting")
    return None

  # preparing dicts
  DICTS = load_dicts_ordered(device)
  #print(DICTS)
  #print(CONFIG["SUPPORTED_LANGS"])
  
  # loading previous sync dates
  sync_dates = get_sync_dates()
  
  # generating cards for every FROM language
  for lang in CONFIG["FROM_LANGS"]:
    print()
    print(f"Exporting from {get_lang_name(lang)} language...")
    print()
    sync_dates.extend(export_lang(device, lang))

  # generating study cards
  print()
  print(f"Exporting study questions...")
  print()
  
  sync_dates.extend(export_study(device))
  
  # drop ununique dates
  sync_dates = list(set(sync_dates))
  
  print("saving sync dates")
  with open("sync_dates.json", "w", encoding="utf-8") as k:
    json.dump(sync_dates, k)
  
  TRANSLATOR.close()

def get_lang_name(code):
  codes = {x.upper():y for x,y in CONFIG["SUPPORTED_LANGS"].items()}
  return codes.get(code.upper(), code)

# TODO migrate it to init.py
def user_friendly_setup(first_setup=False, save=True):
  global CONFIG
  def update(a,b,vals_to_ignore=["", None]):
    a.update((k,v) for k,v in b.items() if v not in vals_to_ignore)
    return a

  
  codes = CONFIG["SUPPORTED_LANGS"].copy()
  langs = [(x,y) for y,x in codes.items()]
  
  
  basic_setup = [
    inquirer.List(
      "DEVICE","Select default device for export of notes",choices=["koreader", "kobo", "csv", "json"]
    ),
    inquirer.Text("FILENAME","Enter filename to export words and sentences from",ignore=lambda x:x["DEVICE"] not in ["csv", "json"], default=""),
    inquirer.List("USUAL_CASE","Do you use languages that are not supported by common translators?",[("Yes",True),("No", False)],False),
    inquirer.Text("CUSTOM_LANGS","(optional) Enter custom language codes and their names via colon, separating each new pair with a comma",ignore=lambda x: not x["USUAL_CASE"], default="")]
  
  
  translators_setup = [
    inquirer.Checkbox("TRANS_USE", 
      f"Select translators you want to use", 
      choices=[(f"{x.title()}", 
                (f"USE_{x.upper()}", True)) 
               for x in CONFIG["TRANSLATOR"].translators], 
      default=[(f"USE_{x.upper()}", True) 
               for x in CONFIG["TRANSLATOR"].translators],
      ignore=lambda x: list_input("Do you want to use all available translators?",choices=[("Yes",True), ("No", False)], default=True))
  ]
  

  '''
  (print(f"USE_{name.upper()}",not dict(x["TRANS_USE"]).get(f"USE_{name.upper()}", False)), not dict(x["TRANS_USE"]).get(f"USE_{name.upper()}", False))
  '''
  
  anki_custom_setup=[
    inquirer.Text("MAIN_DECK", "Main deck name (default:Language Learning)","Language Learning"),
    inquirer.Text("IMPORT_WORDS_TO", "Words deck name(default:Words_Reading)","Words_Reading"),
    inquirer.Text("WORD_MODEL_NAME", "Anki model name for words cards(default:Anki Learn words)","Anki Learn words"),
    inquirer.Text("WORD_FRONT_FIELD", "Front field name for words cards(default:Word)","Word"),
    inquirer.Text("WORD_BACK_FIELD", "Back field name for words cards(default:Definitions)","Definitions"),
    
    
    inquirer.Text("IMPORT_NOTES_TO", "Sentences deck name(default:Notes_Reading)","Notes_Reading"),
    inquirer.Text("NOTE_MODEL_NAME", "Anki model name for sentences cards(default:Anki Learn sentences)","Anki Learn sentences"),
    inquirer.Text("NOTE_FRONT_FIELD", "Front field name for sentences cards(default:Question)","Question"),
    inquirer.Text("NOTE_BACK_FIELD", "Back field name for sentences cards(default:Answer)","Answer"),
    
    
    inquirer.Text("IMPORT_STUDY_TO", "Study questions deck name(default:Study)"),
    inquirer.Text
    ("STUDY_MODEL_NAME", "Anki model name for study questions cards(default:Anki Learn sentences)","Anki Learn sentences"),
    
    inquirer.Text("STUDY_FRONT_FIELD", "Front field name for study questions cards(default:Question)","Question"),
    inquirer.Text("STUDY_BACK_FIELD", "Back field name for study questions cards(default:Answer)","Answer")
    
  ]
  
  if first_setup:
    save = True
    
  answers = update({}, prompt(basic_setup))
  custom_langs = {}
  custom_codes = {}
  if "CUSTOM_LANGS" in answers:
    custom_langs = {x.split(":")[1]:x.split(":")[0] for x in answers["CUSTOM_LANGS"].split(",")}
    custom_codes = {x.split(":")[0]:x.split(":")[1] for x in answers["CUSTOM_LANGS"].split(",")}
  tempo = langs.copy()
  langs = custom_langs.copy()
  langs.update(tempo)
  langs = [(x,y) for x,y in langs.items()]
  codes.update(custom_codes)
  CONFIG["SUPPORTED_LANGS"] = codes
  answers.pop("USUAL_CASE")
  
  langs_setup = [
    inquirer.Checkbox(
        "FROM_LANGS",
        message="Select default input languages (Space -> Select, Enter -> Confirm)",
        choices=langs,
    ),
    inquirer.List(
        "TO_LANG",
        message="Select default output language",
        choices=langs,
    ),
    inquirer.Text("CLOUD_DIR", "[optional] Path to cloud directory on your pc (local copy)")
  ]
  
  answers = update(answers, prompt(langs_setup))
  print(answers)
  koreader_specific = [inquirer.Text(x.upper(),f"Enter comma separated folder names form KOreader for books in {codes[x]} language",ignore=lambda _: answers["DEVICE"]!="koreader", default="") for x in answers["FROM_LANGS"]]
  
  answers = update(answers, prompt(koreader_specific))
  
  tr = prompt(translators_setup)
  tr.update(tr["TRANS_USE"])
  tr.pop("TRANS_USE")
  answers = update(answers, tr)
  api = []
  not_used_tranlators = {}
  for name, options in CONFIG["TRANSLATOR"].translators.items(): 
    
    doesnt_need = not options["needs_auth_key"]
    not_use = not answers.get(f"USE_{name.upper()}", False)
    if not_use:
      not_used_tranlators[f"USE_{name.upper()}"] = False
    has_api = not ""==CONFIG.get(f"{name.upper()}_AUTH_KEY", "")
    
    ignore_ = not_use or doesnt_need or has_api
    #print(name, ("no auth",doesnt_need), ("dont use",not_use), ("has api",has_api), ("ignore", ignore_))
    question = inquirer.Text(
      f"{name.upper()}_AUTH_KEY",
      f"Please enter API key for {name.title()}",
      default="",
      ignore=ignore_
    )
    api.append(question)
  #print(answers)
  #print(CONFIG)
  answers = update(answers, prompt(api))
  answers = update(answers, not_used_tranlators)
  
  do_anki_setup = list_input("[optional] Do you want to customize anki related settings?",choices=[ ("No", False),("Yes", True)], default=False)
  if do_anki_setup:
    answers = update(answers, prompt(anki_custom_setup))
  
  CONFIG.update(answers)
  do_save = list_input("Do you want to save the settings?",choices=[ ("No", False),("Yes", True)], default=True if save=="False" else False)
  if do_save:
    to_save = CONFIG.copy()
    if not to_save.get("CUSTOM_LANGS",{}):
      to_save.pop("CUSTOM_LANGS",None)
    to_save.pop("TRY_DOWNLOAD",None)
    to_save.pop("WAS_SETUP",None)
    to_save.pop("DICT_PATHS",None)
    to_save.pop("SUPPORTED_LANGS",None)
    to_save.pop("FROM_LANGS",None)
    to_save.pop("TRANSLATOR",None)
    to_save["TO_LANG"] = to_save["TO_LANG"].upper()
    print(to_save)
    
    print("Saving newly made config...")
    with open("PROPERTIES.env", "w", encoding="utf-8") as f:
      for k,v in to_save.items():
        f.write(f"\n{k}={v}")
      f.write("\nWAS_SETUP=True")
    # TODO think of a better structure for setup



# generate cards from dicts or from google translate if dicts are not available
def generate_cards(words, lang, import_words_to):
  fields = anki_connect.invoke("modelFieldNames", modelName=CONFIG["WORD_MODEL_NAME"])
  ids = []
  note_blueprint = {"deckName": import_words_to,
                  "modelName": CONFIG["WORD_MODEL_NAME"],
                  'fields': {x:'' for x in fields},
                  "options": {
                      "allowDuplicate": False,
                      "duplicateScope": "deck",
                  },
                  }
  notes = []
  translations = []
  for word in words:
    note = copy.deepcopy(note_blueprint)
    note['fields'][CONFIG["WORD_FRONT_FIELD"]] = word
    if CONFIG["USE_DICTS"]:
      definitions = []
       
      subdicts = DICTS.get(lang.upper(), DICTS["others"])
      for dictionary in subdicts:
        result = dictionary.get(word)
        if result:
          definitions.append(result)
      if definitions:
        note['fields'][CONFIG["WORD_BACK_FIELD"]] = ''.join('<div class="definition">'+x+'</div>' for x in definitions)
      else:
        t = (word, TRANSLATOR.translate(word, from_=lang))
        translations.append(t)
        note['fields'][CONFIG["WORD_BACK_FIELD"]] = f'<div class="definition">{t[1]}</div>'
    else:
      t = (word, TRANSLATOR.translate(word, from_=lang))
      translations.append(t)
      note['fields'][CONFIG["WORD_BACK_FIELD"]] = f'<div class="definition">{t[1]}</div>'
    notes.append(note)
  from_to = f"{lang}{CONFIG['TO_LANG']}"
  translations = [(x,t) for x,t in translations 
                  if t!="No translation available"]
  TRANSLATOR.update_previous_translations(
    dict(translations),from_to)
  ids = anki_connect.invoke("addNotes", notes=notes)

# exports all notes from study books as question-answer cards
def export_study(device):
  sync_dates = []
  if not check_reqs(["STUDY_FRONT_FIELD", "STUDY_BACK_FIELD", "STUDY_MODEL_NAME"], raise_error=False):
    return []

  if type(device).__name__ != "Koreader" or "STUDY" not in CONFIG:
    return []
  
  device.connect()

  print(f"syncing all study questions...")
  
  notes,notes_dates = device.get_notes("STUDY")
  notes,notes_dates = get_new_items(notes, notes_dates)
  
  notes = [[x[1], x[0], x[2]] for x in notes if x[1] != None and x[1].strip() != '']
  print(f"Got {len(notes)} study questions...")
  
  if len(notes)>0:
    fields = anki_connect.invoke("modelFieldNames", modelName=CONFIG.get("STUDY_MODEL_NAME"))
    ids = []
    note_blueprint = {"deckName": "",
                    "modelName": CONFIG.get("STUDY_MODEL_NAME"),
                    'fields': {x:'' for x in fields},
                    "options": {
                        "allowDuplicate": False,
                        "duplicateScope": "deck",
                    },
                    }
    decks = []
    for i, note1 in enumerate(notes.copy()):
      note = copy.deepcopy(note_blueprint)
      note['deckName'] = f"{CONFIG['MAIN_DECK']}::{CONFIG.get('IMPORT_STUDY_TO', 'Study')}::{os.path.basename(note1[2])}"
      decks.append(note["deckName"])
      #print(note['deckName'])
      note['fields'][CONFIG.get("STUDY_FRONT_FIELD")] = note1[0]
      note['fields'][CONFIG.get("STUDY_BACK_FIELD")] = note1[1]
      notes[i] = note

    decks = list(set(decks))
    for deck in decks:
      anki_connect.invoke("createDeck", deck=deck)
    
    ids = anki_connect.invoke("addNotes", notes=notes)

    sync_dates = []
    notes_dates = [ms_to_str(x) for x in notes_dates]
    sync_dates.extend(notes_dates)
    
    device.close()

    with open("history.txt", "a") as f:
      if ids:
        f.write(f"\n[{sync_dates[0]}][STUDY]: {len(ids)} study questions imported.")
  return sync_dates

# exports all words and notes for specific language
def export_lang(device, lang):
  check_reqs(["WORD_FRONT_FIELD", "WORD_BACK_FIELD", "WORD_MODEL_NAME", "NOTE_FRONT_FIELD", "NOTE_BACK_FIELD", "NOTE_MODEL_NAME"])
  
  sync_dates = []

  device.connect()
  FROM_LANG=lang
  
  IMPORT_WORDS_FROM = CONFIG["FROM_LANGS"][lang]
  if not IMPORT_WORDS_FROM:
    CONFIG["SKIP_REPEATS_CHECK"] = True
  to_lang = CONFIG["TO_LANG"]
  import_notes_to= f"{CONFIG['MAIN_DECK']}::{get_lang_name(lang)}_{get_lang_name(to_lang)}::{CONFIG['IMPORT_NOTES_TO']}"
  import_words_to= f"{CONFIG['MAIN_DECK']}::{get_lang_name(lang)}_{get_lang_name(to_lang)}::{CONFIG['IMPORT_WORDS_TO']}"
  anki_connect.invoke("createDeck", deck=import_notes_to)
  anki_connect.invoke("createDeck", deck=import_words_to)
  
  

  print(f"syncing all words...")
  words, words_dates = device.get_words(FROM_LANG)
  words, words_dates = get_new_items(words, words_dates)
  
  print(f"syncing all notes...")
  notes, notes_dates = device.get_notes(FROM_LANG)
  notes, notes_dates = get_new_items(notes, notes_dates)
  
  # list -> (note, translation)
  notes = [[x[0], TRANSLATOR.translate(x[0], from_=lang)] for x in notes if x[1] == None or x[1].strip() == '']

  
  from_to = f"{lang}{CONFIG['TO_LANG']}"
  notes = [(x,t) for x,t in notes if t!="No translation available"]
  TRANSLATOR.update_previous_translations(dict(notes),from_to)

  # print(notes)
  len_words = add_words(words, import_words_to, lang, IMPORT_WORDS_FROM)
  
  print(f"Got {len(notes)} notes...")  
  len_sentences = add_notes(notes, import_notes_to)
  
  device.close()
  is_skip_sync = (isinstance(device, csv_connect.Csv) 
               or isinstance(device, json_connect.Json)) 
  
  sync_dates = []
  words_dates = [ms_to_str(x) for x in words_dates]
  notes_dates = [ms_to_str(x) for x in notes_dates]
  
  if not is_skip_sync:
    sync_dates.extend(words_dates)
    sync_dates.extend(notes_dates)
  else: print("skipping sync dates...")
  
  
  with open("history.txt", "a") as f:
    if len_sentences:
      f.write(f"\n[{notes_dates[0]}][{lang}]: {len_sentences} sentences imported.")
    if len_words:
      f.write(f"\n[{words_dates[0]}][{lang}]: {len_words} words imported.")
  
  return sync_dates

# logic of adding words to anki decks
def add_words(words, to_, lang, from_=None):
  ids = []
  left_out_words = words
  amount_words = 0
  if len(words)>0:
    ids = []
    query_words = ''.join(f'"deck:{from_}" AND "{CONFIG["IMPORT_FIELD"]}:{word}" AND "is:suspended" AND -"deck:{to_}"' + ' OR ' for word in words)[:-4]
    
    if not CONFIG.get("SKIP_REPEATS_CHECK"):
      ids = anki_connect.invoke("findCards", query=query_words)
    
    repeats = []
    if len(ids) > 0:
      imported_words = anki_connect.invoke("cardsInfo", cards=ids)
      imported_words = [x['fields'][CONFIG["IMPORT_FIELD"]]['value'] for x in imported_words]
      amount_words+=len(imported_words)
      print(f"imported words from anki: {imported_words}")
      left_out_words = [item for item in words if item not in imported_words]
      anki_connect.invoke("changeDeck", cards=ids, deck=to_)
      anki_connect.invoke("unsuspend", cards=ids)
    else:
      print("Couldn't find any word to import from anki, gonna try to generate from dicts")
    if left_out_words:
      repeat_ids = []
      
      query_words = ''.join(f'"deck:{CONFIG["MAIN_DECK"]}" AND "{CONFIG["IMPORT_FIELD"]}:{word}" AND -"is:suspended" OR "deck:{CONFIG["MAIN_DECK"]}" AND "{CONFIG["WORD_FRONT_FIELD"]}:{word}" AND -"is:suspended"' + ' OR ' for word in left_out_words)[:-4]
      if not CONFIG.get("SKIP_REPEATS_CHECK"):
        repeat_ids = anki_connect.invoke("findCards", query=query_words)
      repeats = anki_connect.invoke("cardsInfo", cards=repeat_ids)
      #repeats = [x['fields'][IMPORT_FIELD]['value'] for x in repeats]
      
      reps = []
      for card in repeats:
        imp = card['fields'].get(CONFIG["IMPORT_FIELD"])
        gen = card['fields'].get(CONFIG["WORD_FRONT_FIELD"])
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
    generate_cards(left_out_words, lang, to_)
  amount_words+=len(left_out_words)
  len_words = amount_words
  
  print(f"Got {len_words} words...")
  return len_words

# logic of adding notes to anki decks
def add_notes(notes, to_):
  ids = []
  if len(notes)>0:
    fields = anki_connect.invoke("modelFieldNames", modelName=CONFIG["NOTE_MODEL_NAME"])
    ids = []
    note_blueprint = {"deckName": to_,
                    "modelName": CONFIG["NOTE_MODEL_NAME"],
                    'fields': {x:'' for x in fields},
                    "options": {
                        "allowDuplicate": False,
                        "duplicateScope": "deck",
                    },
                    }
    for i, note1 in enumerate(notes.copy()):
      note = copy.deepcopy(note_blueprint)
      note['fields'][CONFIG["NOTE_FRONT_FIELD"]] = note1[0]
      note['fields'][CONFIG["NOTE_BACK_FIELD"]] = note1[1]
      notes[i] = note
    
    ids = anki_connect.invoke("addNotes", notes=notes)
  if not ids:
    ids = []
  return len(ids)

# loads all dates that were synced
def get_sync_dates():
  sync_dates = []
  try:
    with open("sync_dates.json", "r", encoding="utf-8") as f:
      sync_dates = json.load(f)
  except:
    print("No file sync_dates.json....")
  
  return sync_dates

# returns only dates and items that are new and out of sync
def get_new_items(l, dates, to_str_delegate=ms_to_str):
  new_items = None
  if len(l) != len(dates):
    print("not enought dates for the values provided!")
  else:
    sync = get_sync_dates()
    item_dates = [(l[i], x) for i,x in enumerate(dates) if to_str_delegate(x) not in sync]
    new_items = [x[0] for x in item_dates]
    new_dates = [x[1] for x in item_dates]
    new_dates = sorted(new_dates)
  return new_items, new_dates

if __name__ == "__main__":
  
  try:
    #main()
    app()
    pass
  except Exception as e:
    if "No connection could be made" in str(e):
      e = "[ERROR]: AnkiConnect add-on is not installed or Anki is not running"
    print(traceback.format_exc())
    print(e)
  input("Press Enter to finish...")
