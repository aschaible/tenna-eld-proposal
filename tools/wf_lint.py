#!/usr/bin/env python3
"""Lint the wireframes (public/index.html) against Tenna's formatting
standards from Tom Caliendo's 9/21/2026 UX audit, for one revision.

Run: python3 tools/wf_lint.py [vN]        default: the latest revision
     python3 tools/wf_lint.py v11 --regress 1a2d545
                                           also checks that every earlier
                                           revision reads identically to
                                           that git commit

It reads the text a reader sees for that revision (data-rev-from / -until on
blocks, data-revi-from / -until inline) and checks, per screen:

  S1  title case on titles, buttons, field labels, table headers, cells,
      pills, list-row titles and status chips (the SCOPE classes below)
  S2  dates as MM/DD/YYYY and times as HH:MM AM/PM inside mockups
  S3  speed as "N MPH"
  S4  durations as HHh MMm SSs (no H:MM, no "6 min", no "7 d 18 h");
      every time range shows its duration beside it (judgment call 4)
      and joins its ends with → (judgment call 9)
  S5  miles as a decimal with the word miles, no thousands separator
  S6  N/A only where the screen says why the value is unavailable
      drivers as first and last name (no "M. Alvarez"), vehicles as fleet
      number and asset name (no "Unit 218")
  prose: annotations and legend use m/d/yyyy, no em dash, no "carries"

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
           'automatic', 'manual', 'driver', 'auto', 'edited', 'v3'}
# Strings of this many words or more are sentences, not labels, and keep
# sentence case (judgment call 1), except in the ALWAYS roles.
SENTENCE_WORDS = 5
ALWAYS = {'ph-btn', 'wb-btn', 'th', 'ph-appbar-t', 'wb-h', 'ph-label', 'ph-card-h', 'ph-tab'}

class Extractor(HTMLParser):
    """Visible text per screen for a revision, plus the label strings."""
    def __init__(self, ver):
        super().__init__(convert_charrefs=True)
        self.ver = vi(ver); self.stack = []; self.screens = {}; self.order = []
        self.cur = None; self.part = None; self.labels = []; self.collect = []
        self.prose = []

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
            self.screens[self.cur] = {'frame': [], 'annot': []}; frame['item'] = True
        if self.cur:
            if 'wf-frame-col' in cls: self.part = 'frame'; frame['part'] = True
            elif 'wf-annot' in cls: self.part = 'annot'; frame['part'] = True
        if role in SCOPE and self.part == 'frame' and not hid and not self.hidden() \
                and not self.in_caption() and not self.in_exempt():
            frame['buf'] = []
        self.stack.append(frame)
        if tag == 'br': self.emit('\n'); self.stack.pop()
        elif tag in ('img', 'input', 'hr', 'meta', 'link', 'wbr', 'source'): self.stack.pop()
        elif tag in ('div', 'p', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'td', 'th', 'section', 'ul', 'table', 'dt', 'dd', 'label'):
            self.emit('\n')

    def emit(self, t):
        if self.hidden(): return
        if self.cur and self.part: self.screens[self.cur][self.part].append(t)
        elif not self.cur: self.prose.append(t)

    def handle_data(self, d):
        if self.hidden(): return
        self.emit(d)
        if not self.in_caption():
            for f in self.stack:
                if f['buf'] is not None: f['buf'].append(d)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                for f in self.stack[i:]:
                    if f.get('item'): self.cur = None
                    if f.get('part'): self.part = None
                    if f['buf'] is not None:
                        t = re.sub(r'\s+', ' ', ''.join(f['buf'])).strip()
                        if t: self.labels.append((self.cur_id, f['role'], t))
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
    return x.order, {k: {'frame': norm(v['frame']), 'annot': norm(v['annot'])} for k, v in x.screens.items()}, x.labels, norm(x.prose)

def title_case_problems(t):
    words = t.split(' ')
    bad = []
    for i, w in enumerate(words):
        core = w.strip('"“”\'‘’()[]·:;,.?!*›‹→←↓↗✓✗☐☑○◉◎●⚠+&')
        if not core or not core[0].isalpha(): continue
        if core in DATA_OK or core.lower() in DATA_OK: continue
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
    ('S5 thousands separator',            r'\d,\d{3}'),
    ('S5 "mi" abbreviation',              r'\d ?mi\b'),
    ('S2 time range with en dash or hyphen', r'\d\d:\d\d (AM|PM)( ?[–-] ?)\d\d:\d\d (AM|PM)'),
    ('S2 date range not a spaced en dash', r'\d\d/\d\d/\d{4}(–|→| → |-| - )\d\d/\d\d/\d{4}'),
    ('name as initial',                   r'(?<![A-Za-z0-9)/])[A-Z]\. [A-Z][a-z]+'),
    ('vehicle as "Unit N"',               r'\bUnit \d+'),
]
NA_JUSTIFIED = {'w1'}   # screens whose note says why N/A appears (judgment call 7)

def lint(ver):
    order, screens, labels, prose = extract(INDEX, ver)
    out = []
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
    for sid, role, t in labels:
        if role not in ALWAYS and len(t.split(' ')) >= SENTENCE_WORDS: continue
        if role == 'td' and t[:1] in '"“': continue   # a quoted remark in a cell is the driver's prose
        bad = title_case_problems(t)
        if bad: out.append((sid, 'S1 title case (%s)' % role, '%s  <- %s' % (t[:80], ', '.join(bad))))
    for m in re.finditer(r'—|\bcarries\b|(?<!\d)0\d/\d\d/\d{4}', prose):
        out.append(('page', 'prose: em dash, "carries" or MM/DD/YYYY', prose[max(0, m.start() - 40):m.end() + 20].replace('\n', ' ')))
    seen = set(); uniq = []
    for f in out:
        if f not in seen: seen.add(f); uniq.append(f)
    return uniq

def regress(commit, upto):
    base = subprocess.run(['git', 'show', '%s:public/index.html' % commit], capture_output=True, text=True,
                          cwd=os.path.join(ROOT, '..')).stdout
    tmp = os.path.join(ROOT, '..', '.wf_lint_base.html'); open(tmp, 'w', encoding='utf-8').write(base)
    base_js = subprocess.run(['git', 'show', '%s:public/revisions.js' % commit], capture_output=True, text=True,
                             cwd=os.path.join(ROOT, '..')).stdout
    base_versions = re.findall(r"\{ id: '(v\d+)'", base_js)
    diffs = []
    try:
        # only revisions that existed in the base commit can be compared
        for v in [x for x in ORDER[:vi(upto)] if x in base_versions]:
            a = extract(tmp, v)[1]; b = extract(INDEX, v)[1]
            for sid in b:
                if sid in a and a[sid] != b[sid]: diffs.append((v, sid))
                if sid not in a: diffs.append((v, sid + ' (new)'))
    finally:
        os.remove(tmp)
    return diffs

if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--regress' in argv: argv = argv[:argv.index('--regress')] + argv[argv.index('--regress') + 2:]
    args = [x for x in argv if not x.startswith('--')]
    ver = args[0] if args else ORDER[-1]
    findings = lint(ver)
    for sid, kind, text in findings: print('%-5s %-40s %s' % (sid.upper(), kind, text))
    print('%s: %d finding(s)' % (ver, len(findings)))
    rc = 1 if findings else 0
    if '--regress' in sys.argv:
        commit = sys.argv[sys.argv.index('--regress') + 1]
        d = regress(commit, ver)
        for v, sid in d: print('REGRESSION %s %s differs from %s' % (v, sid, commit))
        print('regression against %s (revisions that exist there, below %s): %s' % (commit, ver, 'clean' if not d else '%d difference(s)' % len(d)))
        rc = rc or (1 if d else 0)
    sys.exit(rc)
