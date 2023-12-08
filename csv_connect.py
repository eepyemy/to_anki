from datetime import datetime
import os
from functools import reduce
import csv
from utility_funcs import *


CSV_FILENAME="bulk_export.csv"
#shutil.copyfile(src, dst)

class Csv:

  # checks if there is all data that is needed
  def __has_needed_data(self, scope="all"):
    result = False
    json_path = os.path.join(os.getcwd(), CSV_FILENAME)
    if scope == "all":
      result = os.path.exists(json_path)
    
    return result
  
  def get_dict_order(self):
    return {}
  
  # backup db, opens db connection, resets latest date
  def __init__(self, download_dicts=False):
    self.PROPERTIES={}
    if os.path.exists("PROPERTIES.env"):
      with open("PROPERTIES.env", "r", encoding="utf-8") as f:
        self.PROPERTIES = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in x and x.strip("\n")[-1]!="="}
    self.__is_connected = False
    self.__notes_data = []
    self.__download_dicts = download_dicts
    #self.connect()
    self.books = {}
    
  #  opens db connection
  def connect(self):
    failed = False
    if self.__has_needed_data(scope="all"):
      
      try:
        with open(CSV_FILENAME, "r", encoding="utf-8", newline='\n') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=self.PROPERTIES.get("CSV_DELIMITER",','), quotechar='|')
            self.__data = [x for x in spamreader]
        self.__is_connected = True
      except Exception as e:
        self.__data = {}
        print(f"Couldn't open {CSV_FILENAME}...",e)
  
    else:
      print(f"[{CSV_FILENAME}] error, couldn't find csv file")
      failed = True

    return not failed

  # closes db connection 
  def close(self):
    if self.__is_connected:
      self.__is_connected = False

  # safe query vocab db
  def __query(self, lang, type):
    if self.__is_connected:
      main = int(self.PROPERTIES.get("CSV_FIELD",0))
      langf = int(self.PROPERTIES.get("CSV_FIELD",1))
      if isinstance(self.__data, list):
        if type=="words":
          # (x[langf:langf+1] or [lang])[0] = safe list.get(index) with default lang
          return [(x[main],(x[langf:langf+1] or [None])[0]) for x in self.__data if len(x[0].strip().split())==1]
        elif type=="notes":
          return [(x[main],(x[langf:langf+1] or [None])[0]) for x in self.__data if len(x[0].strip().split())>1]
      return []
    else:
      return []
  
  # query db for all saved words, omit those that are not in target lang
  def get_words(self, lang=None) -> list:
    #print("lang selection is not working for now, come later for this")
    if lang is not None:
      lang = lang.upper().split("-")[0].split('_')[0]
      if lang not in self.PROPERTIES:
        print("there is no folder in self.properties set to detect lang")

    def lang_check_func(lang_):
      if lang_ is None:
        return True
      
      # normilize lang_
      lang_ = lang_.upper().split("-")[0].split('_')[0]
      if lang_ not in self.PROPERTIES:
        return False
      
      return lang_ == lang
      
    
    if not self.__is_connected:
      print("There is no DB for words, returning empty array")
      return [], []
    
    # get words in discdending order
    all_words = self.__query(lang,"words")
    # print(all_words)
    all_words = list([word for word, lang_ in all_words if lang_check_func(lang_)])


    # get words that are older than form_date
    words = [x.lower() for x in all_words]
    dates = [datetime.now().timestamp() for x in all_words]
    
    if len(words)==0:
      return [], []

    return words, dates
  
  # query db for all saved notes, omit those that are not in target lang
  def get_notes(self, lang=None) -> list:
    if lang is not None:
      lang = lang.upper().split("-")[0].split('_')[0]
      if lang not in self.PROPERTIES:
        print("there is no folder in self.properties set to detect lang")

    def lang_check_func(lang_):
      if lang_ is None:
        return True
      
      # normilize lang_
      lang_ = lang_.upper().split("-")[0].split('_')[0]
      if lang_ not in self.PROPERTIES:
        return False
      
      return lang_ == lang
    
    #print("lang selection is not working for now, come later for this")

    # check if have data
    if not self.__is_connected:
      return [], []
    
    # json -> Text, Annotation, Time created (if lang | and time is greater than latest update)
    all_notes = self.__query(lang, "notes")
    # Sort by time
    # all_notes = sorted(all_notes, key=lambda x: int(x[2]))
    
    # print(all_notes)
    dates = [datetime.now().timestamp() for x in all_notes]
    all_notes = [(x, "") for x,lang_ in all_notes if lang_check_func(lang_)]
    
    if len(all_notes)==0:
      return [], []

    return all_notes, dates
  
# just for debug
if __name__ == "__main__":
  k = Csv()
  k.connect()
  print(k.get_notes("RU"))
  print(k.get_notes("ES"))
  print(k.get_notes("Study"))
  print(k.get_words("RU"))
  print(k.get_words("ES"))
  k.close()
