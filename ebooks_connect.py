from datetime import datetime, timedelta
import os
from functools import reduce
from utility_funcs import *
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from simplemma import lemma_iterator, simple_tokenizer
from collections import Counter
from glob import glob

def get_lemmas(text, lang=None):
  lemmas = [x for x in lemma_iterator(text, lang)]
  return lemmas

EBOOKS_DIR="ebooks"
#shutil.copyfile(src, dst)

class Ebooks:
 
	# checks if there is all data that is needed
	def __has_needed_data(self, scope="all"):
		result = False
		ebooks_path = os.path.join(os.getcwd(), EBOOKS_DIR)
		if scope == "all":
			result = os.path.exists(ebooks_path)
		
		return result
	
	def get_dict_order(self):
		return {}
	
	# backup db, opens db connection, resets latest date
	def __init__(self, config=None):
		global EBOOKS_DIR
		if config is not None:
			self.CONFIG=config
		else:
			with open("settings/PROPERTIES.env", "r", encoding="utf-8") as f:
				self.CONFIG = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in x and x.strip("\n")[-1]!="="}
		EBOOKS_DIR = config.get("FILENAME",EBOOKS_DIR)
		self.__is_connected = False
		self.__notes_data = []
		#self.connect()
		self.books = {}
		
	def __load_ebook(self, filename):
		try:
			if filetype(filename, "epub"):
				book = epub.read_epub(filename)
				content = ""
				for doc in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
					soup = BeautifulSoup(doc.get_body_content(), "html.parser")
					content += " " + " ".join(soup.strings)
			else:
				with open(filename, "r", encoding="utf-8") as f:
					content = f.read()
			return content
		except Exception as e:
			print("Could not open the book", e)

	#  opens db connection
	def connect(self):
		failed = False
		if self.__has_needed_data(scope="all"):
			
			try:
				langs = glob(f"{EBOOKS_DIR}{os.sep}*")
				langs = [os.path.basename(x) for x in langs if os.path.isdir(x)]
				self.__data = {}
				self.__is_connected = True
			except Exception as e:
				self.__data = {}
				print(f"Couldn't open {EBOOKS_DIR}...",e)
	
		else:
			print(f"[{EBOOKS_DIR}] error, couldn't find ebooks file")
			failed = True

		return not failed
			

	# closes db connection 
	def close(self):
		if self.__is_connected:
			self.__is_connected = False

	# safe query vocab db
	def __query(self, lang, type):
		if self.__is_connected:
			if lang not in self.__data:
				print(f"\n[{os.path.basename(EBOOKS_DIR)}]Checking the books for {lang} language...")
				self.__data[lang] = []
				if os.path.isdir(EBOOKS_DIR):
					ebooks = glob(f"{EBOOKS_DIR}{os.sep}{lang}{os.sep}*.*")
				else:
					ebooks = [EBOOKS_DIR] # in case its one book
					first_lang = list(self.CONFIG["FROM_LANGS"].keys())[0].replace("_", "-").strip("-").upper()
					if lang.replace("_", "-").strip("-").upper() != first_lang:
						return []

					
				for ind, ebook in enumerate(ebooks):
					ebook_name = os.path.splitext(os.path.basename(ebook))[0]
					print(f"({ind+1}/{len(ebooks)}) Extracting words from {ebook_name}...")
					content = self.__load_ebook(ebook)
					words = content.split()
					try:
						lang_code = lang.lower().split("-")[0]
						words = [x for x in lemma_iterator(content, lang_code) if x.islower()]
					except Exception as e:
						print(f"{e}\n\nCouldn't lemmatize text, gonna use raw text..")
					
					counted = Counter(words)
					sorted_count = [(x[0], ebook_name) for x in sorted(counted.items(), key=lambda x: x[1], reverse=True)]

					coverage = self.CONFIG.get("COVERAGE",100)
					needed = []
					covered = 0
					for x in sorted_count:
						needed.append(x)
						covered = sum([counted[x[0]] for x in needed])
						#print(covered)
						covered = (covered/len(words))*100 
						if covered>=float(coverage):
							break
					self.__data[lang].extend(needed)
					print(f"{len(needed)} words extracted to achieve {covered:.0f} coverage!")
			items = self.__data[lang]
			if isinstance(items, list):
				if type=="words":
					return items
				elif type=="notes":
					return []
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
		words = [(x[0].lower(),x[1]) for x in all_words]
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
		
		# ebooks -> Text, Annotation, Time created (if lang | and time is greater than latest update)
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
	k = Ebooks({"FILENAME":"ebooks"})
	k.connect()
	print(k.get_words("RU"))
	a = k.get_words("NL")
	a = [f"\n{x[0]}" for x in a[0]]
	with open("extracted.txt", "w", encoding="utf-8") as f:
		f.writelines(a)
	k.close()
	