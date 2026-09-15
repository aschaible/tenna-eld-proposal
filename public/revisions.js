/*
 * Revision toggle. Shared by every page in the package.
 *
 * Five versions of this document set exist:
 *   v1  "Original"    - as presented for the 8/20/2026 product session
 *   v2  "8/28/2026"   - revised after the 8/17/2026 FMCSA compliance
 *                       review memo on host reporting; the snapshot sent
 *                       to Tenna on 8/28/2026
 *   v3  "9/2/2026"    - data ownership split and API surfaces, after the
 *                       8/28/2026 huddle settled P1, P2 and P5
 *   v4  "9/3/2026"    - mobile stack comparison rewritten as an open
 *                       two-option decision (native vs React Native), and
 *                       the 9/3/2026 Tom Cuthbertson session applied to the
 *                       wireframes
 *   v5  "9/8/2026"    - the 9/8/2026 Tom Cuthbertson call applied to the wireframes:
 *                       P3 settled, D35 required with a trigger rule, the
 *                       reason list, the no-signal roadside path, engine
 *                       hours and VIN sourcing, power-down handling
 *   v6  "9/10/2026"   - Adam takes product-requirements ownership; P3, Q17,
 *                       Q18, Q19, Q20, Q23, Q24 settled; Q1 restated with
 *                       the walk-off scenario; 9/3/2026, 9/8/2026 and 9/10/2026 sessions logged
 *   v7  "9/11/2026"   - design coverage check against the FMCSA test plan RTM:
 *                       three conflicts fixed, seven UI gaps drawn (D36, D37,
 *                       header indicators, D7/D9/D12/D16/D24/W15/W17/W10 edits)
 *   v8  "9/14/2026"   - the 9/14/2026 Tom Cuthbertson call applied: exempt-driver
 *                       flow (D38), trip details required, whole-month retention,
 *                       legal hold on W15, yard move ends at 20 mph, daily transfer
 *                       self-test, malfunction notice copy
 *
 * Content that differs between them is marked up in place, as a range
 * rather than as a single version, so a fourth revision costs one entry in
 * VERSIONS and nothing else:
 *
 *   data-rev-from="v2"    block-level  · visible in v2 and every later revision
 *   data-rev-until="v1"   block-level  · visible in v1 and earlier
 *   data-revi-from="v2"   inline       · same, for a phrase inside a sentence
 *   data-revi-until="v1"  inline
 *
 * A swap is a pair: the outgoing side carries -until="vN", the incoming side
 * -from="vN+1". An element with neither attribute is present in every version.
 * Content introduced in one revision and replaced in the next carries both.
 *
 * Only one side is ever visible, and whatever is new in the revision being
 * read is outlined so it can be found. The choice persists across pages via
 * localStorage and can be forced with ?v=original, ?v=8-28, ?v=9-2, ?v=9-3, ?v=9-8, ?v=9-10,
 * ?v=9-11 or ?v=9-14, so a link can open the package in a known state.
 */
(function () {
  'use strict';

  var KEY = 'tenna-eld-revision';

  var VERSIONS = [
    { id: 'v1', label: 'Original', sub: '8/20/2026 session', slug: 'original' },
    { id: 'v2', label: '8/28/2026', sub: 'host reporting', slug: '8-28' },
    { id: 'v3', label: '9/2/2026', sub: 'data ownership', slug: '9-2' },
    { id: 'v4', label: '9/3/2026', sub: 'stack · wireframes', slug: '9-3' },
    { id: 'v5', label: '9/8/2026', sub: 'Tom Cuthbertson call', slug: '9-8' },
    { id: 'v6', label: '9/10/2026', sub: 'product decisions', slug: '9-10' },
    { id: 'v7', label: '9/11/2026', sub: 'requirements check', slug: '9-11' },
    { id: 'v8', label: '9/14/2026', sub: 'Tom Cuthbertson call', slug: '9-14' }
  ];

  var DEFAULT = VERSIONS[VERSIONS.length - 1].id;

  function known(id) {
    for (var i = 0; i < VERSIONS.length; i++) if (VERSIONS[i].id === id) return true;
    return false;
  }

  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  function fromQuery() {
    var m = /[?&]v=([^&#]+)/.exec(window.location.search);
    if (!m) return null;
    var want = decodeURIComponent(m[1]).toLowerCase();
    for (var i = 0; i < VERSIONS.length; i++) {
      if (want === VERSIONS[i].id || want === VERSIONS[i].slug) return VERSIONS[i].id;
    }
    return null;
  }

  /* Hide anything not yet introduced in the version being read, and anything
     superseded before it. Generated from VERSIONS rather than written out as
     pair rules, which is what makes a new revision a one-line change. */
  function visibilityRules() {
    var out = [];
    VERSIONS.forEach(function (view, vi) {
      var sels = [];
      VERSIONS.forEach(function (other, oi) {
        var body = 'body[data-version="' + view.id + '"] ';
        if (oi > vi) {
          sels.push(body + '[data-rev-from="' + other.id + '"]');
          sels.push(body + '[data-revi-from="' + other.id + '"]');
        } else if (oi < vi) {
          sels.push(body + '[data-rev-until="' + other.id + '"]');
          sels.push(body + '[data-revi-until="' + other.id + '"]');
        }
      });
      if (sels.length) out.push(sels.join(',\n') + ' { display: none !important; }');
    });
    /* A card that turns settled in revision N carries data-settled-from="vN"
       and reads settled in N and every later revision, without duplicating
       the card. */
    VERSIONS.forEach(function (view, vi) {
      VERSIONS.forEach(function (other, oi) {
        if (oi <= vi) out.push('body[data-version="' + view.id + '"] .pcard[data-settled-from="' + other.id + '"] { border-left-color: var(--green, #2E8B57); }');
      });
    });
    /* The What changed section shows only the block for the revision on
       screen unless the reader asks for the earlier ones. */
    VERSIONS.forEach(function (view) {
      out.push('body[data-version="' + view.id + '"] #whats-changed .wc-body:not(.wc-all) > [data-rev-from]:not([data-rev-from="' + view.id + '"]) { display: none !important; }');
    });
    return out.join('\n');
  }

  /* Change marking, opt-in and on by default. Orange means new in the revision
     on screen; gray means this is the side about to be replaced. An element
     that is both (introduced in one revision, superseded in the next) reads as
     new, which is the more useful signal while that revision is the one open.

     A mark repaints what it marks, which is right for a phrase inside a
     sentence and wrong for a badge. A tag carries its own fill and its own pill
     shape, and repainting it makes two identical tags read as two different
     kinds of tag: an orange square and a blue pill both saying "Tenna API".
     Badges keep their own colours and take a ring instead. */
  var BADGE = ['.tag', '.chip', '.o-chip', '.src-chip', '.rev-badge', '.gchip', '.qref'];
  var NOT_BADGE = BADGE.map(function (c) { return ':not(' + c + ')'; }).join('');

  function markRules() {
    var out = [];
    VERSIONS.forEach(function (v) {
      var b = 'body.rev-marks[data-version="' + v.id + '"] ';
      function badges(attr, extra) {
        return BADGE.map(function (c) {
          return b + c + '[' + attr + '="' + v.id + '"]' + (extra || '');
        }).join(',\n');
      }
      var notFrom = ':not([data-rev-from="' + v.id + '"])';
      var notIFrom = ':not([data-revi-from="' + v.id + '"])';
      out.push(
        /* new in this revision, block level */
        b + '[data-rev-from="' + v.id + '"]' + NOT_BADGE + ' {',
        '  border-left: 3px solid #F37021;',
        '  padding-left: 14px;',
        '  background-image: linear-gradient(90deg, rgba(243,112,33,0.055), rgba(243,112,33,0) 340px);',
        '  border-radius: 0 8px 8px 0;',
        '}',
        /* new in this revision, inline */
        b + '[data-revi-from="' + v.id + '"]' + NOT_BADGE + ' {',
        '  background-color: rgba(243,112,33,0.13);',
        '  box-shadow: 0 0 0 2px rgba(243,112,33,0.13);',
        '  border-radius: 3px;',
        '}',
        /* new in this revision, badge: ring only, so the badge stays itself */
        badges('data-rev-from') + ',',
        badges('data-revi-from') + ' { box-shadow: 0 0 0 2px rgba(243,112,33,0.34); }',
        /* replaced after this revision */
        b + '[data-rev-until="' + v.id + '"]' + NOT_BADGE + notFrom + ',',
        b + '[data-revi-until="' + v.id + '"]' + NOT_BADGE + notIFrom + ' {',
        '  background-color: rgba(107,116,132,0.10); border-radius: 3px;',
        '}',
        badges('data-rev-until', notFrom) + ',',
        badges('data-revi-until', notIFrom) + ' { box-shadow: 0 0 0 2px rgba(107,116,132,0.24); }'
      );
    });
    return out.join('\n');
  }

  function injectStyles() {
    var css = [
      /* ---- version range visibility ---- */
      visibilityRules(),

      /* ---- change marking ---- */
      markRules(),

      /* ---- revision annotation block, used inside wireframe panels ---- */
      '.rev-what {',
      '  border: 1px solid #F8D3B7; background: #FFF8F3; border-radius: 10px;',
      '  padding: 12px 15px; font-size: 13px; color: #3D4654; line-height: 1.6;',
      '}',
      '.rev-what .rev-what-h {',
      '  display: block; font-size: 9.5px; font-weight: 800; letter-spacing: 1.4px;',
      '  text-transform: uppercase; color: #D9591A; margin-bottom: 7px;',
      '}',
      '.rev-what ul { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 5px; }',
      '.rev-what li { font-size: 13px; }',
      '.rev-what p { margin: 0 0 7px 0; font-size: 13px; color: #3D4654; }',
      '.rev-what p:last-child { margin-bottom: 0; }',

      /* ---- badges ---- */
      '.rev-badge {',
      '  display: inline-block; font-family: "JetBrains Mono", Menlo, monospace;',
      '  font-size: 9px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;',
      '  padding: 3px 8px; border-radius: 999px; white-space: nowrap; vertical-align: middle;',
      '  background: #F37021; color: #fff; border: 1px solid #D9591A;',
      '}',
      '.rev-badge.rev-changed { background: #FFF1E8; color: #D9591A; }',
      '.rev-badge.rev-orig { background: #EEF0F4; color: #4A5261; border-color: #D9DDE4; }',

      /* ---- the floating control ---- */
      /* Solid background on its own compositor layer. A backdrop blur here
         forces the browser to re-composite everything scrolling underneath
         the fixed bar, which reads as flicker on long pages; at 96% opacity
         the blur was invisible anyway. */
      '.revbar {',
      '  position: fixed; right: 18px; bottom: 18px; z-index: 900;',
      '  background: #1A1F2A; color: #fff;',
      '  border-radius: 14px; box-shadow: 0 12px 36px rgba(26,31,42,0.34);',
      '  padding: 10px 12px; font-family: inherit;',
      '  display: flex; flex-direction: column; gap: 8px; max-width: 384px;',
      '  transform: translateZ(0);',
      '}',
      '.revbar .rb-cap {',
      '  font-size: 8.5px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase;',
      '  color: rgba(255,255,255,0.45); display: flex; align-items: center; gap: 7px;',
      '}',
      '.revbar .rb-cap b { color: #F8A05F; letter-spacing: 1.2px; }',
      '.revbar .rb-opts { display: flex; gap: 6px; align-items: stretch; }',
      '.revbar select.rb-select {',
      '  flex: 1 1 auto; min-width: 0; cursor: pointer; font: inherit; font-size: 12px; font-weight: 700;',
      '  background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.18);',
      '  color: #fff; border-radius: 9px; padding: 7px 30px 7px 10px; line-height: 1.25;',
      '  -webkit-appearance: none; appearance: none;',
      '  background-image: url("data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2210%22 height=%226%22><path d=%22M0 0l5 6 5-6z%22 fill=%22%23F8A05F%22/></svg>");',
      '  background-repeat: no-repeat; background-position: right 10px center;',
      '}',
      '.revbar select.rb-select:hover { background-color: rgba(255,255,255,0.15); }',
      '.revbar select.rb-select option { color: #1A1F2A; background: #fff; }',
      '.revbar button.rb-step {',
      '  flex: 0 0 auto; cursor: pointer; font: inherit; font-size: 14px; font-weight: 800; line-height: 1;',
      '  background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.14);',
      '  color: rgba(255,255,255,0.72); border-radius: 9px; padding: 0 10px;',
      '}',
      '.revbar button.rb-step:hover:not(:disabled) { background: rgba(255,255,255,0.15); color: #fff; }',
      '.revbar button.rb-step:disabled { opacity: 0.3; cursor: default; }',
      '.revbar .rb-sub { font-size: 9.5px; font-weight: 600; color: rgba(255,255,255,0.48); }',
      '.revbar .rb-foot { display: flex; align-items: center; justify-content: flex-end; }',
      '.revbar a.rb-link { font-size: 10px; font-weight: 800; color: #F8A05F; white-space: nowrap; }',
      '.revbar a.rb-link:hover { color: #fff; }',
      '.revbar .rb-collapse {',
      '  position: absolute; top: 6px; right: 8px; cursor: pointer; background: none; border: 0;',
      '  color: rgba(255,255,255,0.35); font-size: 13px; line-height: 1; padding: 2px 4px;',
      '}',
      '.revbar .rb-collapse:hover { color: #fff; }',
      '.revbar.collapsed { padding: 8px 12px; }',
      '.revbar.collapsed .rb-opts, .revbar.collapsed .rb-sub, .revbar.collapsed .rb-foot, .revbar.collapsed .rb-collapse { display: none; }',
      '.revbar.collapsed .rb-cap { cursor: pointer; color: rgba(255,255,255,0.72); }',
      '@media (max-width: 700px) {',
      '  .revbar { right: 10px; left: 10px; bottom: 10px; max-width: none; }',
      '}',
      /* ---- What changed: collapsed by default ---- */
      '#whats-changed .wc-toggle {',
      '  display: inline-flex; align-items: center; gap: 9px; cursor: pointer; font: inherit;',
      '  background: #FFF8F3; border: 1px solid #F8D3B7; color: #D9591A; border-radius: 999px;',
      '  padding: 8px 16px 8px 14px; font-size: 12.5px; font-weight: 800; letter-spacing: 0.2px;',
      '}',
      '#whats-changed .wc-toggle:hover { background: #FFF1E8; }',
      '#whats-changed .wc-toggle .wc-caret { display: inline-block; transition: transform 0.15s; font-size: 11px; }',
      '#whats-changed .wc-toggle[aria-expanded="true"] .wc-caret { transform: rotate(90deg); }',
      '#whats-changed .wc-toggle .wc-count { font-weight: 600; color: #8A5A3C; }',
      '#whats-changed .wc-body { margin-top: 18px; }',
      '#whats-changed .wc-body[hidden] { display: none; }',
      '#whats-changed .wc-more {',
      '  display: inline-block; margin-top: 14px; font-size: 11.5px; font-weight: 700; color: #D9591A;',
      '  background: none; border: 0; padding: 0; cursor: pointer; font-family: inherit; text-decoration: underline;',
      '}',
      '#whats-changed .wc-more:hover { color: #1A1F2A; }',
      '@media print { .revbar { display: none; } }'
    ].join('\n');
    var style = document.createElement('style');
    style.setAttribute('data-revisions', '');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function build(current) {
    var bar = document.createElement('div');
    bar.className = 'revbar';
    bar.setAttribute('role', 'group');
    bar.setAttribute('aria-label', 'Document revision');

    var cap = document.createElement('div');
    cap.className = 'rb-cap';
    cap.innerHTML = 'Viewing revision <b></b>';
    bar.appendChild(cap);

    var opts = document.createElement('div');
    opts.className = 'rb-opts';
    function stepBtn(txt, dir, label) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'rb-step';
      b.setAttribute('data-dir', String(dir));
      b.setAttribute('aria-label', label);
      b.textContent = txt;
      b.addEventListener('click', function () {
        var i = indexOf(document.body.getAttribute('data-version')) + dir;
        if (i >= 0 && i < VERSIONS.length) apply(VERSIONS[i].id, true);
      });
      return b;
    }
    var sel = document.createElement('select');
    sel.className = 'rb-select';
    sel.setAttribute('aria-label', 'Choose a revision');
    VERSIONS.forEach(function (v) {
      var o = document.createElement('option');
      o.value = v.id;
      o.textContent = v.label + ' \u00b7 ' + v.sub;
      sel.appendChild(o);
    });
    sel.addEventListener('change', function () { apply(sel.value, true); });
    opts.appendChild(stepBtn('\u2039', -1, 'Earlier revision'));
    opts.appendChild(sel);
    opts.appendChild(stepBtn('\u203a', 1, 'Later revision'));
    bar.appendChild(opts);

    var sub = document.createElement('div');
    sub.className = 'rb-sub';
    bar.appendChild(sub);

    if (document.getElementById('whats-changed')) {
      var foot = document.createElement('div');
      foot.className = 'rb-foot';
      var link = document.createElement('a');
      link.className = 'rb-link';
      link.href = '#whats-changed';
      link.textContent = 'What changed →';
      foot.appendChild(link);
      bar.appendChild(foot);
    }

    var col = document.createElement('button');
    col.type = 'button';
    col.className = 'rb-collapse';
    col.setAttribute('aria-label', 'Collapse revision control');
    col.textContent = '−';
    col.addEventListener('click', function () { bar.classList.add('collapsed'); });
    bar.appendChild(col);
    cap.addEventListener('click', function () { bar.classList.remove('collapsed'); });

    return bar;
  }

  var barEl = null;

  /* A page whose <title> carries a revision date declares one spelling per
     version as <meta name="rev-title-vN" content="..."> so the tab label
     stays honest. A version with no meta keeps the title it was served with. */
  function applyTitle(id) {
    var m = document.querySelector('meta[name="rev-title-' + id + '"]');
    if (m && m.getAttribute('content')) document.title = m.getAttribute('content');
  }

  function apply(id, persist) {
    document.body.setAttribute('data-version', id);
    applyTitle(id);
    if (persist) store(KEY, id);
    var v = VERSIONS.filter(function (x) { return x.id === id; })[0];
    var i = indexOf(id);
    if (wcToggle && v) {
      var n = VERSIONS.length - 1;
      wcToggle.innerHTML = '<span class="wc-caret">\u25b6</span>What changed in revision ' + v.label +
        (i > 0 ? ' <span class="wc-count">\u00b7 ' + i + ' earlier revision' + (i === 1 ? '' : 's') + '</span>' : '');
    }
    if (!barEl) return;
    var sel = barEl.querySelector('.rb-select');
    if (sel) sel.value = id;
    var steps = barEl.querySelectorAll('.rb-step');
    for (var k = 0; k < steps.length; k++) {
      var dir = parseInt(steps[k].getAttribute('data-dir'), 10);
      steps[k].disabled = (i + dir < 0 || i + dir >= VERSIONS.length);
    }
    var b = barEl.querySelector('.rb-cap b');
    if (v && b) b.textContent = v.label;
    var sub = barEl.querySelector('.rb-sub');
    if (v && sub) sub.textContent = (i === VERSIONS.length - 1 ? 'Latest \u00b7 ' : 'Revision ' + (i + 1) + ' of ' + VERSIONS.length + ' \u00b7 ') + v.sub;
  }

  function indexOf(id) {
    for (var i = 0; i < VERSIONS.length; i++) if (VERSIONS[i].id === id) return i;
    return -1;
  }

  /* Collapse the What changed section behind one toggle. Expanded, it shows
     the block for the revision on screen; a link underneath reveals the
     earlier revisions' blocks too. Opening the page at #whats-changed, or
     following the control's link, expands it. */
  var wcToggle = null;
  function setupWhatsChanged() {
    var sec = document.getElementById('whats-changed');
    if (!sec) return;
    var container = sec.querySelector('.container') || sec;
    var body = document.createElement('div');
    body.className = 'wc-body';
    while (container.firstChild) body.appendChild(container.firstChild);
    wcToggle = document.createElement('button');
    wcToggle.type = 'button';
    wcToggle.className = 'wc-toggle';
    wcToggle.setAttribute('aria-expanded', 'false');
    wcToggle.setAttribute('aria-controls', 'wc-body');
    body.id = 'wc-body';
    var more = document.createElement('button');
    more.type = 'button';
    more.className = 'wc-more';
    more.textContent = 'Show what changed in earlier revisions';
    more.addEventListener('click', function () {
      var all = body.classList.toggle('wc-all');
      more.textContent = all ? 'Show only this revision' : 'Show what changed in earlier revisions';
    });
    body.appendChild(more);
    function setOpen(open) {
      wcToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      body.hidden = !open;
    }
    wcToggle.addEventListener('click', function () { setOpen(body.hidden); });
    container.appendChild(wcToggle);
    container.appendChild(body);
    setOpen(window.location.hash === '#whats-changed');
    window.addEventListener('hashchange', function () { if (window.location.hash === '#whats-changed') setOpen(true); });
    document.addEventListener('click', function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[href$="#whats-changed"]') : null;
      if (a) setOpen(true);
    });
  }

  function init() {
    injectStyles();
    var current = fromQuery() || read(KEY) || DEFAULT;
    if (!known(current)) current = DEFAULT;
    document.body.classList.add('rev-marks');
    setupWhatsChanged();
    barEl = build(current);
    document.body.appendChild(barEl);
    apply(current, false);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
