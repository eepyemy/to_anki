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
  def __init__(self, config=None):
    global CSV_FILENAME
    if config is not None:
      self.CONFIG=config
    else:
      with open("PROPERTIES.env", "r", encoding="utf-8") as f:
        self.CONFIG = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in x and x.strip("\n")[-1]!="="}
    CSV_FILENAME = config.get("FILENAME",CSV_FILENAME)
    self.__is_connected = False
    self.__notes_data = []
    #self.connect()
    self.books = {}
    
  #  opens db connection
  def connect(self):
    failed = False
    if self.__has_needed_data(scope="all"):
      
      try:
        with open(CSV_FILENAME, "r", encoding="utf-8", newline='\n') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=self.CONFIG.get("CSV_DELIMITER",','), quotechar=self.CONFIG.get("CSV_QUOTECHAR",'|'))
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
    result = []
    mainf = int(self.CONFIG.get("CSV_FIELD",0))
    langf = int(self.CONFIG.get("CSV_LANG_FIELD",1))
    if self.__is_connected:
      if isinstance(self.__data, list):        
        separator = lambda x: False
        if type=="words":
          separator = lambda x: len(x[0].strip().split())==1  
        elif type=="notes":
          separator = lambda x: len(x[0].strip().split())>1
        
        result = [(x[mainf],(x[langf:langf+1] or [None])[0]) for x in self.__data if separator(x)]
        
        count_langs = len(self.CONFIG["FROM_LANGS"])
        
        result = [(word,lang_) for word,lang_ in result
                  if ((count_langs==1 and lang_ is None)
                      or lang_check_func(lang_))]
    return result
  
  # query db for all saved words, omit those that are not in target lang
  def get_words(self, lang=None) -> list:
    #print("lang selection is not working for now, come later for this")
    
    if not self.__is_connected:
      print("There is no DB for words, returning empty array")
      return [], []
    
    # get words in discdending order
    all_words = self.__query(lang,"words")
    # print(all_words)
    dates = [datetime.now().timestamp() for _,_ in all_words]
    all_words = list([word for word,_ in all_words])


    # get words that are older than form_date
    words = [(x.lower(),self.CONFIG["FILENAME"]) for x in all_words]
    
    if len(words)==0:
      return [], []

    return words, dates
  
  # query db for all saved notes, omit those that are not in target lang
  def get_notes(self, lang=None) -> list: 
    #print("lang selection is not working for now, come later for this")

    # check if have data
    if not self.__is_connected:
      return [], []
    
    # json -> Text, Annotation, Time created (if lang | and time is greater than latest update)
    all_notes = self.__query(lang, "notes")
    # Sort by time
    # all_notes = sorted(all_notes, key=lambda x: int(x[2]))
    
    # print(all_notes)
    dates = [datetime.now().timestamp() for _,_ in all_notes]
    all_notes = [(x, "", self.CONFIG["FILENAME"]) for x,_ in all_notes]
    
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
