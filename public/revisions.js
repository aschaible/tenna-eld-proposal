/*
 * Revision toggle. Shared by every page in the package.
 *
 * Four versions of this document set exist:
 *   v1  "Original"    - as presented for the August 20 product session
 *   v2  "8/28/2026"   - revised after the August 17 FMCSA compliance
 *                       review memo on host reporting; the snapshot sent
 *                       to Tenna on 28 August
 *   v3  "9/2/2026"    - data ownership split and API surfaces, after the
 *                       28 August huddle settled P1, P2 and P5
 *   v4  "9/3/2026"    - mobile stack comparison rewritten as an open
 *                       two-option decision (native vs React Native), and
 *                       the 9/3 FMCSA consultant session applied to the
 *                       wireframes
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
 * localStorage and can be forced with ?v=original, ?v=8-28, ?v=9-2 or
 * ?v=9-3, so a link can open the package in a known state.
 */
(function () {
  'use strict';

  var KEY = 'tenna-eld-revision';

  var VERSIONS = [
    { id: 'v1', label: 'Original', sub: 'Aug 20 session', slug: 'original' },
    { id: 'v2', label: '8/28/2026', sub: 'host reporting', slug: '8-28' },
    { id: 'v3', label: '9/2/2026', sub: 'data ownership', slug: '9-2' },
    { id: 'v4', label: '9/3/2026', sub: 'stack · wireframes', slug: '9-3' }
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
      '.revbar {',
      '  position: fixed; right: 18px; bottom: 18px; z-index: 900;',
      '  background: rgba(26,31,42,0.96); color: #fff;',
      '  border-radius: 14px; box-shadow: 0 12px 36px rgba(26,31,42,0.34);',
      '  padding: 10px 12px; font-family: inherit;',
      '  display: flex; flex-direction: column; gap: 8px; max-width: 384px;',
      '  backdrop-filter: blur(8px);',
      '}',
      '.revbar .rb-cap {',
      '  font-size: 8.5px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase;',
      '  color: rgba(255,255,255,0.45); display: flex; align-items: center; gap: 7px;',
      '}',
      '.revbar .rb-cap b { color: #F8A05F; letter-spacing: 1.2px; }',
      '.revbar .rb-opts { display: flex; gap: 6px; }',
      '.revbar button.rb-opt {',
      '  flex: 1 1 0; min-width: 0; text-align: left; cursor: pointer; font: inherit;',
      '  background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.14);',
      '  color: rgba(255,255,255,0.72); border-radius: 9px; padding: 6px 10px;',
      '  line-height: 1.25; transition: background 0.12s, border-color 0.12s;',
      '}',
      '.revbar button.rb-opt:hover { background: rgba(255,255,255,0.13); }',
      '.revbar button.rb-opt .l { display: block; font-size: 11.5px; font-weight: 800; letter-spacing: -0.1px; }',
      '.revbar button.rb-opt .s { display: block; font-size: 8.5px; font-weight: 600; color: rgba(255,255,255,0.42); margin-top: 1px; }',
      '.revbar button.rb-opt[aria-pressed="true"] {',
      '  background: #F37021; border-color: #F37021; color: #fff;',
      '}',
      '.revbar button.rb-opt[aria-pressed="true"] .s { color: rgba(255,255,255,0.78); }',
      '.revbar .rb-foot { display: flex; align-items: center; justify-content: flex-end; }',
      '.revbar a.rb-link { font-size: 10px; font-weight: 800; color: #F8A05F; white-space: nowrap; }',
      '.revbar a.rb-link:hover { color: #fff; }',
      '.revbar .rb-collapse {',
      '  position: absolute; top: 6px; right: 8px; cursor: pointer; background: none; border: 0;',
      '  color: rgba(255,255,255,0.35); font-size: 13px; line-height: 1; padding: 2px 4px;',
      '}',
      '.revbar .rb-collapse:hover { color: #fff; }',
      '.revbar.collapsed { padding: 8px 12px; }',
      '.revbar.collapsed .rb-opts, .revbar.collapsed .rb-foot, .revbar.collapsed .rb-collapse { display: none; }',
      '.revbar.collapsed .rb-cap { cursor: pointer; color: rgba(255,255,255,0.72); }',
      '@media (max-width: 700px) {',
      '  .revbar { right: 10px; left: 10px; bottom: 10px; max-width: none; }',
      '}',
      /* the version buttons stop fitting side by side on narrow phones */
      '@media (max-width: 500px) {',
      '  .revbar .rb-opts { flex-direction: column; }',
      '}',
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
    VERSIONS.forEach(function (v) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'rb-opt';
      b.setAttribute('data-v', v.id);
      b.innerHTML = '<span class="l">' + v.label + '</span><span class="s">' + v.sub + '</span>';
      b.addEventListener('click', function () { apply(v.id, true); });
      opts.appendChild(b);
    });
    bar.appendChild(opts);

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
    if (!barEl) return;
    var buttons = barEl.querySelectorAll('.rb-opt');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute('aria-pressed', buttons[i].getAttribute('data-v') === id ? 'true' : 'false');
    }
    var v = VERSIONS.filter(function (x) { return x.id === id; })[0];
    var b = barEl.querySelector('.rb-cap b');
    if (v && b) b.textContent = v.label;
  }

  function init() {
    injectStyles();
    var current = fromQuery() || read(KEY) || DEFAULT;
    if (!known(current)) current = DEFAULT;
    document.body.classList.add('rev-marks');
    barEl = build(current);
    document.body.appendChild(barEl);
    apply(current, false);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
