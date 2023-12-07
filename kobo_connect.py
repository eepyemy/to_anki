import sqlite3
from datetime import datetime
import os, string
import shutil
import psutil

def str_to_date(str, m=False):
  if m:
    return datetime.strptime(str, "%Y-%m-%dT%H:%M:%S.%f")
  else:
    return datetime.strptime(str, '%Y-%m-%dT%H:%M:%SZ')
def date_to_str(date):
  return date.strftime("%Y-%m-%dT%H:%M:%SZ")


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
    db_path = os.path.join(os.getcwd(), "KoboReader.sqlite")
    if scope == "all":
      result = os.path.exists(db_path)
    return result

  # dummy func implementation of Device interface
  def get_dict_order(self):
    return {}    
  
  def __init__(self):
    self.__is_connected = False
    self.__backup_db(os.path.join(os.getcwd(),"KoboReader.sqlite"))
    self.__notes_latest_date = ""
    self.__words_latest_date = ""

  def close(self):
    if self.__is_connected:
      self.__con.close()
      self.__is_connected = False
  
  def connect(self):
    if self.__has_needed_data():
      self.__is_connected = True
      self.__con = sqlite3.connect('KoboReader.sqlite')
      self.cur = self.__con.cursor()
    else:
      print("can't connect to KoboReader.sqlite, no such file in working direcrtory")

  # safe query vocab db
  def __query(self, command):
    if self.__is_connected:
      return self.cur.execute(command)
    else:
      return []

  def get_latest_date(self):
    return {"notes":self.__notes_latest_date, "words":self.__words_latest_date}

  def get_words(self, from_date, lang):
    def lang_check_func(data, lang=None):
      if lang is None:
        return True
      
      # normilize lang
      data = data.upper().strip("-").split("-")[0].split('_')[0]
      lang = lang.upper().strip("-").split("-")[0].split('_')[0]

      if data==lang:
        return True
      else:
        return False

    all_words = self.__query("SELECT * FROM WordList ORDER BY DateCreated")
    all_words = list(all_words)


    words = [x[0] for x in all_words if lang_check_func(x[2],lang) and str_to_date(x[3])>from_date]
    dates = [x[3] for x in all_words if lang_check_func(x[2],lang) and str_to_date(x[3])>from_date]
    
    if len(words)==0:
      return []
    
    latest_date = max(dates, key=lambda x:str_to_date(x))
    if self.__words_latest_date == "":
      self.__words_latest_date = latest_date

    if str_to_date(latest_date) > str_to_date(self.__words_latest_date):
      self.__words_latest_date = latest_date

    return words
  
  def get_notes(self, from_date, lang):
    def lang_check_func(data, lang=None):
      if lang is None:
        return True
      
      # normilize lang
      data = data.upper().strip("-").split("-")[0].split('_')[0]
      lang = lang.upper().strip("-").split("-")[0].split('_')[0]
      
      if data==lang:
        return True
      else:
        return False

    all_notes = list(self.__query("SELECT Text, Annotation, VolumeID, DateModified FROM Bookmark ORDER BY DateCreated"))
    #print(all_notes)

    

    content_dict = {}
    content_dict = {x[0]: x[1] for x in self.__query("SELECT ContentID, SelectedDictionary FROM content_settings")}
    #print(content_dict)
    notes = []
    dates = []
    for text, annotation, content_id, date in all_notes:
      book_lang = content_dict.get(content_id)
      if not book_lang:
        continue
      if lang_check_func(lang,book_lang) and str_to_date(date)>from_date:
        if text:
          notes.append([text, annotation])
          dates.append(date)
    
    if len(notes)==0:
      return []

    latest_date = max(dates, key=lambda x:str_to_date(x))

    if self.__notes_latest_date == "":
      self.__notes_latest_date = latest_date

    if str_to_date(latest_date) > str_to_date(self.__notes_latest_date):
      self.__notes_latest_date = latest_date
  

    return notes