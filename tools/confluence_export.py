#!/usr/bin/env python3
"""Export the proposal site to a Confluence page tree.

The site stays the master. This script turns four site pages into Confluence
storage-format documents, renders diagrams and wireframe frames to PNG,
rewrites anchors and site links into Confluence links, and (with --publish)
creates or updates the pages and attachments through the Confluence Cloud
REST API.

Trees produced (under the Confluence parent you name):

  ELD Architecture                       public/architecture.html, sections 2-9 as children
  Tenna to ELD Data Contracts            T1-T8 as children, OpenAPI + Postman attached
  ELD Certification Roadmap              public/certification.html, one page
  ELD Wireframes                         public/index.html at its latest revision
    Wireframes · Mobile App                one child per screen group (D screens)
    Wireframes · Control Panel             one child per screen group (W screens)
    Wireframes · Data Element Inventory
    Wireframes · Ownership and API Surfaces
    Wireframes · Screen Flow Map
  ELD Decision Log                       public/decisions.html at its latest revision
    Decision Log · Product Decisions, Open Questions, Settled Questions, Meetings

Wireframe frames and the flow map are screenshots of the real page (served
over HTTP, latest revision) taken with puppeteer-core and the installed
Google Chrome; annotations become text next to each image.

Build only (writes build/confluence/*.xml, *.png and manifest.json):
    ../communication/xlenv/bin/python tools/confluence_export.py

Build and publish:
    set -a; . ./.env.confluence.local; set +a    # CONFLUENCE_BASE, _EMAIL, _TOKEN
    export CONFLUENCE_PARENT_ID=3761831940       # "Tenna ELD (TELD)"
    ../communication/xlenv/bin/python tools/confluence_export.py --publish [--only KEY,KEY]

Re-run after every site revision; pages are matched by title and updated in
place, attachments are replaced. --only limits the publish to the named page
keys (build file stems) or titles; --only wireframes publishes every page
whose key starts with "3", --only decisions every key starting with "4".

Needs beautifulsoup4 (in communication/xlenv), Google Chrome, node and
puppeteer-core (npm install --save-dev puppeteer-core).
"""
import argparse, base64, copy, json, mimetypes, os, re, socket, subprocess, sys, tempfile, time, uuid
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, NavigableString, Comment, Tag, CData

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
PUBLIC = os.path.join(ROOT, 'public')
SRC = os.path.join(PUBLIC, 'architecture.html')
CERT_SRC = os.path.join(PUBLIC, 'certification.html')
WF_SRC = os.path.join(PUBLIC, 'index.html')
DEC_SRC = os.path.join(PUBLIC, 'decisions.html')
API_DIR = os.path.join(PUBLIC, 'api')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

ARCH_TITLE = 'ELD Architecture'
CONTRACTS_TITLE = 'Tenna to ELD Data Contracts'
CERT_TITLE = 'ELD Certification Roadmap'
WF_TITLE = 'ELD Wireframes'
DEC_TITLE = 'ELD Decision Log'
ATTACH_FILES = ['tenna-eld-contracts.openapi.json', 'tenna-eld-contracts.postman_collection.json']

# Site path -> page key of the page that mirrors the whole site page (for links with no fragment)
SITE_ROOT_KEYS = {'/architecture': '00-architecture', '/certification': '20-certification',
                  '/': '30-wireframes', '/decisions': '40-decisions'}


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------

class Page:
    def __init__(self, key, title, parent_key=None, shift=1, site='/architecture'):
        self.key = key            # stable key, also the output file stem
        self.title = title
        self.parent_key = parent_key
        self.shift = shift        # heading levels to move up (h3 -> h2 when 1)
        self.site = site          # site path the content came from, for "#id" links
        self.root = _DOC.new_tag('div')   # the page's nodes, moved out of the source tree
        self.ids = set()          # anchor ids that live on this page
        self.title_ids = set()    # ids that resolve to the page itself (its heading in the source)
        self.attachments = []     # [(filename, local path)]
        self.children_macro = False
        self.body = ''            # storage format, filled by render()

    def add(self, node):
        """Move a source node into this page."""
        if isinstance(node, Comment):
            return
        if isinstance(node, NavigableString) and not node.strip():
            return
        self.root.append(node)

    def collect_ids(self):
        for el in self.root.find_all(id=True):
            self.ids.add(el['id'])


_DOC = BeautifulSoup('', 'html.parser')


def text_of(el):
    return re.sub(r'\s+', ' ', el.get_text()).strip()


def inner_html(el):
    return ''.join(str(c) for c in el.contents)


def frag(html):
    return BeautifulSoup(html, 'html.parser')


def has_class(el, *names):
    cl = el.get('class') or []
    return any(n in cl for n in names)


def alive(el):
    return not getattr(el, 'decomposed', False) and el.parent is not None


# ----------------------------------------------------------------------------
# Architecture and certification
# ----------------------------------------------------------------------------

def split_pages(soup):
    doc = soup.find('div', class_='doc')
    nodes = [n for n in doc.children if not (isinstance(n, NavigableString) and not n.strip())]

    pages, order = {}, []

    def add(page):
        pages[page.key] = page
        order.append(page.key)
        return page

    arch = add(Page('00-architecture', ARCH_TITLE, shift=0))
    arch.children_macro = True
    contracts = add(Page('10-data-contracts', CONTRACTS_TITLE, shift=0))
    contracts.children_macro = True
    contracts.ids.add('data-contracts')   # the h3 that becomes this page's title
    contracts.title_ids.add('data-contracts')

    current = arch
    section5 = None
    for n in nodes:
        if isinstance(n, Comment):
            continue
        if isinstance(n, Tag):
            if n.name == 'h1':
                continue
            if n.name == 'p' and 'docmeta' in (n.get('class') or []) and 'On this page' in n.get_text():
                continue
            if n.name == 'h2':
                sid = n.get('id', '')
                if sid == 's1':
                    current = arch
                    arch.add(n)         # keep "1. Context" as a heading on the parent page
                    continue
                current = add(Page(sid, text_of(n), parent_key=arch.key))
                if sid == 's5':
                    section5 = current
                continue
            if n.name == 'h3' and n.get('id') == 'data-contracts':
                current = contracts
                continue
            if n.name == 'h4' and (n.get('id') or '').startswith('dc-t'):
                current = add(Page(n['id'], text_of(n), parent_key=contracts.key, shift=2))
                continue
            if n.name == 'h3' and n.get('id') == 'home-terminal':
                current = section5
        current.add(n)

    for p in pages.values():
        # ids of the page heading itself (h2 s2..s9, h4 dc-t1..) resolve to the page top
        p.ids.add(p.key)
        p.title_ids.add(p.key)
    return pages, order


def certification_page(soup):
    """public/certification.html is short (five sections, no diagrams): one page."""
    page = Page('20-certification', CERT_TITLE, shift=0, site='/certification')
    doc = soup.find('div', class_='doc')
    for n in doc.children:
        if isinstance(n, Tag):
            if n.name == 'h1':
                continue
            if n.name == 'p' and 'subtitle' in (n.get('class') or []):
                continue
        page.add(n)
    page.ids.add(page.key)
    page.title_ids.add(page.key)
    return page


# ----------------------------------------------------------------------------
# Revisioned pages (wireframes, decision log)
# ----------------------------------------------------------------------------

def versions():
    js = open(os.path.join(PUBLIC, 'revisions.js'), encoding='utf-8').read()
    return re.findall(r"\{\s*id:\s*'(v\d+)'", js)


def apply_revision(soup, cur):
    """Keep what the site shows for revision `cur`; drop the other sides and the attributes."""
    order = versions()
    ci = order.index(cur)
    for el in list(soup.find_all(True)):
        if not alive(el):
            continue
        f = el.get('data-rev-from') or el.get('data-revi-from')
        u = el.get('data-rev-until') or el.get('data-revi-until')
        if (f in order and order.index(f) > ci) or (u in order and order.index(u) < ci):
            el.decompose()
    wc = soup.find(id='whats-changed')
    if wc:
        # only the block for the revision being mirrored; the site keeps the history
        for el in list(wc.find_all(attrs={'data-rev-from': True})):
            if not alive(el):
                continue
            if el.get('data-rev-from') != cur and not el.find_parent(attrs={'data-rev-from': cur}):
                el.decompose()
    for el in soup.find_all(True):
        for k in ('data-rev-from', 'data-rev-until', 'data-revi-from', 'data-revi-until',
                  'data-settled-from', 'data-owner'):
            if k in el.attrs:
                del el[k]


BADGES = ('tag', 'chip', 'rev-badge', 'gchip', 'o-chip')
LABELS = ('wf-label', 'q-label', 'rev-what-h', 'eyebrow')
DROP = ('jump', 'onpage', 'role', 'wf-group-head', 'hero-actions', 'revbar', 'filters')


def flatten(root):
    """Turn the site's card and badge markup into plain document markup, in place."""
    for el in list(root.find_all(True)):
        if alive(el) and has_class(el, *DROP):
            el.decompose()
    # badges -> [text]
    for el in list(root.find_all(['span', 'div'])):
        if alive(el) and has_class(el, *BADGES):
            el.replace_with(frag('<i>[' + text_of(el) + ']</i>'))
    # labels -> bold line
    for el in list(root.find_all(['span', 'div'])):
        if alive(el) and has_class(el, *LABELS):
            el.replace_with(frag('<p><b>' + text_of(el) + '</b></p>'))
    for el in list(root.find_all('span', class_='mono')):
        el.name = 'code'
        del el['class']
    for el in list(root.find_all('small')):
        if alive(el):
            el.replace_with(frag('<br/><i>' + inner_html(el) + '</i>'))
    # decision cards: "P1 · title" heading, chips line
    for head in list(root.find_all('div', class_='q-head')):
        if not alive(head):
            continue
        qid = head.find('span', class_='q-id')
        title = head.find('h3')
        chips = head.find('div', class_='q-chips')
        t = (text_of(qid) + ' · ' if qid else '') + (inner_html(title) if title else '')
        line = ' '.join(str(c) for c in chips.contents).strip() if chips else ''
        art = head.find_parent('article')
        h = frag('<h2>' + t + '</h2>').h2
        if art and art.get('id'):
            h['id'] = art['id']
            del art['id']
        head.replace_with(h)
        if line:
            h.insert_after(frag('<p>' + line + '</p>'))
    # wireframe items: "D1 · Login" heading above the frame, tags line
    for head in list(root.find_all('div', class_='wf-head')):
        if not alive(head):
            continue
        wid = head.find('span', class_='wf-id')
        name = head.find('h4')
        rest = [c for c in head.contents if c is not wid and c is not name]
        t = (text_of(wid) + ' · ' if wid else '') + (inner_html(name) if name else '')
        line = ' '.join(str(c) for c in rest).strip()
        item = head.find_parent('div', class_='wf-item')
        h = frag('<h2>' + t + '</h2>').h2
        if item is not None:
            if item.get('id'):
                h['id'] = item['id']
                del item['id']
            item.insert(0, h)
            head.decompose()
        else:
            head.replace_with(h)
        if line:
            h.insert_after(frag('<p>' + line + '</p>'))
    # surface cards: "T1 · Identity" heading, meta as a list
    for head in list(root.find_all('div', class_='sfc-head')):
        if not alive(head):
            continue
        sid = head.find('span', class_='sfc-id')
        name = head.find('h4')
        t = (text_of(sid) + ' · ' if sid else '') + (inner_html(name) if name else '')
        art = head.find_parent('article')
        h = frag('<h3>' + t + '</h3>').h3
        if art is not None and art.get('id'):
            h['id'] = art['id']
            del art['id']
        head.replace_with(h)
    for meta in list(root.find_all('div', class_='sfc-meta')):
        items = ''
        for s in meta.find_all('span', recursive=False):
            b = s.find('b')
            if b is None:
                continue
            val = ''.join(str(c) for c in s.contents if c is not b)
            items += '<li><b>' + text_of(b) + ':</b> ' + val + '</li>'
        meta.replace_with(frag('<ul>' + items + '</ul>'))
    for lbl in list(root.find_all('span', class_='lbl')):
        if alive(lbl):
            lbl.replace_with(frag('<p><i>' + inner_html(lbl) + '</i></p>'))
    # timeline: "date · title" heading, who line
    for item in list(root.find_all('div', class_='tl-item')):
        date = item.find('div', class_='tl-date')
        card = item.find('div', class_='tl-card')
        h3 = card.find('h3') if card else None
        t = (text_of(date) + ' · ' if date else '') + (inner_html(h3) if h3 else '')
        if date:
            date.decompose()
        if h3:
            h3.replace_with(frag('<h2>' + t + '</h2>'))
    for who in list(root.find_all('div', class_='tl-who')):
        if alive(who):
            who.replace_with(frag('<p><i>' + inner_html(who) + '</i></p>'))
    # legend items: badge folded into the paragraph
    for li in list(root.find_all('div', class_='legend-item')):
        i = li.find('i', recursive=False)
        p = li.find('p', recursive=False)
        if i is not None and p is not None:
            p.insert(0, ' ')
            p.insert(0, i.extract())
    # source chips read "T1 · Identity: explanation"
    for chip in list(root.find_all(class_='src-chip')):
        if alive(chip):
            chip.insert_after(': ')
    # data-element lists: "text [tag] [tag]"
    for tags in list(root.find_all('span', class_='tags')):
        tags.insert(0, ' ')
        tags.unwrap()
    # containers -> gone, ids kept on the first block inside
    for el in list(root.find_all(['div', 'section', 'article', 'header', 'span', 'nav', 'footer', 'u'])):
        if not alive(el):
            continue
        if el.get('id'):
            h = el.find(['h2', 'h3', 'h4'])
            if h is not None and not h.get('id'):
                h['id'] = el['id']
            elif h is None:
                first = el.find(['p', 'ul', 'table'])
                if first is not None and not first.get('id'):
                    first['id'] = el['id']
        el.unwrap()


def screenshots(shot_list, out_dir, port=8765):
    """Serve public/ over HTTP and screenshot the listed selectors on the latest revision."""
    if not shot_list:
        return
    nm = None
    for cand in [os.path.join(ROOT, 'node_modules'), os.environ.get('NODE_PATH', '')]:
        if cand and os.path.isdir(os.path.join(cand, 'puppeteer-core')):
            nm = cand
            break
    if not nm:
        raise SystemExit('puppeteer-core not found: npm install --save-dev puppeteer-core (or set NODE_PATH)')
    with socket.socket() as s:
        s.settimeout(0.2)
        busy = s.connect_ex(('127.0.0.1', port)) == 0
    server = None
    if not busy:
        server = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--directory', PUBLIC,
                                   '--bind', '127.0.0.1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
    try:
        ver = versions()[-1]
        js = open(os.path.join(PUBLIC, 'revisions.js'), encoding='utf-8').read()
        slug_ = re.search(r"id: '%s'.*?slug: '([^']+)'" % ver, js).group(1)
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump([{'selector': sel, 'out': os.path.join(out_dir, fname)} for sel, fname in shot_list], f)
            lst = f.name
        env = dict(os.environ, NODE_PATH=nm)
        r = subprocess.run(['node', os.path.join(HERE, 'wf_shots.js'), f'http://127.0.0.1:{port}/?v={slug_}', lst],
                           capture_output=True, text=True, timeout=900, env=env)
        os.unlink(lst)
        print(r.stdout.strip())
        if r.returncode:
            raise SystemExit('screenshots failed: ' + r.stderr[-800:])
    finally:
        if server:
            server.terminate()


def image_tag(soup, fname, width=None, alt=''):
    img = soup.new_tag('ac:image')
    if width:
        img['ac:width'] = str(width)
    if alt:
        img['ac:alt'] = alt
    att = soup.new_tag('ri:attachment')
    att['ri:filename'] = fname
    img.append(att)
    return img


def wireframe_pages(soup, out_dir, take_shots=True):
    """public/index.html (already at one revision) -> ELD Wireframes tree."""
    pages, order = {}, []

    def add(page):
        pages[page.key] = page
        order.append(page.key)
        return page

    root = add(Page('30-wireframes', WF_TITLE, shift=0, site='/'))
    root.children_macro = True
    root.title_ids.add(root.key)

    # frames -> screenshots, before the DOM is flattened
    shots = []
    for item in soup.find_all('div', class_='wf-item'):
        iid = item.get('id')
        col = item.find('div', class_='wf-frame-col')
        if not iid or col is None:
            continue
        fname = f'{iid}.png'
        # the frame itself, not the grid column (which stretches to the annotation's height)
        shots.append((f'#{iid} .wf-phone, #{iid} .wf-web', fname))
        alt = text_of(item.find('h4')) if item.find('h4') else iid
        width = 300 if iid.startswith('d') else 900
        col.replace_with(image_tag(soup, fname, width=width, alt=alt))
        item.attrs['data-shot'] = fname
    flow = soup.find(id='flow')
    flow_svg = flow.find('svg') if flow else None
    if flow_svg is not None:
        shots.append(('#flow svg', 'screen-flow-map.png'))
        flow_svg.replace_with(image_tag(soup, 'screen-flow-map.png', width=900, alt='Screen flow map'))
    if take_shots:
        screenshots(shots, out_dir)

    wc = soup.find(id='whats-changed')
    legend = soup.find(id='legend')
    driver = soup.find(id='driver')
    web = soup.find(id='web')
    data = soup.find(id='data')
    sources = soup.find(id='sources')

    root.add(frag('<p>Wireframes for the Tenna ELD driver app (D screens) and the control panel inside the '
                  'Tenna portal (W screens), with the data each screen uses and the open questions on it. '
                  'The five product decisions the screens depended on are settled and recorded in the '
                  '<a href="/decisions">Decision Log</a>.</p>').p)
    if wc:
        root.add(frag('<h2 id="whats-changed">What changed in this revision</h2>').h2)
        for n in list(wc.find('div', class_='container').children):
            if isinstance(n, Tag) and n.name == 'div':
                for c in list(n.children):
                    if isinstance(c, Tag) and c.name == 'h2':
                        c.decompose()
                root.add(n)
        root.add(frag('<p>Earlier revisions are kept on the site, with a version switch at the bottom right '
                      'of the page.</p>').p)
    if legend:
        for n in list(legend.find('div', class_='container').children):
            root.add(n)
    root.ids.update({'whats-changed', 'legend', 'decisions', 'top'})

    def group_pages(section, parent, prefix):
        cont = section.find('div', class_='container')
        for n in list(cont.children):
            if isinstance(n, Tag) and n.name == 'div' and has_class(n, 'wf-group'):
                gh = n.find('div', class_='wf-group-head')
                h3 = gh.find('h3') if gh else None
                rng = gh.find('span', class_='range') if gh else None
                gtitle = text_of(h3) if h3 else n.get('id', 'group')
                rtext = text_of(rng) if rng else ''
                rtext = re.sub(r'new \d+/\d+/\d+', '', rtext).strip(' ·\xa0')
                title = f'{prefix} · {gtitle}' + (f' ({rtext})' if rtext else '')
                gp = add(Page('3' + n['id'], title, parent_key=parent.key, shift=0, site='/'))   # 3g-auth: key 3* = wireframes
                gp.title_ids.add(n['id'])
                gp.ids.add(n['id'])
                for c in list(n.children):
                    if isinstance(c, Tag) and c.name == 'div' and has_class(c, 'wf-group-head'):
                        continue
                    if isinstance(c, Tag) and c.name == 'div' and has_class(c, 'wf-item'):
                        fname = c.attrs.pop('data-shot', None)
                        if fname:
                            gp.attachments.append((fname, os.path.join(out_dir, fname)))
                    gp.add(c)
            elif isinstance(n, Tag) and n.name == 'h2':
                continue
            else:
                parent.add(n)

    mobile = add(Page('31-mobile', 'Wireframes · Mobile App', parent_key=root.key, shift=0, site='/'))
    mobile.children_macro = True
    mobile.title_ids.add('driver')
    mobile.ids.add('driver')
    group_pages(driver, mobile, 'Wireframes')

    panel = add(Page('32-web', 'Wireframes · Control Panel', parent_key=root.key, shift=0, site='/'))
    panel.children_macro = True
    panel.title_ids.add('web')
    panel.ids.add('web')
    group_pages(web, panel, 'Wireframes')

    def section_page(key, title, section, tid):
        p = add(Page(key, title, parent_key=root.key, shift=0, site='/'))
        p.title_ids.add(tid)
        p.ids.add(tid)
        for n in list(section.find('div', class_='container').children):
            if isinstance(n, Tag) and n.name == 'h2':
                continue
            p.add(n)
        return p

    if data:
        section_page('33-data', 'Wireframes · Data Element Inventory', data, 'data')
    if sources:
        section_page('34-sources', 'Wireframes · Ownership and API Surfaces', sources, 'sources')
    if flow:
        fp = section_page('35-flow', 'Wireframes · Screen Flow Map', flow, 'flow')
        fp.attachments.append(('screen-flow-map.png', os.path.join(out_dir, 'screen-flow-map.png')))
    return pages, order


def decision_pages(soup):
    """public/decisions.html (already at one revision) -> ELD Decision Log tree."""
    pages, order = {}, []

    def add(page):
        pages[page.key] = page
        order.append(page.key)
        return page

    root = add(Page('40-decisions', DEC_TITLE, shift=0, site='/decisions'))
    root.children_macro = True
    root.title_ids.add(root.key)
    hero = soup.find('section', class_='hero')
    if hero:
        for n in list(hero.find('div', class_='container').children):
            if isinstance(n, Tag) and (n.name == 'h1' or has_class(n, 'docmeta', 'subtitle')):
                continue
            root.add(n)
    wc = soup.find(id='whats-changed')
    if wc:
        root.add(frag('<h2 id="whats-changed">What changed in this revision</h2>').h2)
        for n in list(wc.find('div', class_='container').children):
            root.add(n)
        root.add(frag('<p>Earlier revisions are kept on the site, with a version switch at the bottom right '
                      'of the page.</p>').p)
    root.ids.update({'whats-changed', 'top'})

    for key, title, sid in [('41-product', 'Decision Log · Product Decisions', 'product'),
                            ('42-open', 'Decision Log · Open Questions', 'open'),
                            ('43-answered', 'Decision Log · Settled Questions', 'answered'),
                            ('44-meetings', 'Decision Log · Meetings', 'meetings')]:
        section = soup.find(id=sid)
        if not section:
            continue
        p = add(Page(key, title, parent_key=root.key, shift=0, site='/decisions'))
        p.title_ids.add(sid)
        p.ids.add(sid)
        for n in list(section.find('div', class_='container').children):
            if isinstance(n, Tag) and n.name == 'h2':
                # the section's own heading reads as the page's lead line
                p.add(frag('<p><b>' + inner_html(n) + '</b></p>').p)
                continue
            p.add(n)
    return pages, order


# ----------------------------------------------------------------------------
# Rendering one page to storage format
# ----------------------------------------------------------------------------

def macro(name, params=None, body=None, rich=False):
    s = f'<ac:structured-macro ac:name="{name}" ac:schema-version="1" ac:macro-id="{uuid.uuid4()}">'
    for k, v in (params or {}).items():
        s += f'<ac:parameter ac:name="{k}">{v}</ac:parameter>'
    if body is not None:
        if rich:
            s += f'<ac:rich-text-body>{body}</ac:rich-text-body>'
        else:
            s += f'<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>'
    return s + '</ac:structured-macro>'


def anchor_macro(name):
    return macro('anchor', {'': name})


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]


def render_svg_png(svg, out_png):
    """Rasterise one inline SVG with headless Chrome at 2x."""
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', str(svg))
    w, h = (int(m.group(1)), int(m.group(2))) if m else (760, 400)
    html = ('<!doctype html><html><head><meta charset="utf-8"><style>'
            'html,body{margin:0;background:#fff}svg{display:block;width:%dpx;height:%dpx}'
            '</style></head><body>%s</body></html>' % (w, h, str(svg)))
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        src = f.name
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
           f'--window-size={w},{h}', f'--screenshot={out_png}', 'file://' + src]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    os.unlink(src)
    if not os.path.exists(out_png):
        raise RuntimeError(f'Chrome did not write {out_png}: {r.stderr[-400:]}')
    return w


def esc_attr(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


def resolve_link(href, page, pages, id_map):
    """A site href -> (target page, anchor id) when the target is mirrored, else None."""
    if href.startswith(('http:', 'https:', 'mailto:')):
        return None
    path, _, fragment = href.partition('#')
    site = page.site if path == '' else path
    if site != '/':
        site = site.rstrip('/')
    if fragment and site in id_map and fragment in id_map[site]:
        target = pages[id_map[site][fragment]]
        return target, ('' if fragment in target.title_ids else fragment)
    if not fragment and site in SITE_ROOT_KEYS and SITE_ROOT_KEYS[site] in pages:
        return pages[SITE_ROOT_KEYS[site]], ''
    return None


def render(page, pages, id_map, site_base, out_dir):
    doc = BeautifulSoup('<div></div>', 'html.parser')
    root = doc.div
    for n in list(page.root.children):
        root.append(copy.copy(n))

    # 1. Diagrams: SVG -> PNG attachment
    for i, svg in enumerate(root.find_all('svg')):
        label = svg.get('aria-label') or f'diagram {i+1}'
        fname = f'{page.key}-{i+1}-{slug(label)}.png'
        width = render_svg_png(svg, os.path.join(out_dir, fname))
        page.attachments.append((fname, os.path.join(out_dir, fname)))
        svg.replace_with(image_tag(doc, fname, width=width, alt=label))

    # 2. Unwrap table wrappers, drop comments and classes
    for d in root.find_all('div', class_='tbl-wrap'):
        d.unwrap()
    for d in root.find_all('div', class_='stage'):
        d.unwrap()
    for g in root.find_all('p', class_='gate'):
        g.replace_with(frag('<blockquote><p>' + inner_html(g) + '</p></blockquote>'))
    for c in root.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for el in root.find_all(True):
        for attr in ('class', 'role', 'aria-label', 'download', 'style', 'title', 'data-shot', 'target', 'rel'):
            if attr in el.attrs and el.name not in ('ac:image',):
                del el[attr]

    # 3. Headings: shift levels, inject anchors for every id
    for el in root.find_all(['h2', 'h3', 'h4', 'h5']):
        lvl = int(el.name[1]) - page.shift
        el.name = f'h{max(1, min(6, lvl))}'
    for el in list(root.find_all(id=True)):
        aid = el['id']
        del el['id']
        marker = doc.new_tag('anchor-placeholder')
        marker['data-name'] = aid
        if el.name == 'tr':
            cell = el.find(['td', 'th'])
            (cell or el).insert(0, marker)
        elif el.name == 'table':
            cell = el.find(['th', 'td'])
            (cell or el).insert(0, marker)
        elif el.name in ('ul', 'ol'):
            li = el.find('li')
            (li or el).insert(0, marker)
        else:
            el.insert(0, marker)

    # 4. Links
    for a in root.find_all('a', href=True):
        href = a['href']
        inner = inner_html(a)
        hit = resolve_link(href, page, pages, id_map)
        if hit:
            target, anchor_id = hit
            anchor = f' ac:anchor="{anchor_id}"' if anchor_id else ''
            ref = '' if target.key == page.key else f'<ri:page ri:content-title="{esc_attr(target.title)}"/>'
            if not anchor and not ref:
                a.replace_with(frag(inner))
                continue
            a.replace_with(frag(f'<ac:link{anchor}>{ref}<ac:link-body>{inner}</ac:link-body></ac:link>'))
        elif href.startswith('#'):
            a.replace_with(frag(inner))
        elif href.startswith('/api/') and os.path.basename(href) in ATTACH_FILES:
            fname = os.path.basename(href)
            a.replace_with(frag(f'<ac:link><ri:attachment ri:filename="{fname}"/>'
                                f'<ac:link-body>{inner}</ac:link-body></ac:link>'))
        elif href.startswith('/'):
            a['href'] = site_base.rstrip('/') + href
        # absolute http links pass through

    # 5. Code blocks
    for pre in root.find_all('pre'):
        code = pre.get_text()
        pre.replace_with(frag(macro('code', {'language': 'text'}, code)))

    # 5b. Collapse source-file line wrapping: Confluence keeps newlines inside a
    # paragraph as line breaks, so every wrapped line of HTML would show as one.
    for s in list(root.find_all(string=True)):
        if isinstance(s, (CData, Comment)) or s.find_parent('ac:plain-text-body'):
            continue
        if '\n' in s or '  ' in s:
            s.replace_with(re.sub(r'\s+', ' ', s))

    body = inner_html(root)
    body = re.sub(r'<anchor-placeholder data-name="([^"]+)"></anchor-placeholder>',
                  lambda m: anchor_macro(m.group(1)), body)
    body = re.sub(r'<(ri:(?:page|attachment)[^>]*?)(?<!/)></ri:(?:page|attachment)>', r'<\1/>', body)
    body = body.replace('<br>', '<br/>')

    # 6. Page furniture
    tail = ''
    if page.children_macro:
        tail = '<h2>Sections</h2>' + macro('children', {'all': 'true'})
    page.body = body + tail


def validate(page):
    """Storage format must be well-formed XML with the ac/ri namespaces."""
    wrapped = ('<root xmlns:ac="urn:ac" xmlns:ri="urn:ri">' + page.body + '</root>')
    try:
        ET.fromstring(wrapped)
    except ET.ParseError as e:
        dbg = os.path.join(ROOT, 'build', 'confluence', f'{page.key}.invalid.xml')
        os.makedirs(os.path.dirname(dbg), exist_ok=True)
        open(dbg, 'w').write(page.body)
        raise SystemExit(f'{page.key}: not well-formed: {e} (body saved to {dbg})')


# ----------------------------------------------------------------------------
# Confluence Cloud REST
# ----------------------------------------------------------------------------

class Confluence:
    def __init__(self, base, email, token):
        self.base = base.rstrip('/')
        self.auth = 'Basic ' + base64.b64encode(f'{email}:{token}'.encode()).decode()

    def req(self, method, path, data=None, headers=None, raw=None):
        url = self.base + path
        h = {'Authorization': self.auth, 'Accept': 'application/json'}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            h['Content-Type'] = 'application/json'
        if raw is not None:
            body = raw
        h.update(headers or {})
        r = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(r) as resp:
                t = resp.read()
                return json.loads(t) if t else {}
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'{method} {path} -> {e.code}: {e.read()[:600].decode(errors="replace")}')

    def page(self, pid):
        return self.req('GET', f'/wiki/api/v2/pages/{pid}')

    def find(self, space_id, title):
        q = urllib.parse.urlencode({'space-id': space_id, 'title': title, 'status': 'current'})
        res = self.req('GET', f'/wiki/api/v2/pages?{q}').get('results', [])
        return res[0] if res else None

    def upsert(self, space_id, parent_id, title, body):
        existing = self.find(space_id, title)
        if existing:
            cur = self.req('GET', f'/wiki/api/v2/pages/{existing["id"]}?body-format=storage')
            ver = cur['version']['number'] + 1
            data = {'id': existing['id'], 'status': 'current', 'title': title, 'parentId': str(parent_id),
                    'body': {'representation': 'storage', 'value': body},
                    'version': {'number': ver, 'message': 'confluence_export.py'}}
            res = self.req('PUT', f'/wiki/api/v2/pages/{existing["id"]}', data)
            return res['id'], 'updated'
        data = {'spaceId': str(space_id), 'status': 'current', 'title': title, 'parentId': str(parent_id),
                'body': {'representation': 'storage', 'value': body}}
        res = self.req('POST', '/wiki/api/v2/pages', data)
        return res['id'], 'created'

    def attachments(self, page_id):
        res = self.req('GET', f'/wiki/api/v2/pages/{page_id}/attachments?limit=250').get('results', [])
        return {a['title']: (a['id'], a.get('fileSize')) for a in res}

    def attach(self, page_id, fname, path, existing):
        """Create the attachment, or upload a new version if the name exists."""
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(fname)[0] or 'application/octet-stream'
        with open(path, 'rb') as f:
            content = f.read()
        parts = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{fname}"\r\n'
                 f'Content-Type: {ctype}\r\n\r\n').encode() + content + \
                (f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="minorEdit"\r\n\r\ntrue'
                 f'\r\n--{boundary}--\r\n').encode()
        headers = {'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-Atlassian-Token': 'nocheck'}
        att_id, size = existing.get(fname, (None, None))
        if att_id and size == len(content):
            return   # unchanged; Confluence rejects a new version with identical bytes
        if att_id:
            path_ = f'/wiki/rest/api/content/{page_id}/child/attachment/{att_id}/data'
        else:
            path_ = f'/wiki/rest/api/content/{page_id}/child/attachment'
        self.req('POST', path_, raw=parts, headers=headers)

    def set_full_width(self, page_id):
        """Content appearance: full width, so the wide tables are not squeezed."""
        for key in ('content-appearance-published', 'content-appearance-draft'):
            props = self.req('GET', f'/wiki/api/v2/pages/{page_id}/properties?key={key}').get('results', [])
            if props:
                pr = props[0]
                if pr.get('value') == 'full-width':
                    continue
                self.req('PUT', f'/wiki/api/v2/pages/{page_id}/properties/{pr["id"]}',
                         {'key': key, 'value': 'full-width',
                          'version': {'number': pr['version']['number'] + 1}})
            else:
                self.req('POST', f'/wiki/api/v2/pages/{page_id}/properties', {'key': key, 'value': 'full-width'})


# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'confluence'))
    ap.add_argument('--site-base', default='https://appaxis-eld-build.vercel.app')
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--parent', default=os.environ.get('CONFLUENCE_PARENT_ID'),
                    help='Confluence page id the trees are created under')
    ap.add_argument('--only', default='',
                    help='comma-separated page keys or titles to publish; "wireframes" = keys 3*, "decisions" = keys 4*')
    ap.add_argument('--skip-shots', action='store_true', help='reuse the PNGs already in --out (no Chrome run)')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    pages, order = {}, []

    def merge(p, o):
        pages.update(p)
        order.extend(o)

    with open(SRC, encoding='utf-8') as f:
        merge(*split_pages(BeautifulSoup(f.read(), 'html.parser')))
    with open(CERT_SRC, encoding='utf-8') as f:
        cert = certification_page(BeautifulSoup(f.read(), 'html.parser'))
    pages[cert.key] = cert
    order.append(cert.key)

    cur = versions()[-1]
    with open(WF_SRC, encoding='utf-8') as f:
        wf = BeautifulSoup(f.read(), 'html.parser')
    apply_revision(wf, cur)
    p, o = wireframe_pages(wf, args.out, take_shots=not args.skip_shots)
    for pg in p.values():
        flatten(pg.root)
    merge(p, o)
    with open(DEC_SRC, encoding='utf-8') as f:
        dec = BeautifulSoup(f.read(), 'html.parser')
    apply_revision(dec, cur)
    p, o = decision_pages(dec)
    for pg in p.values():
        flatten(pg.root)
    merge(p, o)

    # ids per site, so "/decisions#q24" and "/#d1" resolve across trees
    id_map = {}
    for key in order:
        pg = pages[key]
        pg.collect_ids()
        for aid in pg.ids:
            id_map.setdefault(pg.site, {}).setdefault(aid, key)

    for key in order:
        render(pages[key], pages, id_map, args.site_base, args.out)
        validate(pages[key])
    contracts = pages['10-data-contracts']
    for fname in ATTACH_FILES:
        contracts.attachments.append((fname, os.path.join(API_DIR, fname)))

    manifest = []
    for key in order:
        pg = pages[key]
        path = os.path.join(args.out, f'{key}.xml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(pg.body)
        manifest.append({'key': key, 'title': pg.title, 'parent': pg.parent_key, 'site': pg.site,
                         'file': os.path.basename(path), 'attachments': [a[0] for a in pg.attachments]})
    with open(os.path.join(args.out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'built {len(order)} pages in {args.out} (site revision {cur})')
    for m in manifest:
        depth, k = 0, m['parent']
        while k:
            depth += 1
            k = pages[k].parent_key
        print(f'{"  " * depth}{m["title"]}  ({len(pages[m["key"]].body)//1024} KB, {len(m["attachments"])} attachments)')

    if not args.publish:
        return
    base, email, token = (os.environ.get(k) for k in ('CONFLUENCE_BASE', 'CONFLUENCE_EMAIL', 'CONFLUENCE_TOKEN'))
    if not (base and email and token and args.parent):
        sys.exit('publish needs CONFLUENCE_BASE, CONFLUENCE_EMAIL, CONFLUENCE_TOKEN and --parent / CONFLUENCE_PARENT_ID')
    cf = Confluence(base, email, token)
    space_id = cf.page(args.parent)['spaceId']
    ids = {}
    only = {x.strip() for x in args.only.split(',') if x.strip()}

    def wanted(key, title):
        if not only:
            return True
        if key in only or title in only:
            return True
        if 'wireframes' in only and key.startswith('3'):
            return True
        if 'decisions' in only and key.startswith('4'):
            return True
        return False

    for key in order:                      # parents come before children in order
        pg = pages[key]
        if not wanted(key, pg.title):
            continue
        if pg.parent_key and pg.parent_key not in ids:
            found = cf.find(space_id, pages[pg.parent_key].title)
            if not found:
                sys.exit(f'{pg.title}: parent "{pages[pg.parent_key].title}" is not published yet; publish it first')
            ids[pg.parent_key] = found['id']
        parent_id = ids[pg.parent_key] if pg.parent_key else args.parent
        pid, what = cf.upsert(space_id, parent_id, pg.title, pg.body)
        ids[key] = pid
        existing = cf.attachments(pid) if pg.attachments else {}
        for fname, path in pg.attachments:
            try:
                cf.attach(pid, fname, path, existing)
            except RuntimeError as e:
                print(f'  WARNING attachment {fname}: {e}')
        try:
            cf.set_full_width(pid)
        except RuntimeError as e:
            print(f'  WARNING full width: {e}')
        print(f'{what} {pg.title} -> {base}/wiki/spaces/TS/pages/{pid}')


if __name__ == '__main__':
    main()
