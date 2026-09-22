#!/usr/bin/env python3
"""Lint the wireframes (public/index.html) against Tenna's formatting
standards from Tom Caliendo's 9/21/2026 UX audit, for one revision.

Run: python3 tools/wf_lint.py [vN]        default: the latest revision
     python3 tools/wf_lint.py v11 --regress 1a2d545
                                           also checks that every earlier
                                           revision reads identically to
                                           that git commit: screen frames,
                                           annotations and headings fail
                                           the run; site prose (the map,
                                           the legend) is reported only

It reads the text a reader sees for that revision (data-rev-from / -until on
blocks, data-revi-from / -until inline) and checks, per screen:

  S1  title case on titles, buttons, field labels, table headers, cells,
      pills, list-row titles and status chips (the SCOPE classes below)
  S2  dates as MM/DD/YYYY and times as HH:MM AM/PM inside mockups
  S3  speed as "N MPH"
  S4  durations as HHh MMm SSs (no H:MM, no "6 min", no "7 d 18 h");
      every time range shows its duration beside it (judgment call 4)
      and joins its ends with → (judgment call 9)
  S5  miles as a decimal with the word miles, no thousands separator;
      one decimal place (109.5 miles), never 0.25 or a bare integer
  S6  N/A only where the screen says why the value is unavailable
      drivers as first and last name (no "M. Alvarez"), vehicles as fleet
      number and asset name (no "Unit 218")
  prose: annotations and legend use m/d/yyyy, no em dash, no "carries"
      hyphenated duration abbreviations (11-h, 30-min, 8-day) are S4 misses
  S1  the sentence test counts only alphabetic words on the label side of a
      "Label: value" chip, so "Audit period: 02/20/2026 – 08/20/2026 ▾" is a
      two-word label; the value side after the colon is not case-checked
  consistency: the same label text spelled two ways on two screens; a
      sign-in surface that says Sign In or Sign Out instead of Log In / Log Out;
      a screen that names a control on another screen (CLAIMS below) which
      that screen does not draw
  navigation: every visible app bar has a back control (‹) unless the
      screen is in NO_BACK (judgment call 6); every sheet has a Cancel or a
      second choice
  structure (index and the other pages): unbalanced tags, duplicate ids,
      duplicate attributes, unresolved same-page and cross-page anchors, and
      revision markup that can never show (a -from element inside an
      ancestor whose -until is earlier)

  S4  minutes, hours or seconds in words on a value or label line (fewer
      than SENTENCE_WORDS words) is a finding (judgment call 10); the
      reverse too: HHh MMm SSs after for, by, after, before or within in a
      sentence (SENTENCE_WORDS words or more), or opening a sentence that
      goes on with before, after or until, is a finding (judgment call 10)

Warnings, printed but not counted: the same duration shown on two
adjacent lines, and dead markup (a -until element inside a later -from
ancestor).

Judgment calls, decided 9/22/2026 so they are not re-decided every pass
(the same list is in the v11 What changed block on the page):

  1. App bar sub-notes (.ph-appbar .r), scenario labels (.ph-state), .sub
     headings and <small> captions are captions, not status values. They
     stay lowercase and are not linted for case.
  2. Event origins (automatic, manual, driver, auto, edited) are lowercase
     data values everywhere.
  3. Values inside table cells and pills follow title case, the same as
     the labels around them. A string of SENTENCE_WORDS words or more is a
     sentence and keeps sentence case, unless it is a button, header,
     title or field label (the ALWAYS roles).
  4. Wherever a time range is shown, its duration is shown next to it as
     HHh MMm SSs.
  5. D16 and the W18 officer box and table keep the Appendix A display
     format and are exempt from S1 to S6. The D16 status bar, its button
     and the W18 filter row are not exempt.
  6. D18 and D32 have no back control; D15, D16 and D31 leave only by PIN
     or password. Not a finding.
  7. A dash marks a value that is pending or none; N/A marks a value
     confirmed unavailable, and the screen says why.
  8. Dates in site prose are m/d/yyyy. Dates inside mockups are
     MM/DD/YYYY.
  9. A date shown with a time ends in the home terminal zone (ET), on
     both ends of a range. A time range uses one arrow (→); a date range
     uses a spaced en dash (–). Table cells (td) are in the title-case scope, and place
     names in cells are title case, as Tenna's site record spells them.
 10. (9/22/2026, internal, not on the page) A duration inside a sentence
     stays in words ("off for 10 minutes", "after 60 minutes idle").
     Calendar spans counted in days or months (an 8-day clock, a 182-day
     export window, 6-month retention) are counts, not durations, and stay
     in words. HHh MMm SSs applies to elapsed time shown as a value or a
     label: a clock, a stat, a cell, a chip.

Exit status 1 when anything is found."""
import re, sys, subprocess, os
from html.parser import HTMLParser

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
INDEX = os.path.join(ROOT, 'index.html')

def versions():
    js = open(os.path.join(ROOT, 'revisions.js'), encoding='utf-8').read()
    return re.findall(r"\{ id: '(v\d+)'", js)

ORDER = versions()
def vi(v): return ORDER.index(v)

# Elements whose text is a title, label, button, header, pill or status value.
SCOPE = {'ph-appbar-t', 'ph-btn', 'ph-label', 'ph-card-h', 'ph-li-b', 'th', 'wb-btn',
         'wb-pill', 'wb-h', 'ph-tab', 'ph-confirm-main', 'ph-toggle-main', 'ph-li-a',
         'ph-state-x', 'ph-chip', 'ph-field-label', 'wb-stat-label', 'td'}
# Captions and prose, never linted for case (judgment call 1).
CAPTION = {'small', 'sub', 'ph-note', 'ph-banner', 'ph-appbar-r', 'ph-state', 'wb-note', 'ph-field'}
# Exempt frames (judgment call 5).
EXEMPT_SCREENS = {'d16'}
EXEMPT_CLASSES = {'wb-box', 'wb-table'}          # inside W18 only
EXEMPT_IN = {'w18'}

# AP style: short function words that may stay lowercase mid-title.
LOWER_OK = {'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'at', 'by', 'in', 'of',
            'on', 'to', 'as', 'if', 'per', 'vs', 'via', 'up', 'with'}
# Words that are data, units or names and are correct lowercase anywhere.
DATA_OK = {'miles', 'mile', 'since', 'ago', 'left', 'radius', 'from', 'odo', 'reg.', 'rev',
           'v0.9.0', 'e9262cb', 'm.alvarez', 'j.whitfield', 'eRODS', 'app.tenna.com', 'fmcsa.dot.gov',
           'dBm', 'h', 'm', 's', 'mo', 'ET', 'MPH', 'TLV', 'TLV,', 'protocol', 'proto', 'ack', 'of',
           # event origins are lowercase data values (judgment call 2)
           'automatic', 'manual', 'driver', 'auto', 'edited', 'v3',
           # connectives inside a changed-range value: "was 04:30 PM → 05:15 PM, now 04:30 PM → 05:30 PM"
           'was', 'now'}
# Strings of this many words or more are sentences, not labels, and keep
# sentence case (judgment call 1), except in the ALWAYS roles.
SENTENCE_WORDS = 5
ALWAYS = {'ph-btn', 'wb-btn', 'th', 'ph-appbar-t', 'wb-h', 'ph-label', 'ph-card-h', 'ph-tab'}
# Screens whose app bar has no back control on purpose (judgment call 6).
NO_BACK = {'d15', 'd16', 'd18', 'd31', 'd32'}
# A screen that names a control on another screen: (screen, other screen, text the other screen must show).
CLAIMS = [('w19', 'w15', 'Odometer Jump Threshold')]
# Regulatory phrases that spell a period in words and are not S4 durations.
DURATION_PHRASES = r'24-hour|70 hours / 8 days|60 hours / 7 days|30-minute-in-24-hour|6-month|8th hour|30-minute break|8-day|30-day|8 days|24 hours|8 hours'
OTHER_PAGES = ['architecture.html', 'decisions.html', 'certification.html', 'stack-research.html', 'api-docs.html']

class Extractor(HTMLParser):
    """Visible text per screen for a revision, plus the label strings."""
    def __init__(self, ver):
        super().__init__(convert_charrefs=True)
        self.ver = vi(ver); self.stack = []; self.screens = {}; self.order = []
        self.cur = None; self.part = None; self.labels = []; self.collect = []
        self.prose = []; self.ui = []      # (screen, 'appbar'|'sheet', text, button count)

    def visible(self, a):
        f = a.get('data-rev-from') or a.get('data-revi-from')
        u = a.get('data-rev-until') or a.get('data-revi-until')
        return not ((f and vi(f) > self.ver) or (u and vi(u) < self.ver))

    def hidden(self): return any(f['hid'] for f in self.stack)
    def in_caption(self): return any(f['cap'] for f in self.stack)
    def in_exempt(self):
        return self.cur in EXEMPT_SCREENS or (self.cur in EXEMPT_IN and any(f['ex'] for f in self.stack))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs); cls = (a.get('class') or '').split()
        hid = tag in ('style', 'script') or not self.visible(a)
        par = self.stack[-1]['cls'] if self.stack else []
        # role of this element in the label scope
        role = None
        if 'ph-appbar' in par and 't' in cls: role = 'ph-appbar-t'
        elif 'ph-appbar' in par and 'r' in cls: role = 'ph-appbar-r'
        elif 'ph-card' in par and 'h' in cls: role = 'ph-card-h'
        elif 'ph-li' in par and 'b' in cls: role = 'ph-li-b'
        elif 'ph-li' in par and 'a' in cls: role = 'ph-li-a'
        elif 'ph-confirm' in par and tag == 'span': role = 'ph-confirm-main'
        elif 'ph-toggle' in par and tag == 'span' and 'sw' not in cls: role = 'ph-toggle-main'
        elif 'ph-tabbar' in par: role = 'ph-tab'
        elif 'wb-stat' in par and tag == 'small': role = 'wb-stat-label'
        elif tag == 'th': role = 'th'
        elif tag == 'td': role = 'td'
        else:
            for c in ('ph-btn', 'ph-label', 'wb-btn', 'wb-pill', 'wb-h', 'ph-chip', 'ph-note',
                      'ph-banner', 'ph-state', 'wb-note', 'ph-field', 'sub'):
                if c in cls: role = c; break
            if role is None and tag == 'small': role = 'small'
        frame = {'tag': tag, 'cls': cls, 'hid': hid, 'cap': role in CAPTION,
                 'ex': bool(EXEMPT_CLASSES & set(cls)), 'role': role, 'buf': None}
        if 'wf-item' in cls and not hid and not self.hidden():
            self.cur = a.get('id'); self.order.append(self.cur)
            self.screens[self.cur] = {'frame': [], 'annot': [], 'head': []}; frame['item'] = True
        if self.cur:
            if 'wf-frame-col' in cls: self.part = 'frame'; frame['part'] = True
            elif 'wf-annot' in cls: self.part = 'annot'; frame['part'] = True
        if role in SCOPE and self.part == 'frame' and not hid and not self.hidden() \
                and not self.in_caption() and not self.in_exempt():
            frame['buf'] = []
        if self.cur and self.part == 'frame' and not hid and not self.hidden():
            if 'ph-appbar' in cls or 'ph-sheet' in cls:
                frame['ui'] = 'appbar' if 'ph-appbar' in cls else 'sheet'; frame['uibuf'] = []; frame['btns'] = 0
            if 'ph-btn' in cls:
                for f in self.stack:
                    if f.get('ui') == 'sheet': f['btns'] += 1
        self.stack.append(frame)
        if tag == 'br': self.emit('\n'); self.stack.pop()
        elif tag in ('img', 'input', 'hr', 'meta', 'link', 'wbr', 'source'): self.stack.pop()
        elif tag in ('div', 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'td', 'th', 'section', 'ul', 'table', 'dt', 'dd', 'label'):
            self.emit('\n')

    def emit(self, t):
        if self.hidden(): return
        if self.cur and self.part: self.screens[self.cur][self.part].append(t)
        elif self.cur: self.screens[self.cur]['head'].append(t)
        else: self.prose.append(t)

    def handle_data(self, d):
        if self.hidden(): return
        self.emit(d)
        for f in self.stack:
            if f['buf'] is not None and not self.in_caption(): f['buf'].append(d)
            if f.get('uibuf') is not None: f['uibuf'].append(d)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                for f in self.stack[i:]:
                    if f.get('item'): self.cur = None
                    if f.get('part'): self.part = None
                    if f['buf'] is not None:
                        t = re.sub(r'\s+', ' ', ''.join(f['buf'])).strip()
                        if t: self.labels.append((self.cur_id, f['role'], t))
                    if f.get('uibuf') is not None:
                        self.ui.append((self.cur_id, f['ui'], re.sub(r'\s+', ' ', ''.join(f['uibuf'])).strip(), f['btns']))
                del self.stack[i:]
                if tag in ('div', 'p', 'li', 'td', 'th', 'tr', 'h1', 'h2', 'h3', 'h4'): self.emit('\n')
                return

    @property
    def cur_id(self): return self.cur

def norm(parts):
    t = ''.join(parts); t = re.sub(r'[ \t\u00a0]+', ' ', t)
    t = re.sub(r' *\n *', '\n', t); return re.sub(r'\n+', '\n', t).strip()

def extract(path, ver):
    x = Extractor(ver); x.feed(open(path, encoding='utf-8').read())
    extract.ui = x.ui
    return x.order, {k: {'frame': norm(v['frame']), 'annot': norm(v['annot']), 'head': norm(v['head'])} for k, v in x.screens.items()}, x.labels, norm(x.prose)

def label_side(t):
    """The label part of a "Label: value" chip; the whole string otherwise."""
    m = re.match(r'^(.*?[A-Za-z\)]): (?!\d\d (AM|PM))', t)
    return m.group(1) if m else t

def word_count(t):
    """Words in a label: tokens with a letter or digit, not counting times, dates, durations and zones."""
    n = 0
    for w in t.split(' '):
        core = w.strip('"“”\'‘’()[]·:;,.?!*›‹→←↓↗✓✗☐☑○◉◎●⚠+&')
        if not re.search(r'[A-Za-z0-9]', core): continue
        if re.fullmatch(r'\d+h|\d\dm|\d\ds|AM|PM|ET|\d\d?:\d\d|\d\d/\d\d/\d{4}', core): continue
        n += 1
    return n

def title_case_problems(t):
    words = t.split(' ')
    bad = []
    for i, w in enumerate(words):
        core = w.strip('"“”\'‘’()[]·:;,.?!*›‹→←↓↗✓✗☐☑○◉◎●⚠+&')
        if not core or not core[0].isalpha(): continue
        if core in DATA_OK or core.lower() in DATA_OK or re.fullmatch(r'v\d+', core): continue   # version markers (v1, v2, v3) are data values
        if core[0].islower():
            if i not in (0, len(words) - 1) and core.lower() in LOWER_OK: continue
            if "'" in core or '-' in core and core.split('-')[0][0].isupper(): continue
            bad.append(w)
    return bad

CHECKS = [
    ('S2 time without leading zero',      r'(?<![\d:])\d:\d\d ?(AM|PM)'),
    ('S2 24-hour time',                   r'(?<![\d:h])\d\d:\d\d(:\d\d)?(?! ?(AM|PM|ET))(?![\d:])'),
    ('S2 date not MM/DD/YYYY',            r'(?<![\d/])\d/\d{1,2}/\d{4}|(?<![\d/])\d{1,2}/\d/\d{4}'),
    ('S2 "Jul 2026" style month',         r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) 20\d\d\b'),
    ('S3 lowercase mph',                  r'\bmph\b'),
    ('S4 duration as H:MM',               r'(?<![\d:])\d{1,2}:\d\d(?! ?(AM|PM))(?![\d:])'),
    ('S4 duration in words',              r'\b\d+ ?(min|mins|h|hr|hrs|d)\b(?! ?\d)'),
    ('S4 hyphenated duration abbreviation', r'\b\d+-(h|hr|hrs|min|mins|d)\b'),
    ('S5 thousands separator',            r'\d,\d{3}'),
    ('S5 "mi" abbreviation',              r'\d ?mi\b'),
    ('S5 miles not to one decimal',        r'(?<![\d.])\d+ miles|\d\.\d{2,} miles'),
    ('S2 time range with en dash or hyphen', r'\d\d:\d\d (AM|PM)( ?[–-] ?)\d\d:\d\d (AM|PM)'),
    ('S2 date range not a spaced en dash', r'\d\d/\d\d/\d{4}(–|→| → |-| - )\d\d/\d\d/\d{4}'),
    ('name as initial',                   r'(?<![A-Za-z0-9)/])[A-Z]\. [A-Z][a-z]+'),
    ('vehicle as "Unit N"',               r'\bUnit \d+'),
]
NA_JUSTIFIED = {'w1'}   # screens whose note says why N/A appears (judgment call 7)

def lint(ver):
    order, screens, labels, prose = extract(INDEX, ver)
    out = []; warn = []
    for sid in order:
        fr = screens[sid]['frame']
        if sid in EXEMPT_SCREENS: continue
        body = fr
        if sid in EXEMPT_IN:
            # drop the exempt officer box and table text: lines that are Appendix A rows
            body = '\n'.join(l for l in fr.split('\n') if not re.match(r'^(0\d{3}$|\d\d:\d\d:\d\d$|[\d,]+\.\d$|ALVAREZ|UNIT 218|Wed 8/19/2026)', l))
        for name, pat in CHECKS:
            for m in re.finditer(pat, body):
                line = body[body.rfind('\n', 0, m.start()) + 1:]
                line = line.split('\n', 1)[0]
                if name.startswith('S2 date') and re.search(r'\d{1,2}/\d{1,2}/\d{4}', line) and sid == 'w4' and 'app.tenna.com' in line: continue
                out.append((sid, name, line.strip()[:100]))
        # judgment call 4: a time range shows its duration on the same line
        for line in body.split('\n'):
            if re.search(r'\d\d:\d\d (AM|PM)( ET)? → \d\d:\d\d (AM|PM)', line) and not re.search(r'\d\dh \d\dm \d\ds', line):
                out.append((sid, 'JC4 time range without a duration', line.strip()[:100]))
        # judgment call 9: a date shown with a time ends in ET
        for m in re.finditer(r'\d\d/\d\d/\d{4} · \d\d:\d\d (AM|PM)(?! ET)', body):
            line = body[body.rfind('\n', 0, m.start()) + 1:].split('\n', 1)[0]
            out.append((sid, 'JC9 date and time without a zone', line.strip()[:100]))
        if 'N/A' in fr and sid not in NA_JUSTIFIED:
            out.append((sid, 'S6 N/A without a stated reason', 'N/A'))
        an = screens[sid]['annot']
        for m in re.finditer(r'(?<!\d)0\d/\d\d/\d{4}', an):
            out.append((sid, 'prose date with leading zero', an[max(0, m.start() - 30):m.end() + 10].replace('\n', ' ')))
        for m in re.finditer(r'—|\bcarries\b', an + '\n' + fr):
            out.append((sid, 'em dash or "carries"', (an + '\n' + fr)[max(0, m.start() - 40):m.end() + 20].replace('\n', ' ')))
        # warnings: durations in words, the same duration on two adjacent lines
        lines = body.split('\n')
        for i, line in enumerate(lines):
            # judgment call 10: words in a sentence, HHh MMm SSs on a value or label line
            for m in re.finditer(r'\b\d+[- ](minutes?|hours?|seconds?)\b', line):
                around = line[max(0, m.start() - 12):m.end() + 12]
                if re.search(DURATION_PHRASES, around) or word_count(line) >= SENTENCE_WORDS: continue
                out.append((sid, 'S4 duration in words on a value line', line.strip()[:100]))
            # and the reverse: the code form inside a sentence
            if word_count(line) >= SENTENCE_WORDS and (
                    re.search(r'\b(for|by|after|before|within) [−-]?\d+h \d\dm \d\ds', line) or
                    re.match(r'\W*\d+h \d\dm \d\ds (before|after|until)\b', line)):
                out.append((sid, 'S4 duration code inside a sentence (JC10)', line.strip()[:100]))
            if i:
                for d in set(re.findall(r'\d+h \d\dm \d\ds', line)):
                    if d in lines[i - 1]: warn.append((sid, 'duration repeated on adjacent lines', '%s / %s' % (lines[i - 1].strip()[:45], line.strip()[:45])))
    # S1 on labels: the sentence test counts alphabetic words on the label side
    spellings = {}
    for sid, role, t in labels:
        if role == 'td' and t[:1] in '"“': continue   # a quoted remark in a cell is the driver's prose
        side = label_side(t)
        if role not in ALWAYS and word_count(side) >= SENTENCE_WORDS: continue
        bad = title_case_problems(side)
        if bad: out.append((sid, 'S1 title case (%s)' % role, '%s  <- %s' % (t[:80], ', '.join(bad))))
        if word_count(side) < SENTENCE_WORDS and re.search(r'[A-Za-z]', side):
            spellings.setdefault(side.lower(), {}).setdefault(side, set()).add(sid)
        if role in ('ph-btn', 'ph-appbar-t', 'ph-li-a', 'ph-card-h', 'wb-btn') and re.search(r'\bSign(ed)? (In|Out|in|out)\b', t):
            out.append((sid, 'one verb: Log In / Log Out', t[:80]))
    for key, forms in spellings.items():
        if len(forms) > 1:
            out.append(('multi', 'same label spelled two ways', ' | '.join('%s (%s)' % (f, ','.join(sorted(x.upper() for x in ss))) for f, ss in sorted(forms.items()))))
    # a screen that names a control on another screen
    for sid, other, text in CLAIMS:
        if sid in screens and other in screens and text.lower() not in screens[other]['frame'].lower():
            out.append((sid, 'claims a control %s does not draw' % other.upper(), text))
    # navigation: back control on every app bar, a way out of every sheet
    for sid, kind, text, btns in extract.ui:
        if kind == 'appbar' and '‹' not in text and sid not in NO_BACK:
            out.append((sid, 'app bar without a back control', text[:80]))
        if kind == 'sheet' and btns < 2 and 'Cancel' not in text:
            out.append((sid, 'sheet with no Cancel or second choice', text[:80]))
    for m in re.finditer(r'—|\bcarries\b|(?<!\d)0\d/\d\d/\d{4}', prose):
        out.append(('page', 'prose: em dash, "carries" or MM/DD/YYYY', prose[max(0, m.start() - 40):m.end() + 20].replace('\n', ' ')))
    seen = set(); uniq = []
    for f in out:
        if f not in seen: seen.add(f); uniq.append(f)
    lint.warnings = warn
    return uniq

VOID = {'br', 'img', 'input', 'hr', 'meta', 'link', 'wbr', 'source', 'col', 'area', 'base', 'embed', 'param', 'track'}

class Structure(HTMLParser):
    """Tag balance, ids, anchors, duplicate attributes and revision nesting for one page."""
    def __init__(self, ver):
        super().__init__(); self.ver = vi(ver); self.stack = []; self.ids = {}; self.hrefs = []
        self.problems = []; self.dead = 0
    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]; keys = [k for k, _ in attrs]
        for k in set(keys):
            if keys.count(k) > 1: self.problems.append(('duplicate attribute %s' % k, line, tag))
        a = dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids: self.problems.append(('duplicate id %s' % a['id'], line, tag))
            self.ids.setdefault(a['id'], line)
        if a.get('href'): self.hrefs.append((line, a['href']))
        f = a.get('data-rev-from') or a.get('data-revi-from'); u = a.get('data-rev-until') or a.get('data-revi-until')
        for k in ('data-rev-from', 'data-rev-until', 'data-revi-from', 'data-revi-until'):
            if a.get(k) and a[k] not in ORDER: self.problems.append(('unknown revision %s' % a[k], line, tag))
        for _, af, au, _ in self.stack:
            if af and u and u in ORDER and vi(u) < vi(af): self.dead += 1
            if au and f and f in ORDER and vi(f) > vi(au): self.problems.append(('never visible: from %s inside until %s' % (f, au), line, tag))
        if tag not in VOID: self.stack.append((tag, f, u, line))
    def handle_endtag(self, tag):
        if tag in VOID: return
        names = [x[0] for x in self.stack]
        if tag not in names: self.problems.append(('stray closing tag', self.getpos()[0], tag)); return
        i = len(names) - 1 - names[::-1].index(tag)
        for x in self.stack[i + 1:]: self.problems.append(('unclosed %s from line %d' % (x[0], x[3]), self.getpos()[0], tag))
        del self.stack[i:]

def structure(ver):
    pages = {}
    for fn in ['index.html'] + OTHER_PAGES:
        path = os.path.join(ROOT, fn)
        if not os.path.exists(path): continue
        p = Structure(ver); p.feed(open(path, encoding='utf-8').read())
        for x in p.stack: p.problems.append(('unclosed at end of file', x[3], x[0]))
        pages[fn] = p
    out = []; dead = 0
    for fn, p in pages.items():
        dead += p.dead
        for what, line, tag in p.problems: out.append((fn, what, 'line %d <%s>' % (line, tag)))
        for line, h in p.hrefs:
            if h.startswith('#') and h[1:] not in p.ids: out.append((fn, 'unresolved anchor', 'line %d %s' % (line, h)))
            elif re.match(r'^[a-z-]+\.html#', h):
                f, anchor = h.split('#', 1)
                if f in pages and anchor not in pages[f].ids: out.append((fn, 'unresolved cross-page anchor', 'line %d %s' % (line, h)))
            elif re.match(r'^[a-z-]+\.html$', h) and not os.path.exists(os.path.join(ROOT, h)): out.append((fn, 'missing page', 'line %d %s' % (line, h)))
    structure.dead = dead
    return out

def regress(commit, upto):
    base = subprocess.run(['git', 'show', '%s:public/index.html' % commit], capture_output=True, text=True,
                          cwd=os.path.join(ROOT, '..')).stdout
    tmp = os.path.join(ROOT, '..', '.wf_lint_base.html'); open(tmp, 'w', encoding='utf-8').write(base)
    base_js = subprocess.run(['git', 'show', '%s:public/revisions.js' % commit], capture_output=True, text=True,
                             cwd=os.path.join(ROOT, '..')).stdout
    base_versions = re.findall(r"\{ id: '(v\d+)'", base_js)
    diffs = []; prose_diffs = []
    try:
        # only revisions that existed in the base commit can be compared
        for v in [x for x in ORDER[:vi(upto)] if x in base_versions]:
            _, a, _, pa = extract(tmp, v); _, b, _, pb = extract(INDEX, v)
            for sid in b:
                if sid in a and a[sid] != b[sid]:
                    parts = ','.join(k for k in ('frame', 'annot', 'head') if a[sid].get(k) != b[sid].get(k))
                    diffs.append((v, '%s (%s)' % (sid, parts)))
                if sid not in a: diffs.append((v, sid + ' (new)'))
            if pa != pb:
                la, lb = pa.split('\n'), pb.split('\n')
                changed = [x for x in lb if x not in set(la)][:3]
                prose_diffs.append((v, '; '.join(x[:60] for x in changed) or 'lines removed'))
    finally:
        os.remove(tmp)
    regress.prose = prose_diffs
    return diffs

if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--regress' in argv: argv = argv[:argv.index('--regress')] + argv[argv.index('--regress') + 2:]
    args = [x for x in argv if not x.startswith('--')]
    ver = args[0] if args else ORDER[-1]
    findings = lint(ver) + structure(ver)
    for sid, kind, text in findings: print('%-5s %-40s %s' % (sid.upper(), kind, text))
    for sid, kind, text in lint.warnings: print('warn  %-5s %-40s %s' % (sid.upper(), kind, text))
    print('%s: %d finding(s), %d warning(s), %d dead revision span(s)' % (ver, len(findings), len(lint.warnings), structure.dead))
    rc = 1 if findings else 0
    if '--regress' in sys.argv:
        commit = sys.argv[sys.argv.index('--regress') + 1]
        d = regress(commit, ver)
        for v, sid in d: print('REGRESSION %s %s differs from %s' % (v, sid, commit))
        for what in dict.fromkeys(w for _, w in regress.prose):
            vs = [v for v, w in regress.prose if w == what]
            print('prose  %s to %s: site prose differs from %s (not counted): %s' % (vs[0], vs[-1], commit, what))
        print('regression against %s (revisions that exist there, below %s): %s' % (commit, ver, 'clean' if not d else '%d difference(s)' % len(d)))
        rc = rc or (1 if d else 0)
    sys.exit(rc)
