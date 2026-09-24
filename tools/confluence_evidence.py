#!/usr/bin/env python3
"""Publish the Phase 2 test evidence to a Confluence page tree.

Sources live in ../communication (the test plan and results workbooks, the
RESULTS.md files in the evidence folders, the findings write-ups, and the
test protocol sheets). Raw session logs stay local and are cited by folder
and session id.

Tree produced (under the Confluence parent you name):

  ELD Phase 2 Test Evidence
    Test Evidence · Failure Mode Findings              communication/2026-09-24 Failure Mode Findings - Phase 2 Prototype.md
    Test Evidence · Test Plan and Acceptance Criteria   Tracker-ELD Test Plan - Phase 2.xlsx
    Test Evidence · React Native Android Results        2026-08-31 Android Re-cert - Pixel 7.xlsx
    Test Evidence · React Native iOS Results            ios-evidence/RESULTS.md
    Test Evidence · Native Android Results              one child per native-android-evidence-*/RESULTS.md
    Test Evidence · Native iOS Results                  ios-native-findings.md + one child per ios-evidence/*-native/RESULTS.md
    Test Evidence · Test Protocols                      one child per protocol sheet (HTML), PDF attached

Build only:   ../communication/xlenv/bin/python tools/confluence_evidence.py
Publish:      set -a; . ./.env.confluence.local; set +a; export CONFLUENCE_PARENT_ID=3761831940
              ../communication/xlenv/bin/python tools/confluence_evidence.py --publish [--only KEY,...]

Needs beautifulsoup4, markdown and openpyxl (all in communication/xlenv).
"""
import argparse, glob, json, os, re, sys
import markdown, openpyxl
from bs4 import BeautifulSoup, Tag, NavigableString, Comment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from confluence_export import Confluence, macro, validate, esc_attr, inner_html, text_of  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
COMM = os.path.abspath(os.path.join(ROOT, '..', 'communication'))
ROOT_TITLE = 'ELD Phase 2 Test Evidence'
FINDINGS_MD = os.path.join(COMM, '2026-09-24 Failure Mode Findings - Phase 2 Prototype.md')
PLAN_XLSX = os.path.join(COMM, 'Tracker-ELD Test Plan - Phase 2.xlsx')
RN_ANDROID_XLSX = os.path.join(COMM, '2026-08-31 Android Re-cert - Pixel 7.xlsx')
RN_IOS_MD = os.path.join(COMM, 'ios-evidence', 'RESULTS.md')
IOS_FINDINGS_MD = os.path.join(COMM, 'ios-native-findings.md')


class Page:
    def __init__(self, key, title, parent_key=None):
        self.key, self.title, self.parent_key = key, title, parent_key
        self.body = ''
        self.attachments = []
        self.children_macro = False


# ----------------------------------------------------------------------------
# Converters
# ----------------------------------------------------------------------------

def clean_xhtml(soup):
    """Make bs4 output acceptable storage format."""
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for el in soup.find_all(True):
        for attr in list(el.attrs):
            if attr not in ('href', 'colspan', 'rowspan'):
                del el[attr]
    for a in soup.find_all('a', href=True):
        if not a['href'].startswith(('http:', 'https:', 'mailto:')):
            a.unwrap()
    html = inner_html(soup)
    html = re.sub(r'<(br|hr)\s*/?>', r'<\1/>', html)
    # Confluence shows a newline inside a paragraph as a line break: collapse
    # source wrapping everywhere except inside code macro bodies.
    parts = re.split(r'(<!\[CDATA\[.*?\]\]>)', html, flags=re.S)
    html = ''.join(p if p.startswith('<![CDATA[') else re.sub(r'\s*\n\s*', ' ', p) for p in parts)
    return html


def md_to_storage(text, drop_h1=True):
    """Markdown -> storage format. The first h1 becomes the page title (returned), not body."""
    html = markdown.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists'])
    soup = BeautifulSoup(html, 'html.parser')
    title = None
    h1 = soup.find('h1')
    if h1 is not None:
        title = text_of(h1)
        if drop_h1:
            h1.decompose()
    for pre in soup.find_all('pre'):
        code = pre.get_text()
        pre.replace_with(BeautifulSoup(macro('code', {'language': 'text'}, code), 'html.parser'))
    for el in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
        pass  # keep levels: h2 is the top level under the page title
    return clean_xhtml(soup), title


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def cell(v):
    if v is None:
        return ''
    if hasattr(v, 'strftime'):
        return v.strftime('%m/%d/%Y').lstrip('0').replace('/0', '/')
    s = str(v)
    return esc(s).replace('\n', '<br/>')


def xlsx_to_storage(path):
    """Each sheet: title rows as headings, key/value rows as paragraphs, blocks of
    multi-column rows as tables (first row of a block is the header, single-cell
    rows inside a block are section rows)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f'<h2>{esc(ws.title)}</h2>')
        rows = [[c for c in r] for r in ws.iter_rows(values_only=True)]
        i = 0
        while i < len(rows):
            r = rows[i]
            vals = [cell(c) for c in r]
            n = sum(1 for v in vals if v)
            if n == 0:
                i += 1
                continue
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            nxt_n = sum(1 for c in (nxt or []) if c not in (None, ''))
            if n >= 3:
                # table block
                ncols = max(len(vals), 1)
                out.append('<table><tbody>')
                out.append('<tr>' + ''.join(f'<th>{v}</th>' for v in vals) + '</tr>')
                i += 1
                while i < len(rows):
                    r = rows[i]
                    vals = [cell(c) for c in r]
                    m = sum(1 for v in vals if v)
                    if m == 0:
                        break
                    if m == 1 and vals[0]:
                        out.append(f'<tr><td colspan="{ncols}"><b>{vals[0]}</b></td></tr>')
                    else:
                        out.append('<tr>' + ''.join(f'<td>{v}</td>' for v in vals) + '</tr>')
                    i += 1
                out.append('</tbody></table>')
                continue
            if n == 1 and vals[0] and i == 0:
                out.append(f'<h3>{vals[0]}</h3>')
            elif n == 1 and vals[0] and nxt_n >= 3:
                out.append(f'<h3>{vals[0]}</h3>')
            elif n == 1 and vals[0]:
                out.append(f'<p>{vals[0]}</p>')
            else:
                k = vals[0].rstrip(':')
                rest = ' · '.join(v for v in vals[1:] if v)
                out.append(f'<p><b>{k}:</b> {rest}</p>')
            i += 1
    return ''.join(out)


def protocol_to_storage(path):
    """A test protocol sheet (HTML with checkboxes and blanks) -> storage format."""
    soup = BeautifulSoup(open(path, encoding='utf-8').read(), 'html.parser')
    body = soup.body
    for t in body.find_all(['style', 'script', 'footer']):
        t.decompose()
    title = text_of(body.h1) if body.h1 else os.path.basename(path)
    if body.h1:
        body.h1.decompose()
    for b in body.find_all('span', class_='box'):
        cl = b.get('class') or []
        b.replace_with('☑ ' if 'checked' in cl else ('☒ ' if 'failed' in cl else '☐ '))
    for f in body.find_all('span', class_='fill'):
        val = text_of(f)
        f.replace_with(BeautifulSoup(' <u>' + (esc(val) if val else '________') + '</u> ', 'html.parser'))
    for v in body.find_all('p', class_='verdict'):
        v.replace_with(BeautifulSoup('<blockquote><p>' + inner_html(v) + '</p></blockquote>', 'html.parser'))
    for r in body.find_all(['div', 'p'], class_='result'):
        r.name = 'p'
        r['class'] = ['done-result']
    for t in body.find_all('span', class_='t'):
        t.replace_with(' (' + text_of(t) + ')')
    for line in body.find_all('div', class_='line'):
        lab = line.find('span')
        if lab is not None:
            lab.replace_with(BeautifulSoup('<b>' + text_of(lab) + ':</b> ', 'html.parser'))
        line.name = 'p'
    for k in body.find_all('div', class_='key'):
        k.replace_with(BeautifulSoup('<blockquote><p>' + inner_html(k) + '</p></blockquote>', 'html.parser'))
    for n in body.find_all(['div', 'p'], class_='note'):
        if 'done-result' in (n.get('class') or []):
            continue
        n.name = 'p'
        n.insert(0, BeautifulSoup('<i>Note: </i>', 'html.parser'))
    for r in body.find_all('p', class_='done-result'):
        txt = inner_html(r)
        txt = re.sub(r'^\s*Result:\s*', '', txt)
        r.replace_with(BeautifulSoup('<p><b>Result:</b> ' + txt + '</p>', 'html.parser'))
    for s in body.find_all('p', class_='sub'):
        s.replace_with(BeautifulSoup('<p><i>' + inner_html(s) + '</i></p>', 'html.parser'))
    for el in body.find_all(['div', 'span', 'section', 'header']):
        el.unwrap()
    # a note div that sat inside an li now is a p inside the li; fine for storage format
    html = clean_xhtml(body)
    # collapse source wrapping
    html = re.sub(r'\s*\n\s*', ' ', html)
    return html, title


# ----------------------------------------------------------------------------
# Tree
# ----------------------------------------------------------------------------

def md_page(key, path, title, parent, fallback_title=None):
    body, h1 = md_to_storage(open(path, encoding='utf-8').read())
    p = Page(key, title or h1 or fallback_title, parent)
    lead = f'<p><i>Source: {esc(os.path.relpath(path, COMM))}</i></p>' if h1 is None else f'<p><b>{esc(h1)}</b></p>'
    p.body = lead + body
    return p


def build():
    pages, order = {}, []

    def add(p):
        pages[p.key] = p
        order.append(p.key)
        return p

    root = add(Page('ev-root', ROOT_TITLE))
    root.children_macro = True
    root.body = ('<p>Evidence from the Phase 2 hardware validation of the Tenna ELD prototype against the Geometris WQ '
                 'tracker: the test plan with acceptance criteria, the executed results for the React Native and native '
                 'builds on Android and iOS, the failure-mode findings with root causes and fixes, and the protocol '
                 'sheets each closing test was run from.</p>'
                 '<p>Raw evidence is the per-session JSONL log the app writes (one file per part, named by session id). '
                 'AppAxis keeps the full set, about 740 MB. Every result below cites its evidence folder and session id, '
                 'so any claim can be checked against the log on request.</p>'
                 '<p>Hardware: Pixel 7 (Android 16), iPhone 17 Pro Max (iOS 26.6.1), WQ trackers 0218 (bench), '
                 'DD:6E (Ford F-150) and 0266 (Toyota).</p>')

    # Failure-mode findings (the criterion 2 write-up), when drafted
    if os.path.exists(FINDINGS_MD):
        add(md_page('ev-findings', FINDINGS_MD, 'Test Evidence · Failure Mode Findings', root.key))

    plan = add(Page('ev-plan', 'Test Evidence · Test Plan and Acceptance Criteria', root.key))
    plan.body = ('<p>The 35 scenarios every build was run against: Tenna\'s 15 connectivity cases (Mark Leszczynski, '
                 '8/27/2026) plus the AppAxis scenarios added for the Phase 2 exit. Acceptance criteria are AppAxis '
                 'proposals, conditionally approved by Tom Cuthbertson on 9/15/2026. Workbook attached.</p>'
                 + xlsx_to_storage(PLAN_XLSX))
    plan.attachments.append((os.path.basename(PLAN_XLSX), PLAN_XLSX))

    rna = add(Page('ev-rn-android', 'Test Evidence · React Native Android Results', root.key))
    rna.body = ('<p>Pixel 7, React Native build. First sheet: the test list with the acceptance criteria as run on '
                '8/30/2026. Second sheet: the clean re-certification run of 8/31/2026 with the previous and final result '
                'per test and the findings F-1 to F-4 and D-1. Workbook attached.</p>' + xlsx_to_storage(RN_ANDROID_XLSX))
    rna.attachments.append((os.path.basename(RN_ANDROID_XLSX), RN_ANDROID_XLSX))

    add(md_page('ev-rn-ios', RN_IOS_MD, 'Test Evidence · React Native iOS Results', root.key))

    android = add(Page('ev-android', 'Test Evidence · Native Android Results', root.key))
    android.children_macro = True
    android.body = ('<p>Native Android (Kotlin) build on the Pixel 7, 9/10/2026 to 9/16/2026: the drive tests on the '
                    'Toyota and the closing tests A to E. One page per evidence folder, in date order.</p>')
    for i, path in enumerate(sorted(glob.glob(os.path.join(COMM, 'native-android-evidence-*', 'RESULTS.md')))):
        folder = os.path.basename(os.path.dirname(path))
        add(md_page(f'ev-android-{i:02d}', path, None, android.key, fallback_title=folder))

    ios = add(Page('ev-ios', 'Test Evidence · Native iOS Results', root.key))
    ios.children_macro = True
    ios.body = ('<p>Native iOS (Swift) build on the iPhone 17 Pro Max, 9/7/2026 to 9/21/2026: the field runs on the '
                'Ford and the Toyota, the kill and walk-up tests, and the findings F-5 to F-10 with their fixes. '
                'One page per evidence folder, in date order, findings first.</p>')
    add(md_page('ev-ios-findings', IOS_FINDINGS_MD, 'Native iOS · Findings F-5 to F-10', ios.key))
    for i, path in enumerate(sorted(glob.glob(os.path.join(COMM, 'ios-evidence', '2026*-native', 'RESULTS.md')))):
        folder = os.path.basename(os.path.dirname(path))
        add(md_page(f'ev-ios-{i:02d}', path, None, ios.key, fallback_title=folder))

    protos = add(Page('ev-protocols', 'Test Evidence · Test Protocols', root.key))
    protos.children_macro = True
    protos.body = ('<p>The sheets each closing test and drive test was run from: build, phone, tracker, and the steps '
                   'with what to record at each, filled in from the session files afterwards (☑ done and passed, '
                   '☒ done with a failure or finding, ☐ not run, recorded values underlined, a Result line where the '
                   'log adds something). Results were verified from the session log, never from the sheet alone. '
                   'PDF of the blank sheet attached.</p>')
    files = sorted(glob.glob(os.path.join(COMM, 'Native *.html')) + glob.glob(os.path.join(COMM, 'Drive Test*.html')))
    for i, path in enumerate(files):
        stem = os.path.splitext(os.path.basename(path))[0]
        filled = os.path.join(COMM, 'protocols-filled', os.path.basename(path))
        src = filled if os.path.exists(filled) else path
        body, h1 = protocol_to_storage(src)
        p = add(Page(f'ev-proto-{i:02d}', f'Protocol · {stem}', protos.key))
        lead = ('' if src == filled else
                '<p><i>Blank sheet as run; results are on the results pages and in the session files.</i></p>')
        p.body = f'<p><b>{esc(h1)}</b></p>' + lead + body
        pdf = os.path.splitext(path)[0] + '.pdf'
        if os.path.exists(pdf):
            p.attachments.append((os.path.basename(pdf), pdf))

    # unique titles (Confluence requires it per space)
    seen = {}
    for k in order:
        t = pages[k].title
        if t in seen:
            pages[k].title = f'{t} ({k})'
        seen[t] = k
    for k in order:
        p = pages[k]
        if p.children_macro:
            p.body += '<h2>Pages</h2>' + macro('children', {'all': 'true'})
        validate(p)
    return pages, order


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'confluence-evidence'))
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--parent', default=os.environ.get('CONFLUENCE_PARENT_ID'))
    ap.add_argument('--only', default='', help='comma-separated page keys to publish')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    pages, order = build()
    manifest = []
    for k in order:
        p = pages[k]
        open(os.path.join(args.out, f'{k}.xml'), 'w', encoding='utf-8').write(p.body)
        manifest.append({'key': k, 'title': p.title, 'parent': p.parent_key, 'attachments': [a[0] for a in p.attachments]})
    json.dump(manifest, open(os.path.join(args.out, 'manifest.json'), 'w'), indent=2)
    print(f'built {len(order)} pages in {args.out}')
    for m in manifest:
        depth, k = 0, m['parent']
        while k:
            depth += 1
            k = pages[k].parent_key
        print(f'{"  " * depth}{m["title"]}  ({len(pages[m["key"]].body)//1024} KB, {len(m["attachments"])} att)')
    if not args.publish:
        return
    base, email, token = (os.environ.get(k) for k in ('CONFLUENCE_BASE', 'CONFLUENCE_EMAIL', 'CONFLUENCE_TOKEN'))
    if not (base and email and token and args.parent):
        sys.exit('publish needs CONFLUENCE_BASE, CONFLUENCE_EMAIL, CONFLUENCE_TOKEN and CONFLUENCE_PARENT_ID')
    cf = Confluence(base, email, token)
    space_id = cf.page(args.parent)['spaceId']
    only = {x.strip() for x in args.only.split(',') if x.strip()}
    ids = {}
    for k in order:
        p = pages[k]
        if only and k not in only:
            continue
        if p.parent_key and p.parent_key not in ids:
            found = cf.find(space_id, pages[p.parent_key].title)
            if not found:
                sys.exit(f'{p.title}: parent "{pages[p.parent_key].title}" is not published yet')
            ids[p.parent_key] = found['id']
        parent_id = ids[p.parent_key] if p.parent_key else args.parent
        pid, what = cf.upsert(space_id, parent_id, p.title, p.body)
        ids[k] = pid
        existing = cf.attachments(pid) if p.attachments else {}
        for fname, path in p.attachments:
            try:
                cf.attach(pid, fname, path, existing)
            except RuntimeError as e:
                print(f'  WARNING attachment {fname}: {e}')
        try:
            cf.set_full_width(pid)
        except RuntimeError as e:
            print(f'  WARNING full width: {e}')
        print(f'{what} {p.title} -> {base}/wiki/spaces/TS/pages/{pid}')


if __name__ == '__main__':
    main()
