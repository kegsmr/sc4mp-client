import ast
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


# === Extra: Find string literals used in Tkinter UI code and print line numbers ===
print("\n--- Strings in Tkinter UI that are NOT localized ---")

class StringFinder(ast.NodeVisitor):
	def __init__(self):
		self.loc_strings = set(matches)  # already localized
		self.found_strings = []

	def visit_Call(self, node):
		# Look for something like Label(..., text="...")
		if isinstance(node.func, ast.Attribute) or isinstance(node.func, ast.Name):
			for kw in node.keywords:
				if isinstance(kw.value, ast.Str):
					val = kw.value.s
					if val and val not in self.loc_strings and len(val.strip()) > 1:
						self.found_strings.append((val, node.lineno))
		self.generic_visit(node)

	# Optional: also find things like `label["text"] = "Hello"`
	def visit_Assign(self, node):
		if isinstance(node.value, ast.Str):
			val = node.value.s
			if val and val not in self.loc_strings and len(val.strip()) > 1:
				self.found_strings.append((val, node.lineno))
		self.generic_visit(node)

finder = StringFinder()
tree = ast.parse(content)
finder.visit(tree)

for string, lineno in sorted(finder.found_strings, key=lambda x: x[1]):
	print(f"Line {lineno}: {string}")