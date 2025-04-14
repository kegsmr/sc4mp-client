import os
import re
import json

from core.util import *

LANGUAGES = ["es", "fr", "it", "ru"]

LOCALE_FILENAME = "locale.json"
LOCALE_TARGET = "sc4mpclient.py"

FUNCTION_PATTERN = re.compile(r'loc\(["\'](.*?)["\']\)')

locale_path = os.path.join("resources", LOCALE_FILENAME)

if os.path.exists(locale_path):
	messages = json.load(open(locale_path, "r", encoding="utf-8"))
else:
	messages = {}

with open(LOCALE_TARGET, 'r', encoding='utf-8') as file:
	content = file.read()
	matches = FUNCTION_PATTERN.findall(content)
	for match in matches:
		messages.setdefault(match, {})

for translations in messages.values():
	for language in LANGUAGES:
		translations.setdefault(language, "")

json.dump(messages, open(locale_path, "w", encoding="utf"), indent=4)