from time import sleep
import json
import os
import copy
import traceback

import anki_connect
import kobo_connect
import koreader_connect
import json_connect, csv_connect
import ebooks_connect

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
BATCH=0
TOTAL=0

@app.command()
def main(
  type: str = CONFIG.get("DEVICE", None), 
  filename: str = None, 
  from_langs: str = "".join(f"{x} " for x in list(CONFIG["FROM_LANGS"].keys()))[:-1], 
  to_lang:str = CONFIG['TO_LANG'], 
  notes_deck_name:str = CONFIG['IMPORT_NOTES_TO'], 
  words_deck_name:str = CONFIG['IMPORT_WORDS_TO'], 
  sleep_sec:int = None,
  batch_size:str = CONFIG.get("BATCH_SIZE", "1000"),
  coverage:str = CONFIG.get("COVERAGE", "95"), 
  use_google: bool = CONFIG.get("USE_GOOGLE", 'True') == 'True', 
  skip_import : bool = CONFIG.get("SKIP_REPEATS_CHECK", 'True') == 'True', 
  download_dicts : bool = CONFIG.get("TRY_DOWNLOAD", 'False') == 'True', 
  use_deepl:bool = CONFIG.get("USE_DEEPL", 'True') == 'True',
  use_dicts:bool = CONFIG.get("USE_DICTS", 'True') == 'True',
  setup:bool = False,
  include_learned:bool = CONFIG.get("INCLUDE_LEARNED", 'False') == 'True',
  translate_words:bool = CONFIG.get("TRANSLATE_WORDS",'False') == 'True',
  verbose:bool = CONFIG.get("VERBOSE", "False") == 'True'
  ):
  
  # intializing config variables
  global CONFIG, TRANSLATOR, DICTS
  #print(CONFIG["FROM_LANGS"])
  
  CONFIG["COVERAGE"] = coverage
  CONFIG["VERBOSE"] = verbose
  CONFIG["TRANSLATE_WORDS"] = translate_words
  CONFIG["INCLUDE_LEARNED"] = include_learned
  CONFIG["BATCH_SIZE"] = batch_size
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

  
  folder_langs = [x.replace("_", "-").strip("-").split("-")[0].upper() for x in CONFIG["FROM_LANGS"]]

  [os.makedirs(f"dicts/{x}") for x in folder_langs if not os.path.isdir(f"dicts/{x}")]
  [os.makedirs(f"ebooks/{x}") for x in folder_langs if not os.path.isdir(f"ebooks/{x}")]

  
  CONFIG["FROM_LANGS"] = {x.upper():get_param(f"{x.upper()}_IMPORT_FROM", "") for x in folder_langs}
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
  elif type == "csv/list":
    device = csv_connect.Csv(config=CONFIG)
  elif type == "ebooks":
    device = ebooks_connect.Ebooks(config=CONFIG)
  
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
  
  # generating cards for every FROM language
  for lang in CONFIG["FROM_LANGS"]:
    print()
    print(f"Exporting from {get_lang_name(lang)} language...")
    print()
    export_lang(device, lang)
  
  sync_dates = get_sync_dates()
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
  input("Press Enter to finish...")

def get_learned_words(lang):
  global CONFIG

  # "deck:Language Learning::Dutch" AND "-is:new"

  deck_name= f"{CONFIG['MAIN_DECK']}::{get_lang_name(lang)}"
  
  query_words = ''.join(f'"deck:{deck_name}" AND -is:new AND -is:suspended')
  ids = anki_connect.invoke("findCards", query=query_words)
  learned_words = []
  if ids:
    cards = anki_connect.invoke("cardsInfo", cards=ids)
    learned_words = [x["fields"][list(x["fields"].keys())[0]]['value'] for x in cards]
  return learned_words

def get_lang_name(code):
  codes = {x.upper():y for x,y in CONFIG["SUPPORTED_LANGS"].items()}
  result = codes.get(code.upper(), code) 
  others = {"EN":"English", "PT":"Portuguese", "ZH":"Chinese"}
  if result in others:
    result = others[result]
  return result

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
      "DEVICE","Select default device for export of notes",choices=["koreader", "kobo", "ebooks", "csv/list", "json"]
    ),
    inquirer.Text("FILENAME","Enter filename to export words and sentences from",ignore=lambda x:x["DEVICE"] not in ["csv/list", "json"], default=""),
    inquirer.List("USUAL_CASE","Do you use languages that are not supported by common translators?",[("Yes",True),("No", False)],False),
    inquirer.Text("CUSTOM_LANGS","(optional) Enter custom language codes and their names via colon, separating each new pair with a comma",ignore=lambda x: not x["USUAL_CASE"], default="")]
  
  skip_translators_default = ["deepl", "generic"]
  translator_choices = [(f"{x.title()}", 
                (f"USE_{x.upper()}", True))
               for x in CONFIG["TRANSLATOR"].translators]
  translator_defaults = ([(f"USE_{x.upper()}", True)
               for x in CONFIG["TRANSLATOR"].translators if x.lower() not in skip_translators_default])
  translators_setup = [
    inquirer.Checkbox("TRANS_USE", 
      f"Select translators you want to use", 
      choices=translator_choices, 
      default=translator_defaults,
      ignore=lambda x: list_input("Want to setup translators?",choices=[("Yes", False), ("No", True)], default=True))
  ]
  

  '''
  (print(f"USE_{name.upper()}",not dict(x["TRANS_USE"]).get(f"USE_{name.upper()}", False)), not dict(x["TRANS_USE"]).get(f"USE_{name.upper()}", False))
  '''
  
  anki_custom_setup=[
    inquirer.Text("MAIN_DECK", "Main deck name (default:Language Learning)","Language Learning"),
    inquirer.Text("IMPORT_WORDS_TO", "Words deck name(default:Words_Reading)","Words"),
    inquirer.Text("WORD_MODEL_NAME", "Anki model name for words cards(default:Anki Learn words)","Anki Learn words"),
    inquirer.Text("WORD_FRONT_FIELD", "Front field name for words cards(default:Word)","Word"),
    inquirer.Text("WORD_BACK_FIELD", "Back field name for words cards(default:Definitions)","Definitions"),
    
    
    inquirer.Text("IMPORT_NOTES_TO", "Sentences deck name(default:Notes_Reading)","Notes"),
    inquirer.Text("NOTE_MODEL_NAME", "Anki model name for sentences cards(default:Anki Learn sentences)","Anki Learn sentences"),
    inquirer.Text("NOTE_FRONT_FIELD", "Front field name for sentences cards(default:Question)","Question"),
    inquirer.Text("NOTE_BACK_FIELD", "Back field name for sentences cards(default:Answer)","Answer"),
    
    
    inquirer.Text("IMPORT_STUDY_TO", "Study questions deck name(default:Study)", "Study"),
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
  #x.replace("_", "-").strip("-").split("-")[0]
  koreader_specific = [inquirer.Text(x.replace("_", "-").strip("-").split("-")[0].upper()
  ,f"Enter comma separated folder names form KOreader for books in {codes[x]} language",ignore=lambda _: answers["DEVICE"]!="koreader", default="") for x in answers["FROM_LANGS"]]

  koreader_specific.append(inquirer.Text("STUDY", f"Enter comma separated folder names form KOreader for books that you study: ",ignore=lambda _: answers["DEVICE"]!="koreader", default=""))
  
  include_learned = [inquirer.List("INCLUDE_LEARNED", message=f"Do you want to include already learned words in the deck?", choices=[("Yes", True), ("No", False)], ignore=lambda _: answers["DEVICE"]not in ["ebooks", "csv/list", "json"])]

  coverage = [inquirer.Text("COVERAGE", message=f"Please enter the percentage of text you aim to be able to understand: ", ignore=lambda _: answers["DEVICE"]not in ["ebooks"], default="95")]

  answers = update(answers, prompt(koreader_specific))
  answers = update(answers, prompt(include_learned))
  answers = update(answers, prompt(coverage))
  
  #print(answers)
  tr = prompt(translators_setup)
  print(tr)
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
  #print(CONFIG)
  do_save = list_input("Do you want to save the settings?",choices=[ ("No", False),("Yes", True)], default=True if save=="False" else False)
  if do_save:
    to_save = CONFIG.copy()
    if not to_save.get("CUSTOM_LANGS",{}):
      to_save.pop("CUSTOM_LANGS",None)
    to_save.pop("TRY_DOWNLOAD",None)
    to_save.pop("WAS_SETUP",None)
    to_save.pop("DICT_PATHS",None)
    to_save.pop("SUPPORTED_LANGS",None)
    to_save.pop("TRANSLATOR",None)
    to_save.pop("FROM_LANGS", None)
    to_save["TO_LANG"] = to_save["TO_LANG"].upper()
    to_save["FROM_LANGS"] = "".join(f'{x.upper()},' for x in CONFIG["FROM_LANGS"])[:-1]
    
    
    print("Saving newly made config...")
    with open("PROPERTIES.env", "w", encoding="utf-8") as f:
      for k,v in to_save.items():
        f.write(f"\n{k}={v}")
      f.write("\nWAS_SETUP=True")
    to_save["WAS_SETUP"] = True  
    print("Saved the following data to PROPERTIES.env :")
    print(to_save)
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
  ebooks_base = "".join(f"{x}::" for x in note_blueprint["deckName"].split("::")[:-2]) + "ebooks::"
  ebook_decks = set([x[1] for x in words if x[1]])
  for d in ebook_decks:
    anki_connect.invoke("createDeck", deck=ebooks_base + d)
  print("")
  for ind, pair in enumerate(words):
    word, ebook_name = pair
    print(f"Generating cards: {BATCH+ind+1}/{TOTAL}...", end="\r", flush=True)
    note = copy.deepcopy(note_blueprint)
    if ebook_name:
      note["deckName"] = ebooks_base + ebook_name
    note['fields'][CONFIG["WORD_FRONT_FIELD"]] = word
    if CONFIG["USE_DICTS"]:
      definitions = []
       
      subdicts = DICTS.get(lang.upper(), DICTS["others"])
      for dictionary in subdicts:
        result = dictionary.get(word)
        if result:
          definitions.append((result,str(dictionary)))
      if definitions:
        note['fields'][CONFIG["WORD_BACK_FIELD"]] = ''.join(f'<div class="definition"><p>{x[1]}</p>{x[0]}</div>' for x in definitions)
      elif CONFIG["TRANSLATE_WORDS"]: # add flag later
        t = (word, TRANSLATOR.translate(word, from_=lang))
        translations.append(t)
        note['fields'][CONFIG["WORD_BACK_FIELD"]] = f'<div class="definition">{t[1]}</div>'
      else:
        continue
    else:
      t = (word, TRANSLATOR.translate(word, from_=lang))
      translations.append(t)
      note['fields'][CONFIG["WORD_BACK_FIELD"]] = f'<div class="definition">{t[1]}</div>'
    notes.append(note)
  print("")
  from_to = f"{lang}{CONFIG['TO_LANG']}"
  translations = [(x,t) for x,t in translations 
                  if t!="No translation available"]
  TRANSLATOR.update_previous_translations(
    dict(translations),from_to)
  print("Adding cards to Anki...")
  ids = anki_connect.invoke("addNotes", notes=notes)
  print("Cards added!")

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
  global BATCH, TOTAL
  TOTAL = 0
  BATCH = 0
  check_reqs(["WORD_FRONT_FIELD", "WORD_BACK_FIELD", "WORD_MODEL_NAME", "NOTE_FRONT_FIELD", "NOTE_BACK_FIELD", "NOTE_MODEL_NAME"])
  
  sync_dates = []

  device.connect()
  FROM_LANG=lang
  
  IMPORT_WORDS_FROM = CONFIG["FROM_LANGS"][lang]
  if not IMPORT_WORDS_FROM:
    CONFIG["SKIP_REPEATS_CHECK"] = True

  import_notes_to= f"{CONFIG['MAIN_DECK']}::{get_lang_name(lang)}::Reading::{CONFIG['IMPORT_NOTES_TO']}"
  import_words_to= f"{CONFIG['MAIN_DECK']}::{get_lang_name(lang)}::Reading::{CONFIG['IMPORT_WORDS_TO']}"
  anki_connect.invoke("createDeck", deck=import_notes_to)
  anki_connect.invoke("createDeck", deck=import_words_to)
  
  

  print(f"syncing all words...")
  words, words_dates = device.get_words(FROM_LANG)
  words, words_dates = get_new_items(words, words_dates)
  
  if not CONFIG["INCLUDE_LEARNED"]:
    print("Retrieving learned words...")
    learned_words = get_learned_words(lang)
    ziped = [x for x in zip(words, words_dates) if x[0][0] not in learned_words]
    if CONFIG["VERBOSE"]:
      print(f"Learned words are: {learned_words}")
    print(f"Skipping already learned words: {len(words) - len(ziped)}...")
    words = [x[0] for x in ziped]
    words_dates = [x[1] for x in ziped]
  
  print(f"syncing all notes...")
  notes, notes_dates = device.get_notes(FROM_LANG)
  notes, notes_dates = get_new_items(notes, notes_dates)
  device.close()
  
  is_skip_sync = (isinstance(device, csv_connect.Csv) 
               or isinstance(device, json_connect.Json)) 
  from_to = f"{lang}{CONFIG['TO_LANG']}"

  sync_dates = get_sync_dates()

  TOTAL = len(words)
  words_batch = []
  result_words = []
  words_dates_batch = []
  len_words = 0
  for ind, pair in enumerate(zip(words,words_dates)):
    word, word_date = pair
    words_batch.append(word)
    words_dates_batch.append(word_date)
    if ((ind+1) % int(CONFIG["BATCH_SIZE"]))==0 or ind+1==len(words):
      
      #do something
      
      len_words += add_words(words_batch, import_words_to, lang, IMPORT_WORDS_FROM)
      BATCH += int(CONFIG["BATCH_SIZE"])
      words_dates_batch = [ms_to_str(x) for x in words_dates_batch]
      if not is_skip_sync:
        sync_dates.extend(words_dates_batch)
        sync_dates = list(set(sync_dates))
        with open("sync_dates.json", "w", encoding="utf-8") as k:
          json.dump(sync_dates, k)
      result_words.append(words_batch)
      words_batch = []
      words_dates_batch = []
    
  notes_batch = []
  result_notes = []
  len_sentences = 0
  notes_dates_batch = []
  for ind, pair in enumerate(zip(notes,notes_dates)):
    note, note_date = pair
    notes_batch.append(note)
    notes_dates_batch.append(note_date)
    if ind % int(CONFIG["BATCH_SIZE"]) or ind+1==len(notes):
      print(f"{ind+1}/{len(notes)} Processing notes...")  

      # translation
      # list -> (note, translation)
      notes_batch = [(x[0], TRANSLATOR.translate(x[0], from_=lang), x[2],) for x in notes_batch if x[1] == None or x[1].strip() == '']
      translations = [(x,t,) for x,t,_ in notes_batch if t!="No translation available"]
      TRANSLATOR.update_previous_translations(dict(translations),from_to)
      len_sentences += add_notes(notes_batch, import_notes_to)
      notes_dates_batch = [ms_to_str(x) for x in notes_dates_batch]
      if not is_skip_sync:
        sync_dates.extend(notes_dates_batch)
        sync_dates = list(set(sync_dates))
        with open("sync_dates.json", "w", encoding="utf-8") as k:
          json.dump(sync_dates, k)
      result_notes.append(notes_batch)
      notes_batch = []
  
  print(f"Got {len_words} words...")  
  print(f"Got {len_sentences} notes...")  
  
  if is_skip_sync:
    print("skipping sync dates...")
  
  
  with open("history.txt", "a") as f:
    if len_sentences:
      f.write(f"\n[{notes_dates[0]}][{lang}]: {len_sentences} sentences imported.")
    if len_words:
      f.write(f"\n[{words_dates[0]}][{lang}]: {len_words} words imported.")

# logic of adding words to anki decks
def add_words(words, to_, lang, from_=None):
  ids = []
  left_out_words = words
  amount_words = 0
  if CONFIG["VERBOSE"]:
    print(f"generating words: {[x[0] for x in left_out_words]}")
  
  len_words = len(words)
  if left_out_words:
    generate_cards(left_out_words, lang, to_)
  amount_words+=len(left_out_words)
  len_words = amount_words
  
  #print(f"Got {len_words} words...")
  return len_words

# logic of adding notes to anki decks
def add_notes(notes, to_):
  ids = []
  if len(notes)>0:
    fields = anki_connect.invoke("modelFieldNames", modelName=CONFIG["NOTE_MODEL_NAME"])
    ids = []

    if CONFIG["DEVICE"] in ["json", "ebooks", "csv/list"]:
      to_ = "".join(f"{x}::" for x in to_.split("::")[:-2]) + "ebooks::"
      print(to_)
    note_blueprint = {"deckName": to_,
                    "modelName": CONFIG["NOTE_MODEL_NAME"],
                    'fields': {x:'' for x in fields},
                    "options": {
                        "allowDuplicate": False,
                        "duplicateScope": "deck",
                    },
                    }
    decks = []
    for i, note1 in enumerate(notes.copy()):
      note = copy.deepcopy(note_blueprint)
      if CONFIG["DEVICE"] in ["json", "ebooks", "csv/list"]:
        note["deckName"] = to_+note1[2]
        decks.append(note["deckName"])
      note['fields'][CONFIG["NOTE_FRONT_FIELD"]] = note1[0]
      note['fields'][CONFIG["NOTE_BACK_FIELD"]] = note1[1]
      notes[i] = note
    [anki_connect.invoke("createDeck", deck=x) for x in decks]
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


