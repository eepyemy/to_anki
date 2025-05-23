import sqlite3
from datetime import datetime
import os, string
import shutil
import psutil
from utility_funcs import *
import json

#shutil.copyfile(src, dst)

class Kobo:

  def __get_path(self):
    partitions = psutil.disk_partitions(all=True)
    paths = []
    for part in partitions:
      mountpoint = part[1]
      path = os.path.join(mountpoint, ".kobo")
      path = os.path.join(path, "KoboReader.sqlite")
      if os.path.exists(path):
        paths.append(path)

    if len(paths)==1:
      print("kobo connected, updating local DB...")
      return paths[0]
    elif len(paths)==0:
      print("kobo is not connected, will try to use old version of DB...")
    else:
      print(".kobo is in more then one drive, make sure that you don't have .kobo anywhere else in the root of drive except in Kobo itself.")
      return None
  
  def __backup_db(self, dst):
    path = self.__get_path()
    if path:
      shutil.copyfile(path, dst)
    else:
      print("[KoboReader.sqlite] failed to backup data...")

  def __has_needed_data(self, scope="all"):
    result = False
    db_path = os.path.join(f"{os.getcwd()}/settings", "KoboReader.sqlite")
    if scope == "all":
      result = os.path.exists(db_path)
    return result

  # dummy func implementation of Type interface
  def get_dict_order(self):
    return {}    
  
  def __init__(self, config=None):
    if config is not None:
      self.CONFIG=config
    else:
      with open("settings/PROPERTIES.env", "r", encoding="utf-8") as f:
        self.CONFIG = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in x and x.strip("\n")[-1]!="="}
    self.__is_connected = False
    self.__backup_db(os.path.join(f"{os.getcwd()}/settings","KoboReader.sqlite"))

  def close(self):
    if self.__is_connected:
      self.__con.close()
      self.__is_connected = False
  
  def connect(self):
    if self.__has_needed_data():
      self.__is_connected = True
      self.__con = sqlite3.connect('settings/KoboReader.sqlite')
      self.cur = self.__con.cursor()
    else:
      print("can't connect to KoboReader.sqlite, no such file in working direcrtory")

  # safe query vocab db
  def __query(self, command):
    if self.__is_connected:
      return self.cur.execute(command)
    else:
      return []

  def get_words(self, lang):
    def lang_check_func(data, lang=lang):
      if lang is None:
        return True
      
      # normilize data and lang
      lang = lang.replace("_", "-").strip("-").upper()
      if lang not in self.CONFIG["SUPPORTED_LANGS"]:
        lang = lang.split("-")[0]
      if isinstance(data, str):
        data = data.replace("_", "-").strip("-").upper()
        if data not in self.CONFIG["SUPPORTED_LANGS"]:
          data = data.split("-")[0]
        if (("-" in data and "-" not in lang)
            or ("-" in lang and "-" not in data)):
          return data.split("-")[0] == lang.split("-")[0]
      return data == lang

    if not self.__is_connected:
      print("There is no DB for words, returning empty array")
      return [], []

    all_words = self.__query("SELECT * FROM WordList ORDER BY DateCreated")
    all_words = list(all_words)

    words = [(word,"") for word,_,lang_,_ in all_words if lang_check_func(lang_)]
    dates = [date_to_ms(str_to_date(date)) for _,_,lang_,date in all_words if lang_check_func(lang_)]
    
    if len(words)==0:
      return [], []

    return words, dates
  
  def get_notes(self, lang):
    def lang_check_func(data, lang=lang):
      if lang is None:
        return True
      
      # normilize data and lang
      lang = lang.replace("_", "-").strip("-").upper()
      if lang not in self.CONFIG["SUPPORTED_LANGS"]:
        lang = lang.split("-")[0]
      if isinstance(data, str):
        data = data.replace("_", "-").strip("-").upper()
        if data not in self.CONFIG["SUPPORTED_LANGS"]:
          data = data.split("-")[0]
      return data == lang

    if not self.__is_connected:
      print("There is no DB for notes, returning empty array")
      return [], []
    
    all_notes = list(self.__query("SELECT Text, Annotation, VolumeID, DateModified FROM Bookmark ORDER BY DateCreated"))
    #print(all_notes)

    

    content_dict = {}
    content_dict = {id:d for id,d in self.__query("SELECT ContentID, SelectedDictionary FROM content_settings")}
    #print(content_dict)
    notes = []
    dates = []
    for text, annotation, content_id, date in all_notes:
      book_lang = content_dict.get(content_id)
      if not book_lang:
        continue
      if lang_check_func(lang,book_lang):
        if text:
          notes.append([text, annotation, ""])
          dates.append(date_to_ms(str_to_date(date)))
    
    if len(notes)==0:
      return [], []

    return notes, dates


if __name__ == "__main__":
  k = Kobo()
  k.connect()
  d = datetime(2023,6,22,1,1,1)
  _, dates = k.get_notes("EN")
  dates.extend(k.get_notes("NL")[1])
  dates.extend(k.get_notes("STUDY")[1])
  dates.extend(k.get_words("NL")[1])
  dates.extend(k.get_words("EN")[1])
  
  print(dates)
  dates = [ms_to_str(x) for x in dates if ms_to_date(x) < d]
  #print(k.get_notes("STUDY"))
  with open("dates.json", "w") as f:
    json.dump(dates, f)
  #print(k.get_notes("RU"))
  #print(k.get_notes("Study"))
  #print(k.get_words("RU"))
  #print(k.get_words("ES"))
  k.close()
  