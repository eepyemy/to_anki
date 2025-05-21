from datetime import datetime

def str_to_date(str):
  return datetime.strptime(str, '%Y-%m-%dT%H:%M:%SZ')

def ms_to_date(ms):
  return datetime.fromtimestamp(int(ms))

def ms_to_str(ms):
  return date_to_str(ms_to_date(ms))

def date_to_ms(date):
  return date.timestamp()

def date_to_str(date, ms_timestamp=True):
  return date.strftime("%Y-%m-%dT%H:%M:%SZ")

def filetype(name, extention):
  return name.split(".")[-1]==extention