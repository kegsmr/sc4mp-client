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

json.dump(messages, open(locale_path, "w", encoding="utf"), indent=4, ensure_ascii=False)


# === Extra: Find all strings and f-strings that are NOT localized ===
# print("\n--- Strings and f-strings that are NOT localized ---")

# class StringFinder(ast.NodeVisitor):
#     def __init__(self):
#         self.loc_strings = set(matches)  # already localized
#         self.found_strings = []

#     def visit_Str(self, node):
#         # Handle regular string literals
#         val = node.s
#         if val and val not in self.loc_strings and len(val.strip()) > 1:
#             self.found_strings.append((val, node.lineno))
#         self.generic_visit(node)

#     def visit_JoinedStr(self, node):
#         # Handle f-strings
#         val = ''.join([part.s if isinstance(part, ast.Str) else '' for part in node.values])
#         if val and val not in self.loc_strings and len(val.strip()) > 1:
#             self.found_strings.append((val, node.lineno))
#         self.generic_visit(node)

#     def visit_Assign(self, node):
#         # Check assignments to look for strings and f-strings
#         if isinstance(node.value, ast.Str):  # Normal string literals
#             val = node.value.s
#             if val and val not in self.loc_strings and len(val.strip()) > 1:
#                 self.found_strings.append((val, node.lineno))
#         elif isinstance(node.value, ast.JoinedStr):  # f-strings
#             val = ''.join([part.s if isinstance(part, ast.Str) else '' for part in node.value.values])
#             if val and val not in self.loc_strings and len(val.strip()) > 1:
#                 self.found_strings.append((val, node.lineno))
#         self.generic_visit(node)

#     def visit_Call(self, node):
#         # Check function calls to find string and f-string arguments
#         if isinstance(node.func, ast.Attribute) or isinstance(node.func, ast.Name):
#             for kw in node.keywords:
#                 if isinstance(kw.value, ast.Str):  # Regular string literals
#                     val = kw.value.s
#                     if val and val not in self.loc_strings and len(val.strip()) > 1:
#                         self.found_strings.append((val, node.lineno))
#                 elif isinstance(kw.value, ast.JoinedStr):  # f-strings
#                     val = ''.join([part.s if isinstance(part, ast.Str) else '' for part in kw.value.values])
#                     if val and val not in self.loc_strings and len(val.strip()) > 1:
#                         self.found_strings.append((val, node.lineno))
#         self.generic_visit(node)

# finder = StringFinder()
# tree = ast.parse(content)
# finder.visit(tree)

# for string, lineno in sorted(finder.found_strings, key=lambda x: x[1]):
#     print(f"Line {lineno}: {string}")