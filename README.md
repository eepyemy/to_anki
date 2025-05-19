# to_anki

An app that: 
* aids mass creation of anki cards from saved words and sentences for language learning or general purpose studying
* supports StarDict dictionaries and can create cards with multiple definitions
* supports Google and DeepL translation for sentences 
* can be used as an export tool in combination with KOreader (takes a bit of tidious setup with Android unfortunately)

### Prerequisites
* Anki up and running on your pc
* AnkiConnect addon installed
* Just in case backup your Anki collection before proceding
* (optional) install recommended anki card templates for better definitions rendering: [Download](https://github.com/eepyemy/Anki_Templates/releases)

## How to use
Download the latest version of the program [here](https://github.com/eepyemy/to_anki/releases)

Extract the zip file

For user friendly initial setup run `setup` file, follow instructions and choose at the end Yes if you want to save the settings. 

After the settings are saved and you no longer want to modify them every time, you can run `export` file, which will skip the initial setup and will use the previously saved settings.

[Optional] Can be used as CLI, use `export --help` for more info.

## What each device mode do

### koreader
the program will look if there is a koreader device connected to pc (works with kobo, but doesnt with Android)

Otherwise it will look into CLOUD_DIR path for koreader folder.

If it finds the folder, it will extract all of the saved words and sentences during the reading for the target languages you selected. The way it determines if the word or a sentence is in the target language is by checking if the book is stored in one of the folders representing that language that user can set during the setup.

Then it creates new cards in your anki collection with all new words and sentences. 

It will also sync all of the dictionaries that your koreader folder has and use them for creating the anki cards. It will also preserve the dictionary order that was used in your koreader.

### kobo (poorly supported)

Program checks if kobo is connected and if it is, program looks for sentences and words that were saved during reading and translates them into anki cards. 

### csv/txt

The program will read the csv or txt file for words and sentences. It will bulk create anki decks for languages selected. Default structure of the file is like this. 

```csv
hello,EN
goedendag,NL
|example of the sentence|,EN
```

If used only for one source language, can be just a txt file with words on each line, basically a wordlist:
```
hello
friend
she
is
awesome
```

### json
The program will read the json file for words and sentences. It will bulk create anki decks for languages selected. Default structure of the file is like this.

```json
{
    "EN":["hello", "friend", "This is a test sentence!"],
    "NL":["hallo", "vriend", "Dit is een testzin!"]
}
```