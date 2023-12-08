import os
from glob import glob
import json 

PROPERTIES={}
if not os.path.exists("PROPERTIES.env"):
  print("PROPERTIES.env is not there, creating default one...")
  with open("PROPERTIES.env", "w", encoding="utf-8") as f:
    f.write("//[optional] api key for DeepL translator, Google used by default\nDEEP_L_AUTH_KEY=\n\n//choose between koreader and kobo\nDEVICE=koreader\n\n//[optional]cloud directory on your pc\nCLOUD_DIR=\n\n//name of the anki deck where all imported data will be stored\nMAIN_DECK=Default\n\n//[optional] specify the full name of anki deck, you want this program to import cards from. you can add more lines following the same naming pattern for other languages you are learning. \nEN_IMPORT_FROM=\nNL_IMPORT_FROM=\n\n[optional] name of the field where the word is being stored in your {lang}_IMPORT_FROM deck.\nIMPORT_FIELD=Word\n\n//name of the deck for imported words from koreader\nIMPORT_WORDS_TO=Words_Reading\n\n//name of the deck for imported notes from koreader\nIMPORT_NOTES_TO=Notes_Reading\n\n//name of the deck for imported study questions from koreader\nIMPORT_STUDY_TO=Study\n\n//language to which you want things to be translated. change to your native language\nTO_LANGUAGE=EN\n\n//Marker folders in koreader, that will signal that a book in that folder has a purpose of learning particular language or just study folder. List all such folders for every lang you are willing to import using ,(comma)\n\nEN=Learn_EN,Other_Learn_EN\nNL=Learn_NL\nSTUDY=Study\n\n//Names of the anki cards models for words and for notes, change if using non default anki model\n\nNOTE_MODEL_NAME=Anki Learn sentences\nWORD_MODEL_NAME=Anki Learn words\nSTUDY_MODEL_NAME=Anki Learn sentences\n\n//Names of the anki cards front and back fields for words, notes and study cards, change if using non default anki model\n\nNOTE_FRONT_FIELD=Question\nNOTE_BACK_FIELD=Answer\n\nWORD_FRONT_FIELD=Word\nWORD_BACK_FIELD=Definitions\n\nSTUDY_FRONT_FIELD=Question\nSTUDY_BACK_FIELD=Answer\n\n")

with open("PROPERTIES.env", "r", encoding="utf-8") as f:
  PROPERTIES = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in 
  x and x.strip("\n")[-1]!="="}

print(PROPERTIES)


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


DICTS = get_dicts()
# print(dicts)
if not DICTS and USE_DICTS:
  print(os.getcwd())
  print("Didnt find any dicts in working directory, trying to download...")
  TRY_DOWNLOAD=True


TRANSLATOR = None
GOOGLE_TRANSLATOR = None


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

PREV_TRANSLATIONS = {}

def update_prev_translations(notes={}):
  global PREV_TRANSLATIONS
  try:
    with open("translations.json", "r", encoding="utf-8") as f:
      PREV_TRANSLATIONS = json.load(f) 
  except Exception as e:
    print("No file for prev translations, creating one...", e)
  PREV_TRANSLATIONS.update(dict(notes))
  with open("translations.json", "w", encoding="utf-8") as f:
    json.dump(PREV_TRANSLATIONS, f)

update_prev_translations()