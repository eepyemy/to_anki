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
  use_google=True
  use_deepl=True
  to_="EN"
  from_="EN"
  translators = {
    "deepl":[
    [deepl.Translator,[]], # constructor, args
    DEEPL_LANGS],
    "google":[
    [Translator,[]], 
    googletrans.LANGUAGES]
  }
  
  def __init__(self, config=None):
    # load previous translations
    self.update_previous_translations()
    self.__load_config(config)
    self.to_ = self.config.get("TO_LANG",self.to_)
    self.use_deepl = self.config.get("USE_DEEPL",self.use_deepl)
    self.use_google = self.config.get("USE_GOOGLE",self.use_google)
    self.translators["deepl"][0][1].append(
      self.config.get("DEEP_L_AUTH_KEY", ""))
    self.__initialize_translators()
  def close(self):
    try:
      translator, _ = self.translators["deepl"] 
      if translator:
        translator.close()
    except Exception as e:
      print("something wrong with closing translator...", e)

  def __initialize_translators(self):
    for name, config in self.translators.items():
      constructor, langs = config
      constructor, args = constructor
      self.translators[name] = [
        constructor(*args),
        langs]
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

  def translate(self, text, from_=None, to_=None, use_google=None, use_deepl=None):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    use_google = use_google if use_google else self.use_google
    use_deepl = use_deepl if use_deepl else self.use_deepl
    
    # skipping translating if already translated it before
    from_to = f"{from_}{to_}"
    if from_to in self.prev_translations:
      if text in self.prev_translations[from_to]:
        return self.prev_translations[from_to][text]

    result = "No translation available"
    result_google = None
    result_deepl = None
    if self.use_deepl:
      # deepl logic
      to_ = to_.upper()
      from_ = from_.upper()
      to_ = "EN-US" if to_ == "EN" else to_
      to_ = "PT-BR" if to_ == "PT" else to_
      result_deepl = self.__translate_deepl(text, from_, to_)
    
    if self.use_google and not result_deepl:
      # google logic
      to_ = to_.lower()
      from_ = from_.lower()
      result_google = self.__translate_google(text, from_, to_)
    tempo = result_deepl if result_deepl else result_google
    result = tempo if tempo else result
     
    return result
  
  def __translate_google(self,text,from_=None,to_=None):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    
    result = None
    translator, supported_langs = self.translators["google"]
    if (from_ not in supported_langs
        or to_ not in supported_langs):
      # print("[Google]: language not supported")
      return result
    try:
      result = "[Google]:"+translator.translate(
        text, src=from_, dest=to_).text
      return result
    except Exception as e:
      print("There was a problem with Google Translate, ", e)
  def __translate_deepl(self,text,from_=None,to_=None):
    from_ = from_ if from_ else self.from_
    to_ = to_ if to_ else self.to_
    
    translator, supported_langs = self.translators["deepl"]
    result = None
    if (from_ not in supported_langs
        or to_ not in supported_langs):
      # print("[DeepL]: language not supported")
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
        source_lang=from_.upper(),
        formality="prefer_less").text
    except Exception as e:
      print("There was a problem with DeepL, ",e)


if __name__ == "__main__":
  a = TranslatorsHandler()
  print(a.translate("я даже не знаю что сказать", to_="EN", from_="RU"))
  a.close()