import sublime, sublime_plugin, re

def toSnakeCase(text):
   s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
   return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def stripWrappingUnderscores(text):
   return re.sub("^(_*)(.*?)(_*)$", r'\2', text)

def getIndexes(text, char):
   indexlist = []
   last = 0
   while last != -1:
      pos = text.find(char, last)
      if pos == -1:
         break
      else:
         indexlist.append(pos)
         last = pos + 1
   return indexlist

def toPascalCase(text):
   if "_" in text:
      callback = lambda pat: pat.group(1).lower() + pat.group(2).upper()
      text = re.sub("(\w)_(\w)", callback, text)
      if text[0].islower():
         text = text[0].upper() + text[1:]
      return text
   return text[0].upper() + text[1:]

def toCamelCase(text):
   text = toPascalCase(text)
   return text[0].lower() + text[1:]


class ConvertToSnakeCommand(sublime_plugin.TextCommand):
   def run(self, edit):
      region = self.view.word(self.view.sel()[0])
      text = stripWrappingUnderscores(self.view.substr(region))
      self.view.replace(edit, region, toSnakeCase(text))

class ConvertToCamel(sublime_plugin.TextCommand):
   def run(self, edit):
      region = self.view.word(self.view.sel()[0])
      text = stripWrappingUnderscores(self.view.substr(region))
      self.view.replace(edit, region, toCamelCase(text))

class ConvertToPascal(sublime_plugin.TextCommand):
   def run(self, edit):
      region = self.view.word(self.view.sel()[0])
      text = stripWrappingUnderscores(self.view.substr(region))
      self.view.replace(edit, region, toPascalCase(text))