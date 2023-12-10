from datetime import datetime, timedelta
import os
import json
from functools import reduce
from utility_funcs import *

JSON_FILENAME="bulk_export.json"
#shutil.copyfile(src, dst)

class Json:
 
  # checks if there is all data that is needed
  def __has_needed_data(self, scope="all"):
    result = False
    json_path = os.path.join(os.getcwd(), JSON_FILENAME)
    if scope == "all":
      result = os.path.exists(json_path)
    
    return result
  
  def get_dict_order(self):
    return {}
  
  # backup db, opens db connection, resets latest date
  def __init__(self, filename=JSON_FILENAME):
    self.PROPERTIES={}
    global JSON_FILENAME
    JSON_FILENAME = filename
    if os.path.exists("PROPERTIES.env"):
      with open("PROPERTIES.env", "r", encoding="utf-8") as f:
        self.PROPERTIES = {x.split("=")[0]:x.split("=")[1].strip() for x in f.readlines() if '=' in x and x.strip()[-1]!="="}
    self.__is_connected = False
    self.__notes_data = []
    #self.connect()
    self.books = {}
    
  #  opens db connection
  def connect(self):
    failed = False
    if self.__has_needed_data(scope="all"):
      
      try:
        with open(JSON_FILENAME, "r", encoding="utf-8") as f:
          self.__data = json.load(f)
        self.__is_connected = True
      except Exception as e:
        self.__data = {}
        print(f"Couldn't open {JSON_FILENAME}...",e)
  
    else:
      print(f"[{JSON_FILENAME}] error, couldn't find json file")
      failed = True

    return not failed
      

  # closes db connection 
  def close(self):
    if self.__is_connected:
      self.__is_connected = False

  # safe query vocab db
  def __query(self, lang, type):
    if self.__is_connected:
      items = self.__data.get(lang, [])
      if isinstance(items, list):
        if type=="words":
          return [x for x in items if len(x.strip().split())==1]
        elif type=="notes":
          return [x for x in items if len(x.strip().split())>1]
      return []
    else:
      return []
  
  # query db for all saved words, omit those that are not in target lang
  def get_words(self, lang=None) -> list:
    #print("lang selection is not working for now, come later for this")

    if not self.__is_connected:
      print("There is no DB for words, returning empty array")
      return [], []
    
    # get words in discdending order
    all_words = self.__query(lang,"words")
    all_words = list(all_words)


    # get words that are older than form_date
    words = [x.lower() for x in all_words]
    dates = [datetime.now().timestamp() for x in all_words]
    
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
    

    dates = [datetime.now().timestamp() for x in all_notes]
    all_notes = [(x, "") for x in all_notes]
    
    if len(all_notes)==0:
      return [],[]

    return all_notes, dates
  
# just for debug
if __name__ == "__main__":
  k = Json()
  k.connect()
  print(k.get_notes("RU"))
  print(k.get_notes("ES"))
  print(k.get_notes("Study"))
  print(k.get_words("RU"))
  print(k.get_words("ES"))
  k.close()

  
  