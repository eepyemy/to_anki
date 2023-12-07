from datetime import datetime, timedelta
import os
import json
from functools import reduce
import csv

def str_to_date(str):
  return datetime.strptime(str, '%Y-%m-%dT%H:%M:%SZ')

def ms_to_date(ms):
  return datetime.fromtimestamp(int(ms))

def date_to_ms(date):
  return date.timestamp()

def date_to_str(date, ms_timestamp=True):
  return date.strftime("%Y-%m-%dT%H:%M:%SZ")

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
    self.__notes_latest_date = ""
    self.__words_latest_date = ""
    self.__study_latest_date = ""
    
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
      print(f"[{CSV_FILENAME}] error, couldn't find json file")
      failed = True

    return not failed
      

  # closes db connection 
  def close(self):
    if self.__is_connected:
      self.__is_connected = False

  def get_latest_date(self):
    return {"notes":self.__notes_latest_date, "words":self.__words_latest_date, "study":self.__study_latest_date}

  # safe query vocab db
  def __query(self, lang, type):
    if self.__is_connected:
      if type=="words":
        if isinstance(self.__data, list):
          return [x[int(self.PROPERTIES.get("CSV_FIELD",0))] for x in self.__data if len(x[0].strip().split())==1]
      elif type=="notes":
        if isinstance(self.__data, list):
          return [x[int(self.PROPERTIES.get("CSV_FIELD",0))] for x in self.__data if len(x[0].strip().split())>1]
      return []
    else:
      return []
  # query db for all saved words, omit those that are not in target lang
  def get_words(self, from_date, lang=None) -> list:
    #print("lang selection is not working for now, come later for this")

    if not self.__is_connected:
      print("There is no DB for words, returning empty array")
      return []
    
    # get words in discdending order
    all_words = self.__query(lang,"words")
    all_words = list(all_words)


    # get words that are older than form_date
    words = [x.lower() for x in all_words]
    dates = [datetime.now().timestamp() for x in all_words]
    
    if len(words)==0:
      return []
    
    # save it in conventional time stamp format
    latest_date_str = max(dates, key=lambda x:ms_to_date(x))
    latest_date_str = ms_to_date(latest_date_str)
    latest_date_str = date_to_str(latest_date_str)

    # update latest_date_str if new date is older or previous date didnt exist
    if self.__words_latest_date == "":
      self.__words_latest_date = latest_date_str

    if str_to_date(latest_date_str) > str_to_date(self.__words_latest_date):
      self.__words_latest_date = latest_date_str

    return words
  
  # query db for all saved notes, omit those that are not in target lang
  def get_notes(self, from_date, lang=None, study=False) -> list:
    if lang is not None:
      lang = lang.upper().split("-")[0].split('_')[0]
      if lang not in self.PROPERTIES:
        print("there is no folder in self.properties set to detect lang")

    
    #print("lang selection is not working for now, come later for this")

    # check if have data
    if not self.__is_connected:
      return []
    
    # json -> Text, Annotation, Time created (if lang | and time is greater than latest update)
    all_notes = self.__query(lang, "notes")
    # Sort by time
    # all_notes = sorted(all_notes, key=lambda x: int(x[2]))
    

    dates = [datetime.now().timestamp() for x in all_notes]
    all_notes = [(x, "") for x in all_notes]
    
    if len(all_notes)==0:
      return []

    latest_date_str = max(dates)
    latest_date_str = ms_to_date(latest_date_str)
    latest_date_str = date_to_str(latest_date_str)

    if not study:
    
      if self.__notes_latest_date == "":
        self.__notes_latest_date = latest_date_str

      if str_to_date(latest_date_str) > str_to_date(self.__notes_latest_date):
        self.__notes_latest_date = latest_date_str
    
    if study:
      if self.__study_latest_date == "":
        self.__study_latest_date = latest_date_str

      if str_to_date(latest_date_str) > str_to_date(self.__study_latest_date):
        self.__study_latest_date = latest_date_str

    return all_notes
  
# just for debug
if __name__ == "__main__":
  k = Json()
  date_10 = datetime.now() - timedelta(days=10)
  date_200 = datetime.now() - timedelta(days=200)
  print(k.get_words(date_200, "nl"))
  print(k.get_notes(date_200, "Nl"))
  print(k.get_words(date_200, "EN"))
  print(k.get_notes(date_200, "en"))
  
  
  