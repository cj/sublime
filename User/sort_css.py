import sublime, sublime_plugin
import re, os, time

# The Sorter now looks for various scopes.  Below is a whitelist of allowed scopes.
# 'list' are the scopes than can be a substring in a list of css rules
# at a basic level, it will look for any amount of whitespace or text that is in the 'ignores' scope
# followed by text from the first element of a 'rule'
#that repeats for each element of the rule, like <whitespace/comment>name</whitespace/comment>value
scopes = {
  'source.css': {
    'list': [
      'meta.property-list.css'
    ],
    'rules': [
      ['meta.property-name.css', 'meta.property-value.css']
    ],
    'ignore': [
      'comment.block.css'
    ]
  },

  'source.scss': {
    'list': [
      'meta.property-list.css',
      'meta.at-rule.mixin.scss'
    ],
    'rules': [
      ['meta.property-name.css', 'meta.property-value.css'],
      ['meta.set.variable'],
      ['variable.scss', 'meta.property-value.css'],
      ['meta.at-rule.include.css']
    ],
    'ignore': [
      'comment.block.scss'
    ]
  }
}

class CssSorter:
  def __init__(self, view, start=0, end=None):
    self.view = view
    if end == None:
      end = self.view.size()
    self.parseBlocks(start, end)

  # Returns true if any of the scopes in target are a substring of scope
  def matchesScope(self, scope, targetScopes):
    for targetScope in targetScopes:
      if scope.find(targetScope) >= 0:
        return True
    return False

  # Returns true if scope contains any of the scopes in rules or ignore
  def ignorable(self, scope):
    for rule in self.scopes['rules']:
      for ruleScope in rule:
        if scope.find(ruleScope) >= 0:
          return True

    return self.matchesScope(scope, self.scopes['ignore'])

  def parseBlocks(self, start, selectionEnd):
    start = 0
    while start < selectionEnd:
      # quick hack to jump to the start of a rule list
      region = self.view.find(u'{', start, sublime.LITERAL)
      if region == None:
        break

      start = region.a+1
      scope = self.view.scope_name(region.a)
      syntax = scope.strip().split(' ')[-1]
      if not syntax in scopes:
        continue
      self.scopes = scopes[syntax]

      # ensure we are at the start of a property list and not in a string
      if not self.matchesScope(scope, self.scopes['list']):
        continue

      # iterate to find the end of the contiuous property list section
      # The below css declaration returns a property list scope region that ends at the first colon of the first rule
      # So, in this case, we have to keep iterating as long as the regions/scopes contain property-list.css
      # .test4 {-moz-border-radius: 1px;border-top-width: 1px;border: none;border-bottom-width: 1px;}
      end = self.parseableRegion(start)
      self.parseBlock(start, end)
      start = end

  def parseableRegion(self, start):
    while True:
      c = self.view.substr(start)
      if c == ' ' or c == '\n':
        start += 1
        continue

      scope = self.view.scope_name(start)
      if self.ignorable(scope):
        # advance to the end of the region, like the end of a name property
        region = self.view.extract_scope(start)
        if region.b == start:
          return start
        start = region.b
      else:
        # semicolons after @include aren't included with the rule so we have to ignore that in a semi-generic way
        if scope.startswith(self.scopes['list'][0]):
          start += 1
        else:
          # we hit a non-rule like a nested selector
          return start

  def parseBlock(self, start, end):
    # grab the current content in this region
    region = sublime.Region(start, end)
    existingContent = self.view.substr(region)

    # don't sort if /*nosort*/ is in the css block
    if re.search(r'/\*\s*nosort\s*\*/', existingContent) != None:
      return

    rules, tailStart = self.parseRules(start, end)
    #print 'parseRulesReturned', rules, start, end, tailStart, tailEnd, parseEnd
    if rules == None or len(rules) == 0:
      return
    rules.sort(self.compareLines)
    tail = self.view.substr(sublime.Region(tailStart, end))

    output = map(lambda rule: rule['rule'], rules)
    output = (''.join(output))+tail

    # Only perform the edit if it needs to be sorted to avoid unnecessary jumping / undo states
    if output != existingContent:
      editObject = self.view.begin_edit()
      self.view.replace(editObject, region, output)
      self.view.end_edit(editObject)

  def prepareRule(self, start, ruleStart, ruleEnd):
    data = {'rule': self.view.substr(sublime.Region(start, ruleEnd))}
    data['sortRule'] = self.view.substr(sublime.Region(ruleStart, ruleEnd)).strip()
    data['sortPrefix'] = ''
    match = re.match(r'^(\-[a-zA-Z]+\-)(.*)', data['sortRule'])
    if match != None:
      data['sortRule'] = match.group(2)
      data['sortPrefix'] = match.group(1)
    data['sortName'] = data['sortRule'].split(':')[0].strip()
    return data


  def parseRules(self, start, end):
    rules = []
    while start < end:
      matchedRule = False
      # at each location, any one of the rules could match
      # each rule is a sequence of scopes that can only be separated by whitespace or something from the ignores block
      for rule in self.scopes['rules']:
        bounds, searchStart = [], start
        for scope in rule:
          ruleStart, ruleEnd = self.parseToScope(searchStart, end, scope)
          if ruleStart == None:
            break

          bounds.append([ruleStart, ruleEnd])
          if searchStart == ruleEnd:
            break
          searchStart = ruleEnd

        # if there isn't a start/end pair for each rule, then one of them didn't match
        if len(bounds) != len(rule):
          continue

        ruleStart, ruleEnd = bounds[0][0], bounds[-1][1]

        # The @include scopes do not include the trailing semi colon :(
        while self.view.substr(ruleEnd) == u';':
          ruleEnd += 1

        rules.append(self.prepareRule(start, ruleStart, ruleEnd))
        start, matchedRule = ruleEnd, True
        break

      if not matchedRule:
        break

    return rules, start

  # This is a custom sorting function for the css rules
  # If there are duplicate rule names, then they should remain in the same order, regardless of value
  # If a rule name is a prefix of the other rule name (like border/border-width), the shorter should always come first
  # Lastly -moz- and such should be ignored
  def compareLines(self, a, b):
    if a['sortName'] == b['sortName']:
      return cmp(a['sortPrefix'], b['sortPrefix'])

    if a['sortName'].startswith(b['sortName']):
      return 1
    elif b['sortName'].startswith(a['sortName']):
      return -1
    else:
      return cmp(a['sortRule'], b['sortRule'])

  # This function traverses until it finds the first instance of scope
  # It continues parsing until it finds the last instance of that scope
  # It stops if it exceeds blockEnd
  def parseToScope(self, start, blockEnd, targetScope):
    while start < blockEnd:
      c = self.view.substr(start)
      if c == ' ' or c == '\n':
        start += 1
        continue

      scope = self.view.scope_name(start).strip()
      #print 'parseTo1', scope, start, c
      if scope.find(targetScope) >= 0:
        break
      elif self.matchesScope(scope, self.scopes['ignore']):
        region = self.view.extract_scope(start)
        if region.b == start:
          break
        start = region.b
      else:
        return None, None

    # If the loop didn't break early, then we did not find the scope
    if start >= blockEnd:
      return None, None

    # Now find the end of the scope region
    end = start
    while end < blockEnd:
      # Find the end of the region that includes end
      region = self.view.extract_scope(end)
      if region.b == end:
        break

      # Make sure it is still part of the scope region
      scope = self.view.scope_name(end)
      #print 'parseTo2', end, region, scope, targetScope
      if scope.find(targetScope) < 0:
        break

      # Some scopes regions don't encompass the full extent of the scope, so we need to keep iterating
      # until we hit the end of this continuous section of scope
      end = region.b

    return start, end

class SortCss(sublime_plugin.TextCommand):
  def run(self, edit):
    selections = self.view.sel()
    if len(selections) == 0:
      CssSorter(self.view)
    elif len(selections) == 1 and selections[0].a == selections[0].b:
      CssSorter(self.view)
    else:
      for selection in selections:
        start, end = min(selection.a, selection.b), max(selection.a, selection.b)
        CssSorter(self.view, start, end)


class SortCssListener(sublime_plugin.EventListener):
  def on_pre_save(self, view):
    if view.settings().get('sort_css_on_save', True):
      CssSorter(view)

class TestSortCss(sublime_plugin.WindowCommand):
  def run(self):
    path = os.path.join(sublime.packages_path(), 'MyPlugins', 'test', 'sortCss')
    inPath = os.path.join(path, 'in')
    outPath = os.path.join(path, 'out')

    files = os.listdir(inPath)
    for filename in files:
      view = self.window.open_file(os.path.join(inPath, filename))
      view.run_command('sort_css')
      content = view.substr(sublime.Region(0, view.size()))


      with open(os.path.join(outPath, filename), 'rb') as f:
        targetContent = f.read()

      content = content.replace('\n', '').replace('\r', '')
      targetContent = targetContent.replace('\n', '').replace('\r', '')

      print u"%s matches: %s" % (filename, content == targetContent)