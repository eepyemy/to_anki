import sqlite3
import os
import shutil
import json
import glob
import psutil
from functools import reduce
import luadata
from utility_funcs import *


VOCAB_FILENAME = "vocabulary_builder.sqlite3"
BOOKS_INFO_FILENAME="bookinfo_cache.sqlite3"
NOTES_FILENAME = "notes.json"
NOTES_FILEPATTERN = "*all-books.json"
SETTINGS_FILENAME="settings.reader.lua"
#shutil.copyfile(src, dst)

class Koreader:

  # Looks for paths with db files
  # Check also dir from properties variable CLOUD_DIR if no kobo connected
  def __get_paths_to_data(self, device_type="kobo", cloud_dir=None) -> dict:
    result = {"vocab":None, "notes":None, "books_info":None, "dicts":None, "settings":None}
    paths = []
    path = None
    partitions = psutil.disk_partitions(all=True)
    need_break = False
    for part in partitions:
      if need_break == True:
        break
      mountpoint = part[1]
      
      if device_type == "kobo":
        path = os.path.join(mountpoint, ".adds")
      elif cloud_dir:
          print("going to cloud dir")
          path = cloud_dir
          need_break=True
      else:
        path = mountpoint
        try:
          directories_in_curdir = next(os.walk(mountpoint))[1]
          if directories_in_curdir:
            path = os.path.join(path, directories_in_curdir[0])
        except Exception as e:
          print("Permission denied", e)
      path = os.path.join(path, "koreader")
      print(f"checking {path}...")
      if os.path.exists(path):
        print("exists!")
        paths.append(path)
    
    if paths:
      path = paths[0]
    if path:
      settings = os.path.join(path, SETTINGS_FILENAME)
      dicts = os.path.join(path, "data")
      dicts = os.path.join(dicts, "dict")
      vocab = os.path.join(path, "settings")
      books_info = os.path.join(vocab, BOOKS_INFO_FILENAME)
      vocab = os.path.join(vocab, VOCAB_FILENAME)
      notes = os.path.join(path, "clipboard")
      print(notes)
      cwd = os.getcwd()
      notes_path = []
      if os.path.exists(notes):
        os.chdir(notes)
        notes_path = sorted(glob.glob(NOTES_FILEPATTERN), key=os.path.getmtime, reverse=True)
        os.chdir(cwd)
      
      if notes_path:
        notes_path = notes_path[0]
        notes_path = os.path.join(notes, notes_path)
      else:
        notes_path = None
      result["notes"] = notes_path

      if os.path.exists(settings):
        result["settings"] = settings

      if self.__download_dicts:
        if os.path.exists(dicts):
          result["dicts"] = dicts

      if os.path.exists(vocab):
        result["vocab"] = vocab

      if os.path.exists(books_info):
        result["books_info"] = books_info

    return result
  
  # copies db from path where it's located
  def __backup_data(self, dst, attempts=5):
    # priority and multiple path search, so it searches first for kobo path, and if there is none on phisical mounting points, let it search in the web
    paths_kobo = self.__get_paths_to_data(device_type="kobo")
    paths_cloud = self.__get_paths_to_data(device_type="cloud", cloud_dir=self.PROPERTIES.get("CLOUD_DIR")) 

    if paths_kobo["vocab"] or paths_kobo["notes"]:
      paths = paths_kobo
      print("kobo connected")
    else:
      print("kobo, not connected, looking for other sources")
      paths = paths_cloud
    for i in range(attempts):
      for datatype, path in list(paths.items())[::-1]:
        if path:
          print("found path...")
          to_file = os.path.join(dst, os.path.basename(path))
          print(f"coppying from {path}")
          if datatype == "notes":
            shutil.copyfile(path, NOTES_FILENAME)
            continue
          if datatype == "dicts":
            shutil.copytree(path, to_file)
            continue  
          shutil.copyfile(path, to_file)
          #time.sleep(10)
      connect = self.connect()
      self.close()
      if connect:
        break
         
  # checks if there is all data that is needed
  def __has_needed_data(self, scope="all"):
    result = False
    vocab_path = os.path.join(os.getcwd(), VOCAB_FILENAME)
    notes_path = os.path.join(os.getcwd(), NOTES_FILENAME)
    books_info_path = os.path.join(os.getcwd(), BOOKS_INFO_FILENAME)
    settings_path = os.path.join(os.getcwd(), SETTINGS_FILENAME)
    if scope == "all":
      result = os.path.exists(vocab_path) and os.path.exists(notes_path) and os.path.join(os.getcwd(), BOOKS_INFO_FILENAME)
    elif scope == "vocab":
      result = os.path.exists(vocab_path)
    elif scope == "notes":
      result = os.path.exists(notes_path)
    elif scope == "books_info":
      result = os.path.exists(books_info_path)
    elif scope == "settings":
      result = os.path.exists(settings_path)
    
    return result
  
  # backup db, opens db connection, resets latest date
  def __init__(self, download_dicts=False):
    self.PROPERTIES={}
    if os.path.exists("PROPERTIES.env"):
      with open("PROPERTIES.env", "r", encoding="utf-8") as f:
        self.PROPERTIES = {x.split("=")[0]:x.split("=")[1].strip() for x in f.readlines() if '=' in x and x.strip()[-1]!="="}
    self.__is_connected = False
    self.__notes_data = []
    self.__download_dicts = download_dicts
    self.__backup_data(os.getcwd())
    #self.connect()
    self.books = {}
    
    if self.__has_needed_data(scope="books_info"):
      books_info = sqlite3.connect(BOOKS_INFO_FILENAME)
      books = books_info.cursor().execute("SELECT directory, title FROM bookinfo")
      self.books = {x[1]:x[0] for x in books}
      books_info.close()

  #  opens db connection
  def connect(self):
    failed = False
    if self.__has_needed_data(scope="vocab"):
      self.__is_connected = True
      self.__con = sqlite3.connect(VOCAB_FILENAME)
      self.cur = self.__con.cursor()
    else:
      print("[vocabulary_builder.sqlite3] failed to backup data, cant connect")
    if self.__has_needed_data(scope="notes"):
      try:
        with open(NOTES_FILENAME, "r", encoding="utf-8") as f:
          self.__notes_data = json.load(f)

      except:
        print("[notes.json] download failed, trying again...")
        failed = True
    else:
      print("[notes.json] failed to backup data, cant connect")
      self.__notes_data = []
    
    self.titles = self.__query("SELECT id, name FROM title")
    if self.titles:
      self.titles = {x[0]:x[1] for x in self.titles}
    else: self.titles = {}
    return not failed
      
  # closes db connection 
  def close(self):
    if self.__is_connected:
      self.__con.close()
      self.__is_connected = False

  # safe query vocab db
  def __query(self, command):
    if self.__is_connected:
      return self.cur.execute(command)
    else:
      return []
  
  # get dict order from koreader
  def get_dict_order(self):
    if self.__has_needed_data(scope="settings"):
      data = luadata.read(os.path.join(os.getcwd(), SETTINGS_FILENAME))
      if data:
        order = data.get("dicts_order", {})
        if not order:
          order = {} 
        return order
    return {}
  
  # query db for all saved words, omit those that are not in target lang
  def get_words(self, lang=None) -> list:
    #print("lang selection is not working for now, come later for this")

    # check if word is from lang book
    def lang_check_func(title_id, lang):
      if lang is None:
        return True
      
      # normilize lang
      lang = lang.upper().split("-")[0].split('_')[0]
      if lang not in self.PROPERTIES:
        return False
      
      title = self.titles.get(title_id)
      filepath = self.books.get(title)


      if not filepath:
        return False

      dirs_in_path = os.path.normpath(filepath).split(os.path.sep)
      return any(word in dirs_in_path for word in self.PROPERTIES.get(lang).split(","))
    
    if not self.__is_connected:
      print("There is no DB for words, returning empty array")
      return [], []
    
    # get words in discdending order
    all_words = self.__query("SELECT word, create_time, title_id FROM vocabulary ORDER BY create_time")
    all_words = list(all_words)


    # get words that are older than form_date
    words = [x[0].lower() for x in all_words if lang_check_func(x[2], lang)]
    dates = [x[1] for x in all_words if lang_check_func(x[2], lang)]
    
    if len(words)==0:
      return [], []

    return words, dates
  
  # query db for all saved notes, omit those that are not in target lang
  def get_notes(self, lang=None) -> list:
    if lang is not None:
      lang = lang.upper().split("-")[0].split('_')[0]
      if lang not in self.PROPERTIES:
        print("there is no folder in self.properties set to detect lang")
    
    # checks if book inside folder with lang tag
    def lang_check_func(filepath, lang):
      if lang is None:
        return True
      
      # normilize lang
      lang = lang.upper().split("-")[0].split('_')[0]
      if lang not in self.PROPERTIES:
        return False
      
      dirs_in_path = os.path.normpath(filepath).split(os.path.sep)
      #print(dirs_in_path, filepath)
      return any(word in dirs_in_path for word in self.PROPERTIES.get(lang).split(","))
    
    #print("lang selection is not working for now, come later for this")

    # check if have data
    if not self.__notes_data:
      return [], []
    
    # json -> Text, Annotation, Time created (if lang)
    all_notes = []
    if 'documents' not in self.__notes_data:
      self.__notes_data = {'documents':[self.__notes_data]}
    for doc in self.__notes_data['documents']:
      filepath = doc.get("file")
      if not lang_check_func(filepath, lang):
        continue
      for entry in doc['entries']:
        
        text = entry['text']
        note = ""
        time_created = entry['time']
        if "note" in entry:
          note = entry["note"]

        all_notes.append((text, note, time_created, filepath))

    # Sort by time
    all_notes = sorted(all_notes, key=lambda x: int(x[2]))
    

    dates = [x[2] for x in all_notes]
    all_notes = [(x[0], x[1], x[3]) for x in all_notes]
    
    if len(all_notes)==0:
      return [], []

    return all_notes, dates
  
# just for debug
if __name__ == "__main__":
  k = Koreader()
  k.connect()
  print(k.get_notes("RU"))
  print(k.get_notes("ES"))
  print(k.get_notes("Study"))
  print(k.get_words("RU"))
  print(k.get_words("ES"))
  k.close()
  