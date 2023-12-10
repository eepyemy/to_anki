import os
from glob import glob
from pystardict import Dictionary
from rich import print

CONFIG={}
if not os.path.exists("PROPERTIES.env"):
  print("PROPERTIES.env is not there, creating default one...")
  with open("PROPERTIES.env", "w", encoding="utf-8") as f:
    f.write("//[optional] api key for DeepL translator, Google used by default\nDEEP_L_AUTH_KEY=\n\n//choose between koreader and kobo\nDEVICE=koreader\n\n//[optional]cloud directory on your pc\nCLOUD_DIR=\n\n//name of the anki deck where all imported data will be stored\nMAIN_DECK=Default\n\n//[optional] specify the full name of anki deck, you want this program to import cards from. you can add more lines following the same naming pattern for other languages you are learning. \nEN_IMPORT_FROM=\nNL_IMPORT_FROM=\n\n[optional] name of the field where the word is being stored in your {lang}_IMPORT_FROM deck.\nIMPORT_FIELD=Word\n\n//name of the deck for imported words from koreader\nIMPORT_WORDS_TO=Words_Reading\n\n//name of the deck for imported notes from koreader\nIMPORT_NOTES_TO=Notes_Reading\n\n//name of the deck for imported study questions from koreader\nIMPORT_STUDY_TO=Study\n\n//language to which you want things to be translated. change to your native language\nTO_LANGUAGE=EN\n\n//Marker folders in koreader, that will signal that a book in that folder has a purpose of learning particular language or just study folder. List all such folders for every lang you are willing to import using ,(comma)\n\nEN=Learn_EN,Other_Learn_EN\nNL=Learn_NL\nSTUDY=Study\n\n//Names of the anki cards models for words and for notes, change if using non default anki model\n\nNOTE_MODEL_NAME=Anki Learn sentences\nWORD_MODEL_NAME=Anki Learn words\nSTUDY_MODEL_NAME=Anki Learn sentences\n\n//Names of the anki cards front and back fields for words, notes and study cards, change if using non default anki model\n\nNOTE_FRONT_FIELD=Question\nNOTE_BACK_FIELD=Answer\n\nWORD_FRONT_FIELD=Word\nWORD_BACK_FIELD=Definitions\n\nSTUDY_FRONT_FIELD=Question\nSTUDY_BACK_FIELD=Answer\n\n")

with open("PROPERTIES.env", "r", encoding="utf-8") as f:
  CONFIG = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in 
  x and x.strip("\n")[-1]!="="}

print(CONFIG)


def get_param(param_name, default=None):
  return CONFIG.get(param_name, default)

CONFIG["FROM_LANGS"] = [x for x in CONFIG if len(x)==2 or len(x)==3 or (len(x.split("-"))==2)]

CONFIG["FROM_LANGS"] = {x:get_param(f"{x}_IMPORT_FROM", "") for x in CONFIG["FROM_LANGS"]}

CONFIG["MAIN_DECK"] = get_param("MAIN_DECK", "Default")
CONFIG["IMPORT_WORDS_TO"] = get_param("IMPORT_WORDS_TO", "Words_Reading")
CONFIG["IMPORT_NOTES_TO"] = get_param("IMPORT_NOTES_TO", "Notes_Reading")
CONFIG["IMPORT_FIELD"] = get_param("IMPORT_FIELD", "Front")

CONFIG["NOTE_MODEL_NAME"] = get_param("NOTE_MODEL_NAME", "Basic")
CONFIG["WORD_MODEL_NAME"] = get_param("WORD_MODEL_NAME", "Basic")

CONFIG["WORD_FRONT_FIELD"] = get_param("WORD_FRONT_FIELD", "Front")
CONFIG["WORD_BACK_FIELD"] = get_param("WORD_BACK_FIELD", "Back")
CONFIG["NOTE_FRONT_FIELD"] = get_param("NOTE_FRONT_FIELD", "Front")
CONFIG["NOTE_BACK_FIELD"] = get_param("NOTE_BACK_FIELD", "Back")

CONFIG["TO_LANG"] = get_param("TO_LANGUAGE")
CONFIG["USE_GOOGLE"]=get_param("USE_GOOGLE", False)
CONFIG["USE_DICTS"]=get_param("USE_DICTS", True)
CONFIG["TRY_DOWNLOAD"]=False

def get_dicts():
  dicts = []
  dicts = glob("dict/**/*.ifo") + glob("dict/**/**/*.ifo")
  return dicts

CONFIG["DICT_PATHS"] = get_dicts()
if not CONFIG["DICT_PATHS"] and CONFIG["USE_DICTS"]:
  print(os.getcwd())
  print("Didnt find any dicts in working directory, trying to download...")
  CONFIG["TRY_DOWNLOAD"]=True

def check_reqs(list_params, raise_error=True):
  result = True
  for a in list_params:
    if not CONFIG.get(a):
      if raise_error:
        raise ValueError(f"Couldn't find {a} in PROPERTIES.env")
      else:
        print(f"Couldn't find {a} in PROPERTIES.env")
      result = False
  return result

def load_dicts_ordered(device):
  if not os.path.exists("custom_dicts_order.txt"):
    with open("custom_dicts_order.txt", "w", encoding="utf-8") as f:
      f.writelines([f"{os.path.basename(x)}\n" 
                    for x in CONFIG["DICT_PATHS"]])

  custom_dicts_order = {}
  with open("custom_dicts_order.txt", "r", encoding="utf-8") as f:
    custom_dicts_order = {x:i+1 for i,x 
                          in enumerate(f.read().split())}
  
  custom_dicts_order = {f"{x}.ifo" if x.split(".")[-1]!="ifo" 
                        else x : y 
                        for x,y in custom_dicts_order.items()}
  custom_dicts_order = {x:y for x,y 
                        in custom_dicts_order.items() if y!=0}

  with open("custom_dicts_order.txt", "w", encoding="utf-8") as f:
    a = {os.path.basename(x):0 for x in get_dicts()}
    a.update(custom_dicts_order)
    a = sorted(a.items(), key=lambda x: x[1])
    a = [f"{x[0]}\n" for x in a]
    f.writelines(a)

  #print(custom_dicts_order)
  #print(dicts)
  dicts = {os.path.basename(x):Dictionary(x[:-4]) 
                     for x in CONFIG["DICT_PATHS"]}
  dicts_order = device.get_dict_order()
  dicts_order = {os.path.basename(x):y 
                 for x,y in dicts_order.items()}
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
  sorted_dicts = [x for x in sorted_dicts 
                  if isinstance(x, Dictionary)]
  return sorted_dicts