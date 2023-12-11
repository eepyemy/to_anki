import googletrans
from googletrans import Translator
import deepl
import json

DEEPL_LANGS = {
    "BG":"Bulgarian",
    "CS":"Czech",
    "DA":"Danish",
    "DE":"German",
    "EL":"Greek",
    "EN":"English",
    "EN-GB":"English(US)",
    "EN-US":"English(GB)",
    "ES":"Spanish",
    "ET":"Estonian",
    "FI":"Finnish",
    "FR":"French",
    "HU":"Hungarian",
    "ID":"Indonesian",
    "IT":"Italian",
    "JA":"Japanese",
    "KO":"Korean",
    "LT":"Lithuanian",
    "LV":"Latvian",
    "NB":"Norwegian",
    "NL":"Dutch",
    "PL":"Polish",
    "PT":"Portuguese",
    "PT-BR":"Portuguese(BR)",
    "PT-PT":"Portuguese(PT)",
    "RO":"Romanian",
    "RU":"Russian",
    "SK":"Slovak",
    "SL":"Slovenian",
    "SV":"Swedish",
    "TR":"Turkish",
    "UK":"Ukrainian",
    "ZH":"Chinese(simplified)"
}

class TranslatorsHandler:
  prev_translations={}
  to_="EN"
  from_="EN"
  translators = {
    "deepl":{
      "to_invoke":"_translate_deepl",
      "use":True,
      "methods":{
        "constructor":[deepl.Translator, {"auth_key":None}],
        "close": ["close", {}]
        }, 
      "supported_langs":DEEPL_LANGS
      },
    "google":{
      "to_invoke":"_translate_google",
      "use":True,
      "methods":{
        "constructor":[Translator, {}],
        }, 
      "supported_langs":googletrans.LANGUAGES
      },
    "generic":{
      "to_invoke":"_translate_generic",
      "use":False,
      "methods":{
        "constructor":[dict, {}],
        }, 
      "supported_langs":googletrans.LANGUAGES
    }
    }
  
  
  def __init__(self, config=None):
    # load previous translations
    self.update_previous_translations()
    self.__load_config(config)
    self.to_ = self.config.get("TO_LANG",self.to_)
    self.__initialize_translators()
  def close(self):
    try:
      for translator in self.translators.values():
        methods = translator.get("methods",{})
        close_method_name, kwargs = methods.get("close",[None, None])
        if close_method_name: 
          instance = translator.get("instance")
          if instance:
            close = getattr(instance, close_method_name)
            close(**kwargs)
    except Exception as e:
      print("There was a problem closing translator...", e)        
    
  def __initialize_translators(self):
    
    for name, config in self.translators.items():
      
      config["use"] = self.config.get(f"USE_{name.upper()}",config.get("use", False))
      to_invoke_name = config.get("to_invoke")
      if to_invoke_name:
        config["to_invoke"] = getattr(self, to_invoke_name, lambda *args, **kwargs: print(f"{name} needs a translation function implemented and linked"))
      methods = config.get("methods",{})
      for method_name, value in methods.items():
        method, kwargs = value
        #print(method, kwargs)
        if ("auth_key" in kwargs and 
          not kwargs.get("auth_key")):
          config["methods"][method_name][1]["auth_key"] = (
            self.config.get(f"{name.upper()}_AUTH_KEY"))
      #print(config)
      methods = config.get("methods",{})
      constructor, kwargs = methods.get("constructor",[None, None])
      if constructor:  
        config["instance"] = (
          constructor(**kwargs))

      self.translators[name] = config
  

  def __load_config(self, config=None):
    if config is not None:
      self.config=config
    else:
      with open("PROPERTIES.env", "r", encoding="utf-8") as f:
        self.config = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in x and x.strip("\n")[-1]!="="}
  def update_previous_translations(self, pairs={},from_to="UNKNOWN"):
    try:
      with open("translations.json", "r", encoding="utf-8") as f:
        self.prev_translations = json.load(f) 
    except Exception as e:
      print("No file for prev translations, creating one...", e)
    if from_to not in self.prev_translations:
      self.prev_translations[from_to] = {}
    self.prev_translations[from_to].update(dict(pairs))
    with open("translations.json", "w", encoding="utf-8") as f:
      json.dump(self.prev_translations, f)

  def translate(self, text, from_=None, to_=None, **kwargs):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    for name, translator in self.translators.items():
      self.translators[name]["use"] = kwargs.get(f"use_{name}",translator.get("use",False))
    
    # skipping translating if already translated it before
    from_to = f"{from_}{to_}"
    if from_to in self.prev_translations:
      if text in self.prev_translations[from_to]:
        return self.prev_translations[from_to][text]

    result = "No translation available"
    results = []
    for translator in self.translators.values():
      result = None
      if translator.get("use"):
        result = translator.get("to_invoke")(text, from_, to_)
      results.append(result)
      if any(results):
        break

    results = [x for x in results if x]
    if results:
      result = results[0]
    
    return result
  
  def __check_langs_supported(self, name, from_, to_):
    supported_langs = self.translators.get(name,{}).get("supported_langs", {})
    result = (from_ in supported_langs
              and to_ in supported_langs)
      # print(f"[{name}]: language not supported")
    return result
  def _translate_google(self,text,from_=None,to_=None):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    to_ = to_.lower()
    from_ = from_.lower()
    
    result = None
    name = "google"
    translator = self.translators[name]["instance"]
    if not self.__check_langs_supported(
      name, from_, to_):
      return result
    
    try:
      result = "[Google]:"+translator.translate(
        text, src=from_, dest=to_).text
      return result
    except Exception as e:
      print(f"There was a problem with {name}, ", e)
  def _translate_deepl(self,text,from_=None,to_=None):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    to_ = to_.upper()
    from_ = from_.upper()
    to_ = "EN-US" if to_ == "EN" else to_
    to_ = "PT-BR" if to_ == "PT" else to_
    
    result = None
    name = "deepl"
    translator = self.translators[name]["instance"]
    if not self.__check_langs_supported(
      name, from_, to_):
      return result
    
    try: 
      usage = translator.get_usage()
      if not text:
        return result
      
      if usage.character.count + len(text) > usage.character.limit:
        print("Out of limit.")
        return result

      return "[DeepL]:"+translator.translate_text(
        text, target_lang=to_, 
        source_lang=from_,
        formality="prefer_less").text
    except Exception as e:
      print("There was a problem with DeepL, ",e)
  def _translate_generic(self,text,from_=None,to_=None):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    to_ = to_.lower()
    from_ = from_.lower()
    
    result = None
    name = "generic"
    translator = self.translators[name]["instance"]
    if not self.__check_langs_supported(
      name, from_, to_):
      return result   
    try: 
      return "Generic translation"
    except Exception as e:
      print("There was a problem with DeepL, ",e)

if __name__ == "__main__":
  a = TranslatorsHandler()
  print(a.translate("я даже не знаю что сказать АФИГЕТЬ!", to_="EN", from_="RU"))