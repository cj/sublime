#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import bisect
import pprint
import difflib

# Sublime Libs
import sublime
import sublime_plugin

################################### CONSTANTS ##################################

INIT          =   'init'
STOREEMPTYS   =   'store_emptys'
MERGE         =   'merge'

KEY           =   'auto_select'
SCOPE         =   'string'

DEBUG         = 0
ALL_TESTS     = 1
TESTS         = DEBUG

################################### BINDINGS ###################################
"""
[{
    "keys": ["alt+a"],
    "command": "auto_select",
    "args": {"cmd": "init"},

    "context": [{
        "key": "setting.auto_select",
        "operand": false,
        "operator": "equal"
    }]
},
{
    "keys": ["alt+a"],
    "command": "auto_select",
    "args": {"cmd": "merge"},

    "context": [{
        "key": "setting.auto_select",
        "operand": true,
        "operator": "equal"
    }]
},
{
    "keys": ["alt+a"],
    "command": "auto_select",
    "args": {"cmd": "store_emptys"},

    "context": [{
        "key": "setting.auto_select",
        "operand": true,
        "operator": "equal"},
    {   "key": "selection_empty",
        "match_all": true,
        "operand": true,
        "operator": "equal" }]
}]
"""

##################################### DEBUG ####################################

def debug(*args):
    if DEBUG: print args

################################ REGION HELPERS ################################

def normalized_region(r):
    return sublime.Region(*(sorted((r.begin(), r.end())) + [r.meta()]))

def normalized_regions(rs):
    return (normalized_region(r) for r in rs)

def subtract_region(r1, r2):
    if not r1.contains(r2): r2 = r1.intersection(r2)

    r1s, r1e = r1.begin(), r1.end()
    r2s, r2e = r2.begin(), r2.end()

    if r1s == r2s and r1e == r2e:
        return []
    elif r1s == r2s:
        return [sublime.Region(r2e, r1e)]
    elif r1e == r2e:
        return [sublime.Region(r1s, r2s)]
    else:
        return [sublime.Region(r1s, r2s), sublime.Region(r2e, r1e)]

class PyRegionSet(list):
    def __init__(self, l=[], merge=False):
        if merge:
            list.__init__(self)
            for r in l: self.add(l)
        else:
            list.__init__(self, l)

    def _bisect(self, r, bisector):
        ix = min(bisector(self, r), len(self) -1)
        reg = self[ix]
        if r < reg and not (reg.contains(r) or reg.intersects(r)): ix -= 1
        return max(0, ix)

    def bisect(self, r):
        return self._bisect(r, bisect.bisect)

    def clear(self):
        del self[:]

    def contains(self, r):
        return self and self.closest_selection(r).contains(r)

    def closest_selection(self, r):
        return self[self.bisect(r)]

    def add(self, r):
        if not self: return self.append(r)

        for ix in xrange(self.bisect(r), -1, -1):
            closest = self[ix]
            debug( 'r:',       r)
            debug( 'ix:',      ix)
            debug( 'closest:', closest)
            debug( 'self:',    self)

            if closest.contains(r) or closest.intersects(r):
                debug( 'closest big')
                self[ix] = closest.cover(r)
                return

            elif r.contains(closest) or r.intersects(closest):
                debug( 'r big')
                r = r.cover(closest)
                if ix: del self[ix]
                else: self[ix] = r 
            else:
                debug( 'isolated insert', ix+1)
                self.insert(ix+1, r)
                return

    def subtract(self, r):
        ix = self.bisect(r)

        while self:
            closest = self[ix]

            if closest.contains(r) or closest.intersects(r):
                del self[ix]
                for reg in subtract_region(closest, r):
                    bisect.insort(self, reg)

                if ix == len(self): break
                continue
            break

def test_PyRegionSet():
    cb = sublime.set_clipboard
    def eq(d1, d2, msg='Objects unequal'):
        if d1 != d2:
            if not isinstance(d1, basestring):
                d1, d2 = map(pprint.pformat, (d1, d2))

            cb(d1)
            diff_msg = ('\n' + '\n'.join(difflib.ndiff(
                           d1.splitlines(),
                           d2.splitlines())))
            raise ValueError('%s:\n\n:%s' % (msg, diff_msg))

    RS = PyRegionSet

    class R(sublime.Region):
        def __repr__(self):
            return 'R%s' % sublime.Region.__repr__(self)

    def PRS(*pts):
        def inner(buf=[]): # fucking stupid linter
            for i, pt in enumerate(pts):
                if i % 2: # 1
                    buf.append(pt)
                    yield R(*buf)
                else: # 0
                    buf=[pt]
        r = RS(inner())
        cb = lambda r: sublime.set_clipboard("assert r == %r" % r)
        s = lambda *a: r.subtract(R(*a)) or cb(r)
        a = lambda *a: r.add(R(*a)) or cb(r)
        return r, s, a

    r, s, a = PRS(1,1,  5,15,  19,19)
    eq(r.closest_selection(R(5, 7)), r[1])

    ALL_TESTS = 1

    if ALL_TESTS:
        r, S, A = PRS(0, 10)
        A(5, 15)
        ex = [R(0, 15)]
        eq (r, ex)

    if ALL_TESTS:
        r, S, A = PRS(0, 15)
        A(20, 30)
        eq(r, [R(0, 15), R(20, 30)])
        A(25, 30)

    if ALL_TESTS:
        r, S, A = PRS(0, 15, 20, 30)

        A(56, 100)
        A(80, 300)

        eq (r, [R(0, 15), R(20, 30), R(56, 300)])

        A(16, 18)
        eq (r, [R(0, 15), R(16, 18), R(20, 30), R(56, 300)])

        S(0, 10)
        eq (r, [R(10, 15), R(16, 18), R(20, 30), R(56, 300)])

        S(5, 80)
        eq (r, [R(80, 300)])

        r.clear()
        eq (r, [])

    if ALL_TESTS:
        r, s, a = PRS(1,1, 2,2, 3,3, 5,8)
        s(2)
        eq (r, [R(1, 1), R(3, 3), R(5, 8)])

    
    if ALL_TESTS:
        r, s, a = PRS(1,1,  5,15, 19,19)
        assert R(5, 7) < R(5, 15)
        s(5, 7)
        eq (r, [R(1, 1), R(7, 15), R(19, 19)])

    if ALL_TESTS:
        r, s, a = PRS(1,1, 19,19)
        a(1, 2)
        eq (r, [R(1, 2), R(19, 19)])

if TESTS: test_PyRegionSet()

################################################################################

def auto_on(view):
    view.settings().set(KEY, True)
    view.set_status(KEY,  '%s: on' % KEY.title())

def auto_off(view):
    view.settings().set(KEY, False)
    view.erase_status(KEY)

class AutoSelectListener(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        if view.settings().get(KEY):
            if all(s.empty() for s in view.sel()):
                existing_regions = PyRegionSet (
                    normalized_regions( view.get_regions(KEY)) )

                sels = [s for s in view.get_regions(KEY + '.selections' ) if s]

                for sel in normalized_regions(sels):
                    if existing_regions.contains(sel):
                        existing_regions.subtract(sel)
                    else:
                        existing_regions.add(sel)

                view.add_regions(KEY, existing_regions, SCOPE, 1)

            view.add_regions( KEY+'.selections', list(view.sel()), '',
                              sublime.HIDDEN )

class AutoSelect(sublime_plugin.TextCommand):
    def run(self, edit, cmd=INIT):
        view = self.view

        if cmd == INIT:
            view.erase_regions(KEY+'.selections')
            view.erase_regions(KEY)
            view.add_regions(KEY, list(s for s in view.sel() if not s), SCOPE,1)
            return auto_on(view)

        if cmd == STOREEMPTYS:
            regions = PyRegionSet(view.get_regions(KEY))

            if all(regions.contains(s) for s in view.sel()):
                cmd = MERGE
            else:
                return view.add_regions ( KEY,   regions + list(view.sel()),
                                          SCOPE, 1 )

        if cmd == MERGE:
            auto_selected = view.get_regions(KEY)

            if auto_selected:
                existing = list(normalized_regions(view.sel()))
                view.sel().clear()
                for sel in auto_selected + existing: view.sel().add(sel)
                view.erase_regions(KEY)

            auto_off(view)