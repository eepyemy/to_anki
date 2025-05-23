import os
from glob import glob
from pystardict import Dictionary
from rich import print
import os
from shutil import unpack_archive
from pyglossary.glossary_v2 import ConvertArgs, Glossary
from shutil import rmtree
import traceback

# #TODO make it unzip all zip files in dicts folder
def unzip_dicts():
	formats = [ "zip", "tar", "tar.gz", "tar.bz", "tar.xz"]
	zips = [] 
	
	[zips.extend(glob(f"dicts/*.{x}") + glob(f"dicts/**/*.{x}") + glob(f"dicts/**/**/*.{x}") + glob(f"dicts/**/**/**/*.{x}")) for x in formats]
	zips = [x for x in zips if os.path.isfile(x)]
	if zips:
		print("Unzipping dictionaries...")
		print(zips)
	for ind, item in enumerate(zips): # loop through items in dir
		filename = os.path.abspath(item)
		zipdir = os.path.splitext(filename)[0]
		if not os.path.exists(zipdir):
			os.mkdir(zipdir)
		
		unpack_archive(filename=item, extract_dir=zipdir) # extract file to dir
		os.remove(filename) # delete zipped file
		print(f"{ind+1}/{len(zips)} done", end="\r")
	print("")
	if zips:
		print("Unzipped!")

# #TODO make built in dicts conversion
# from pyglossary import Glossary
def convert_dicts():
	files = glob("dicts/**/*.*") + glob("dicts/**/**/*.*") + glob("dicts/**/**/**/*.*")
	files = [x for x in files if not os.path.isdir(x)]
	candidates = {}
	for item in files:
		filename = os.path.abspath(item)
		parent = os.path.dirname(filename)
		if any([child.endswith(".ifo") for child in os.listdir(parent)]):
			continue
		if parent not in candidates:
			candidates[parent] = []
		candidates[parent].append(filename)
	if candidates:
		print("Converting dictionaries...")
		print(candidates.keys())

	for ind, pair in enumerate(candidates.items()):
		parent, filenames = pair
		parent_base = os.path.basename(parent)
		for file in filenames:
			try:
				if not os.path.exists(file):
					break
				base = os.path.basename(file)
				glos = Glossary()
				output = ""
				input = ""
				to_delete = ""
				if len(parent_base)<=3:
					output = f"{os.path.splitext(file)[0]}"
					if not os.path.exists(output):
						os.mkdir(f'{output}-sd')
					input = file
					to_delete = file
				else:
					output = f"{parent}"
					if not os.path.exists(output):
						os.mkdir(f'{output}-sd')
					input = file	
					to_delete = parent
				if glos.convert(ConvertArgs(
					inputFilename=f"{input}",
					outputFilename=f"{output}-sd",
					outputFormat="Stardict",
					# you can pass readOptions or writeOptions as a dicts
					# writeOptions={"encoding": "utf-8"},
				)):
					if os.path.isdir(to_delete):
						rmtree(to_delete)
					else:
						os.remove(to_delete)
					break
				else:
					if os.path.isdir(f"{output}-sd"):
						rmtree(f"{output}-sd")
					else:
						os.remove(f"{output}-sd")
					continue
			except Exception as e:
				#traceback.print_exc()
				print("ERROR: ,",e)
				if os.path.isdir(f"{output}-sd"):
					rmtree(f"{output}-sd")
				else:
					os.remove(f"{output}-sd")
				continue
		print(f"{ind+1}/{len(candidates)} done", end="\r")
	print("")
	if candidates:
		print("Converted!")
	
try:	
	Glossary.init()
	unzip_dicts()
	convert_dicts()
except Exception as e:
	print("There was a problem with either converting or unzipping\n", e)

if not os.path.exists("settings"):
	os.makedirs("settings")

CONFIG={}
if not os.path.exists("settings/PROPERTIES.env"):
	print("PROPERTIES.env is not there, creating default one...")
	with open("settings/PROPERTIES.env", "w", encoding="utf-8") as f:
		f.write("//[optional] api key for DeepL translator, Google used by default\nDEEP_L_AUTH_KEY=\nUSE_DEEPL=False\n\n//choose between koreader and kobo\TYPE=koreader\n\n//[optional]cloud directory on your pc\nCLOUD_DIR=\n\n//name of the anki deck where all imported data will be stored\nMAIN_DECK=Language Learning\n\n//[optional] specify the full name of anki deck, you want this program to import cards from. you can add more lines following the same naming pattern for other languages you are learning. \nEN_IMPORT_FROM=\nNL_IMPORT_FROM=\n\n[optional] name of the field where the word is being stored in your {lang}_IMPORT_FROM deck.\nIMPORT_FIELD=Word\n\n//name of the deck for imported words from koreader\nIMPORT_WORDS_TO=Words\n\n//name of the deck for imported notes from koreader\nIMPORT_NOTES_TO=Notes\n\n//name of the deck for imported study questions from koreader\nIMPORT_STUDY_TO=Study\n\n//language to which you want things to be translated. change to your native language\nTO_LANG=EN\n\n//Marker folders in koreader, that will signal that a book in that folder has a purpose of learning particular language or just study folder. List all such folders for every lang you are willing to import using ,(comma)\n\nEN=\nNL=\nSTUDY=Study\n\n//Names of the anki cards models for words and for notes, change if using non default anki model\n\nNOTE_MODEL_NAME=Anki Learn sentences\nWORD_MODEL_NAME=Anki Learn words\nSTUDY_MODEL_NAME=Anki Learn sentences\n\n//Names of the anki cards front and back fields for words, notes and study cards, change if using non default anki model\n\nNOTE_FRONT_FIELD=Question\nNOTE_BACK_FIELD=Answer\n\nWORD_FRONT_FIELD=Word\nWORD_BACK_FIELD=Definitions\n\nSTUDY_FRONT_FIELD=Question\nSTUDY_BACK_FIELD=Answer\n\n")

with open("settings/PROPERTIES.env", "r", encoding="utf-8") as f:
	CONFIG = {x.split("=")[0]:x.split("=")[1].strip("\n") for x in f.readlines() if '=' in 
	x and x.strip("\n")[-1]!="="}

print(CONFIG)


def get_param(param_name, default=None):
	return CONFIG.get(param_name, default)

 
from_langs = [x.replace("_", "-").strip("-").split("-")[0].upper() for x in get_param("FROM_LANGS","").split(",")]
#print(from_langs)
CONFIG["FROM_LANGS"] = {x:get_param(f"{x}_IMPORT_FROM", "") 
												for x in from_langs}


CONFIG["MAIN_DECK"] = get_param("MAIN_DECK", "Language Learning")
CONFIG["IMPORT_WORDS_TO"] = get_param("IMPORT_WORDS_TO", "Words")
CONFIG["IMPORT_NOTES_TO"] = get_param("IMPORT_NOTES_TO", "Notes")
CONFIG["IMPORT_FIELD"] = get_param("IMPORT_FIELD", "Front")

CONFIG["NOTE_MODEL_NAME"] = get_param("NOTE_MODEL_NAME", "Anki Learn sentences")
CONFIG["WORD_MODEL_NAME"] = get_param("WORD_MODEL_NAME", "Anki Learn words")
CONFIG["STUDY_MODEL_NAME"] = get_param("STUDY_MODEL_NAME", "Anki Learn sentences")

CONFIG["WORD_FRONT_FIELD"] = get_param("WORD_FRONT_FIELD", "Word")
CONFIG["WORD_BACK_FIELD"] = get_param("WORD_BACK_FIELD", "Definitions")
CONFIG["NOTE_FRONT_FIELD"] = get_param("NOTE_FRONT_FIELD", "Question")
CONFIG["NOTE_BACK_FIELD"] = get_param("NOTE_BACK_FIELD", "Answer")
CONFIG["STUDY_FRONT_FIELD"] = get_param("STUDY_FRONT_FIELD", "Question")
CONFIG["STUDY_BACK_FIELD"] = get_param("STUDY_BACK_FIELD", "Answer")


CONFIG["TO_LANG"] = get_param("TO_LANG")
CONFIG["USE_GOOGLE"]=get_param("USE_GOOGLE", 'False')
CONFIG["USE_DICTS"]=get_param("USE_DICTS", 'True')
CONFIG["TRY_DOWNLOAD"]=get_param("TRY_DOWNLOAD", 'False')
CONFIG["CUSTOM_LANGS"]=get_param("CUSTOM_LANGS","")

if CONFIG["CUSTOM_LANGS"]:
	CONFIG["CUSTOM_LANGS"] = {x.split(":")[0]:x.split(":")[1] for x in CONFIG["CUSTOM_LANGS"].split(",")}
else:
	CONFIG["CUSTOM_LANGS"] = {}
#print(CONFIG["CUSTOM_LANGS"])

CONFIG["INCLUDE_LEARNED"] = get_param("INCLUDE_LEARNED", 'False')
def get_dicts():
	dicts = []
	dicts = glob("dicts/**/*.ifo") + glob("dicts/**/**/*.ifo") + glob("dicts/**/**/**/*.ifo")
	return dicts

CONFIG["DICT_PATHS"] = get_dicts()
if not CONFIG["DICT_PATHS"] and (CONFIG["USE_DICTS"]=='True'):
	print(os.getcwd())
	print("Didnt find any dicts in working directory, trying to download...")
	CONFIG["TRY_DOWNLOAD"]='True'

def check_reqs(list_params, raise_error=True):
	result = True
	for a in list_params:
		if not CONFIG.get(a):
			if raise_error:
				raise ValueError(f"Couldn't find {a} in PROPERTIES.env")
			else:
				print(f"Couldn't find {a} in PROPERTIES.env")
			result = False
	return result

def load_dicts_ordered(type):
	if not os.path.exists("settings/custom_dicts_order.txt"):
		with open("settings/custom_dicts_order.txt", "w", encoding="utf-8") as f:
			f.writelines([f"{os.path.basename(x)}\n" 
										for x in CONFIG["DICT_PATHS"]])

	custom_dicts_order = {}
	with open("settings/custom_dicts_order.txt", "r", encoding="utf-8") as f:
		custom_dicts_order = {x:i+1 for i,x 
													in enumerate(f.read().split())}
	
	custom_dicts_order = {f"{x}.ifo" if x.split(".")[-1]!="ifo" 
												else x : y 
												for x,y in custom_dicts_order.items()}
	custom_dicts_order = {x:y for x,y 
												in custom_dicts_order.items() if y!=0}

	with open("settings/custom_dicts_order.txt", "w", encoding="utf-8") as f:
		a = {os.path.basename(x):0 for x in get_dicts()}
		a.update(custom_dicts_order)
		a = sorted(a.items(), key=lambda x: x[1])
		a = [f"{x[0]}\n" for x in a]
		f.writelines(a)

	#print(custom_dicts_order)
	#print(dicts)
	dicts = {x:Dictionary(x[:-4]) 
										 for x in CONFIG["DICT_PATHS"]}
	dicts_order = type.get_dict_order()
	dicts_order = {os.path.basename(x):y 
								 for x,y in dicts_order.items()}
	dicts_order.update(custom_dicts_order)

	#print(dicts)
	if dicts_order or dicts:
		temp_len = max(list(dicts_order.values())+[len(dicts)])
	else:
		temp_len = 0
	sorted_dicts = [1]*temp_len
	result = {"others":[]}
	for dpath,d in dicts.items():
		dname = os.path.basename(dpath)

		place = dicts_order.get(dname)
		if not place:
			sorted_dicts.append((dpath, d,))
			continue
		sorted_dicts[place-1] = (dpath, d)
	sorted_dicts = [x for x in sorted_dicts 
									if not isinstance(x, int)]
	LANGS_GROUPS = [x.split("\\")[1].upper() for x,y in sorted_dicts 
												if len(x.split("\\")[1].upper())==2 
												or len(x.split("\\")[1].upper())==3 
												or ((len(x.split("\\")[1].upper().split("-"))==2) and len(x.split("\\")[1])<=8)]
	LANGS_GROUPS = list(set(LANGS_GROUPS))
	#print(LANGS_GROUPS)
	for dpath, d in sorted_dicts:
		lang_folder = dpath.split("\\")[1].upper()
		if lang_folder in LANGS_GROUPS:
			if lang_folder not in result:
				result[lang_folder] = [d]
			else:
				result[lang_folder].append(d)
		else:
			result["others"].append(d)

	return result