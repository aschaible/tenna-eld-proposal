/*
 * Revision toggle. Shared by every page in the package.
 *
 * Two versions of this document set exist:
 *   v1  "Original"    - as presented for the August 20 product session
 *   v2  "8/28/2026"   - revised after the August 17 FMCSA compliance
 *                       review memo on host reporting
 *
 * Content that differs between them is marked up in place:
 *   data-rev="v1"  / data-rev="v2"    block-level swap
 *   data-revi="v1" / data-revi="v2"   inline swap (a phrase inside a sentence)
 *
 * Only one side is ever visible, and in the revised version every edit is
 * outlined so it can be found. The choice persists across pages via
 * localStorage and can be forced with ?v=original or ?v=8-28, so a link
 * can open the package in a known state.
 */
(function () {
  'use strict';

  var KEY = 'tenna-eld-revision';
  var DEFAULT = 'v2';

  var VERSIONS = [
    { id: 'v1', label: 'Original', sub: 'Aug 20 session', slug: 'original' },
    { id: 'v2', label: '8/28/2026', sub: 'host reporting review', slug: '8-28' }
  ];

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

  function injectStyles() {
    var css = [
      /* ---- version swap ---- */
      'body[data-version="v1"] [data-rev="v2"],',
      'body[data-version="v1"] [data-revi="v2"],',
      'body[data-version="v2"] [data-rev="v1"],',
      'body[data-version="v2"] [data-revi="v1"] { display: none !important; }',

      /* ---- change marking (opt-in, on by default in v2) ---- */
      'body.rev-marks[data-version="v2"] [data-rev="v2"] {',
      '  border-left: 3px solid #F37021;',
      '  padding-left: 14px;',
      '  background: linear-gradient(90deg, rgba(243,112,33,0.055), rgba(243,112,33,0) 340px);',
      '  border-radius: 0 8px 8px 0;',
      '}',
      'body.rev-marks[data-version="v2"] [data-revi="v2"] {',
      '  background: rgba(243,112,33,0.13);',
      '  box-shadow: 0 0 0 2px rgba(243,112,33,0.13);',
      '  border-radius: 3px;',
      '}',
      'body.rev-marks[data-version="v1"] [data-rev="v1"],',
      'body.rev-marks[data-version="v1"] [data-revi="v1"] {',
      '  background: rgba(107,116,132,0.10); border-radius: 3px;',
      '}',

      /* ---- "changed on 8/28" annotation block, used inside wireframe panels ---- */
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
      '  display: flex; flex-direction: column; gap: 8px; max-width: 320px;',
      '  backdrop-filter: blur(8px);',
      '}',
      '.revbar .rb-cap {',
      '  font-size: 8.5px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase;',
      '  color: rgba(255,255,255,0.45); display: flex; align-items: center; gap: 7px;',
      '}',
      '.revbar .rb-cap b { color: #F8A05F; letter-spacing: 1.2px; }',
      '.revbar .rb-opts { display: flex; gap: 6px; }',
      '.revbar button.rb-opt {',
      '  flex: 1; text-align: left; cursor: pointer; font: inherit;',
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

  /* A page whose <title> carries a revision date declares both spellings as
     <meta name="rev-title-v1|v2" content="..."> so the tab label stays honest. */
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
    if (current !== 'v1' && current !== 'v2') current = DEFAULT;
    document.body.classList.add('rev-marks');
    barEl = build(current);
    document.body.appendChild(barEl);
    apply(current, false);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
