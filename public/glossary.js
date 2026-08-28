/*
 * Glossary: hover definitions for acronyms and industry jargon.
 * Scans rendered text, wraps known terms, and shows a tooltip on
 * hover, keyboard focus, or tap. Shared by index.html and ecosystem.html.
 */
(function () {
  'use strict';

  /* Each entry: regex source (word-boundaried at runtime), short title, definition.
     Optional `max` caps how many times a term is annotated per page. Common English
     words used as jargon ("host") would otherwise dot half the page; the first
     couple of occurrences carry the definition and the rest read normally. */
  var TERMS = [
    /* Regulatory and compliance */
    { re: 'HOS', title: 'HOS: Hours of Service', def: 'The federal limits on how long a commercial driver may drive and work: 11 hours driving, a 14-hour on-duty window, a required 30-minute break, and a 60/70-hour weekly cycle. Recording HOS accurately is the core job of an ELD.' },
    { re: 'FMCSA', title: 'FMCSA: Federal Motor Carrier Safety Administration', def: 'The US DOT agency that regulates trucking. It maintains the public registry of self-certified ELDs and can revoke a device that fails the technical spec, instantly stranding every fleet that uses it. Staying on that registry is the long-term compliance work in this proposal.' },
    { re: 'CFR', title: 'CFR: Code of Federal Regulations', def: 'The codified body of US federal rules. 49 CFR Part 395 defines Hours of Service and ELD requirements; its Appendix A is the detailed technical specification a device must implement to be listed.' },
    { re: 'Appendix A', title: 'Appendix A (of 49 CFR Part 395)', def: 'The technical specification section of the federal ELD rule. It defines every required event, data element, malfunction threshold, and the exact output file format. It is effectively the requirements document for this build.' },
    { re: 'eRODS', title: 'eRODS: Electronic Records of Duty Status', def: 'FMCSA’s own software that receives and displays a driver’s logs during an inspection or audit. At roadside, the ELD transfers its output file to eRODS via a web service or email; a failed transfer can mean an immediate out-of-service order.' },
    { re: 'DVIRs?', title: 'DVIR: Driver Vehicle Inspection Report', def: 'A federally required pre-trip and post-trip vehicle inspection with defect tracking. It is a separate regulation from the ELD rule but conventionally lives in the same driver app. Tenna already ships a DVIR module, which the new ELD app would surface rather than rebuild.' },
    { re: 'IFTA', title: 'IFTA: International Fuel Tax Agreement', def: 'A pact among US states and Canadian provinces that lets interstate carriers file one consolidated fuel tax return based on miles driven in each jurisdiction. Tenna’s existing IFTA module consumes the same mileage data the trackers and ELD feed would supply.' },
    { re: 'UDRs?|UD Records|UDS', title: 'UDR / UDS: Unidentified Driving Record', def: 'Driving captured while no driver was logged in. The rule requires these records to be surfaced so a driver can claim them, and requires the motor carrier to review each one and either annotate it with a reason or assign it to the right driver, keeping the records six months. The in-vehicle device holds only the last 8 days of unaccepted records; the full backlog is worked on the host. More than 30 minutes of unassigned driving in 24 hours triggers a diagnostic flag.' },
    { re: '[Hh]ost', max: 2, title: 'Host: the carrier\u2019s back-end system', def: 'In ELD terminology, an ELD has two halves. The in-vehicle ELD is the recorder in the truck: here, the driver\u2019s phone plus the Geometris tracker, which holds a short working window and shows the record at roadside. The host is the motor carrier\u2019s back-end system: the server holding the full six-month record, and the web surfaces over it. \u201cHost reporting\u201d means the reports a carrier runs against that server, which is where unidentified-driving review and audit production legally belong.' },
    { re: '[Pp]eer.to.peer transfers?|[Ll]ocal ELD type', title: 'Peer-to-peer (Local) transfer', def: 'One of the two mutually exclusive ways an ELD can hand its output file to an inspector: USB 2.0 or Bluetooth directly to the officer\u2019s device. A provider certifies for this family or for Telematics (web services and email), never both. This build elects Telematics.' },
    { re: '[Tt]elematics ELD(?: type)?', title: 'Telematics ELD type', def: 'The transfer family this build certifies for: the output file goes to FMCSA by HTTPS web service, with email as the fallback. It is the mode Motive, Samsara, and Omnitracs all use. Electing it excludes the peer-to-peer USB and Bluetooth routes, and the election is made at certification rather than at runtime.' },
    { re: '[Pp]ersonal [Cc]onveyance|PC', title: 'Personal Conveyance (PC)', def: 'An off-duty driving mode for using the truck personally, such as commuting home from a job site. Miles driven under Personal Conveyance do not count against HOS clocks. Misuse is an enforcement focus, so it requires carrier authorization and a written annotation.' },
    { re: '[Yy]ard [Mm]oves?|YM', title: 'Yard Move (YM)', def: 'An on-duty driving mode for repositioning a vehicle inside a yard or jobsite at low speed without consuming the 11-hour drive clock. Because Tenna already maps yards and sites as geofences, the app can suggest Yard Move automatically, something generic ELDs cannot do.' },
    { re: 'OFF', title: 'OFF: Off Duty', def: 'One of the four federal duty statuses. The driver is relieved of all work and responsibility, and the time counts against no HOS clock. Driving while off duty is only legal under the Personal Conveyance mode.' },
    { re: '[Ss]leeper [Bb]erth|SB', title: 'SB: Sleeper Berth', def: 'One of the four federal duty statuses. Time resting in a sleeper berth pauses parts of the HOS clocks under specific split-rest rules (8/2 or 7/3 splits). Rare in construction fleets, but every ELD must support it.' },
    { re: 'D', title: 'D: Driving', def: 'One of the four federal duty statuses. The driver is at the controls of a moving commercial vehicle. The ELD sets this status automatically above 5 mph, and it consumes the 11-hour daily drive limit.' },
    { re: 'ON', title: 'ON: On Duty Not Driving', def: 'One of the four federal duty statuses. The driver is working but not driving: loading, inspections, paperwork, jobsite work. It consumes the 14-hour daily window and the 60/70-hour weekly cycle, but not the drive clock.' },
    { re: 'Out-of-Service', title: 'Out-of-Service order', def: 'An enforcement order that immediately sidelines a driver or vehicle until a problem is fixed. A failed log transfer at roadside can trigger one, which is why inspection mode is the highest-stakes feature in the app.' },

    /* Vehicle and hardware data */
    { re: 'VBUS', title: 'VBUS: Vehicle Bus', def: 'A general term for a vehicle’s internal data connection (CAN, J1939, OBD-II). “ECM/VBUS data” means engine data read off this connection rather than inferred from GPS, which the ELD rule requires.' },

    /* Software and engineering */
    { re: 'SOC 2(?: Type 1)?', title: 'SOC 2: System and Organization Controls', def: 'An independent audit of a software company’s security practices. Type 1 verifies the controls exist at a point in time. It is a common enterprise buying checkbox, and Tenna holds it.' },
    { re: 'CMMS', title: 'CMMS: Computerized Maintenance Management System', def: 'Software for managing preventive maintenance, work orders, parts inventory, and mechanic time. Tenna’s Maintenance module is a CMMS built into the same platform as tracking, so shop work links directly to asset records.' },
    { re: 'AEMP', title: 'AEMP: Association of Equipment Management Professionals', def: 'The industry group behind the AEMP/ISO 15143-3 telematics standard, a shared data format that lets one platform pull location and engine data from many different OEM systems.' },
    { re: 'NTP', title: 'NTP: Network Time Protocol', def: 'The standard internet mechanism for keeping a device’s clock accurate. The ELD anchors its clock to NTP, with GPS time as a fallback, to satisfy the 10-minute UTC drift rule.' },
    { re: 'CRC', title: 'CRC: Cyclic Redundancy Check', def: 'A checksum that proves a file was not corrupted or altered. The FMCSA output file ends with a CRC line, and getting it wrong is a known certification failure.' },
    { re: 'ASCII', title: 'ASCII: plain-text encoding', def: 'A basic plain-text character format. The FMCSA ELD output file must be a rigidly formatted ASCII text file with exact section ordering, which eRODS parses during inspections and audits.' },
    { re: '[Ii]dempotent', title: 'Idempotent', def: 'Safe to process more than once. If a flaky connection re-sends the same event, an idempotent ingestion API stores it exactly once. Essential for an ELD because drivers sync hours of queued events after working offline.' },
    { re: '[Ss]tate machine', title: 'State machine', def: 'A software pattern where a system is always in exactly one defined state with strict rules for transitions. The HOS engine is a state machine over duty statuses, which makes the complex federal rules testable and auditable.' },

    /* Industry and market */
    { re: '[Cc]ost cod(?:es|e|ing)', title: 'Cost code', def: 'The construction accounting label that ties labor, equipment, and materials to a specific budget line on a job. Tagging tracker hours and mechanic time with cost codes is how Tenna data lands cleanly in the contractor’s ERP.' }
  ];

  /* Containers where annotation would hurt the design or duplicate links. */
  var SKIP_SELECTOR = 'a, h1, h2, script, style, .nav, .kicker, .eyebrow, .nav-pill, .field-guide, .brand-row, .ico, .module-tag, .hw-class, .layer-label, .arch-flow, .gloss, .gloss-tip';

  var combined = new RegExp(TERMS.map(function (t) { return '\\b(?:' + t.re + ')\\b'; }).join('|'), 'g');
  var matchers = TERMS.map(function (t) { return { rx: new RegExp('^(?:' + t.re + ')$'), t: t }; });
  var used = {};

  function lookup(text) {
    for (var i = 0; i < matchers.length; i++) {
      if (matchers[i].rx.test(text)) return matchers[i].t;
    }
    return null;
  }

  var annotating = false;

  function annotate(root) {
    annotating = true;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue || node.nodeValue.length < 2) return NodeFilter.FILTER_REJECT;
        var p = node.parentElement;
        if (!p || p.closest(SKIP_SELECTOR)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function (node) {
      var text = node.nodeValue;
      combined.lastIndex = 0;
      if (!combined.test(text)) return;
      combined.lastIndex = 0;

      var frag = document.createDocumentFragment();
      var last = 0;
      var m;
      while ((m = combined.exec(text)) !== null) {
        var term = lookup(m[0]);
        if (!term) continue;
        if (term.max) {
          var seen = used[term.re] || 0;
          if (seen >= term.max) continue;
          used[term.re] = seen + 1;
        }
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var span = document.createElement('span');
        span.className = 'gloss';
        span.textContent = m[0];
        span.setAttribute('tabindex', '0');
        span.setAttribute('data-gloss-title', term.title);
        span.setAttribute('data-gloss-def', term.def);
        frag.appendChild(span);
        last = m.index + m[0].length;
      }
      if (last === 0) return;
      if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });
    annotating = false;
  }

  /* Tooltip */
  var tip = null;
  var activeSpan = null;

  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement('div');
    tip.className = 'gloss-tip';
    tip.setAttribute('role', 'tooltip');
    document.body.appendChild(tip);
    return tip;
  }

  function show(span) {
    var t = ensureTip();
    activeSpan = span;
    t.innerHTML = '';
    var h = document.createElement('div');
    h.className = 'gloss-tip-title';
    h.textContent = span.getAttribute('data-gloss-title');
    var d = document.createElement('div');
    d.className = 'gloss-tip-def';
    d.textContent = span.getAttribute('data-gloss-def');
    t.appendChild(h);
    t.appendChild(d);
    t.classList.add('visible');

    var rect = span.getBoundingClientRect();
    var tw = Math.min(360, window.innerWidth - 24);
    t.style.maxWidth = tw + 'px';
    var th = t.offsetHeight;
    var w = t.offsetWidth;
    var left = rect.left + rect.width / 2 - w / 2;
    left = Math.max(12, Math.min(left, window.innerWidth - w - 12));
    var top = rect.top - th - 10;
    if (top < 12) top = rect.bottom + 10;
    t.style.left = left + 'px';
    t.style.top = top + 'px';
  }

  function hide() {
    activeSpan = null;
    if (tip) tip.classList.remove('visible');
  }

  function bindEvents() {
    document.addEventListener('mouseover', function (e) {
      var span = e.target.closest && e.target.closest('.gloss');
      if (span) show(span);
    });
    document.addEventListener('mouseout', function (e) {
      var span = e.target.closest && e.target.closest('.gloss');
      if (span && span === activeSpan) hide();
    });
    document.addEventListener('focusin', function (e) {
      var span = e.target.closest && e.target.closest('.gloss');
      if (span) show(span);
    });
    document.addEventListener('focusout', hide);
    /* Tap toggle for touch devices. */
    document.addEventListener('click', function (e) {
      var span = e.target.closest && e.target.closest('.gloss');
      if (span) {
        if (activeSpan === span && tip && tip.classList.contains('visible')) hide();
        else show(span);
      } else if (!(e.target.closest && e.target.closest('.gloss-tip'))) {
        hide();
      }
    });
    window.addEventListener('scroll', hide, { passive: true });
    window.addEventListener('resize', hide);
  }

  function injectStyles() {
    var css = '' +
      '.gloss { border-bottom: 1px dotted rgba(243,112,33,0.65); cursor: help; }' +
      '.gloss:hover, .gloss:focus { border-bottom-color: #F37021; outline: none; background: rgba(243,112,33,0.07); border-radius: 2px; }' +
      '.gloss-tip { position: fixed; z-index: 1000; background: #1A1F2A; color: rgba(255,255,255,0.92); ' +
      '  padding: 13px 15px; border-radius: 10px; box-shadow: 0 14px 40px rgba(26,31,42,0.35); ' +
      '  font-size: 13px; line-height: 1.55; opacity: 0; visibility: hidden; transition: opacity 0.12s; ' +
      '  pointer-events: none; font-family: inherit; text-align: left; font-weight: 400; font-style: normal; ' +
      '  letter-spacing: 0; text-transform: none; white-space: normal; }' +
      '.gloss-tip.visible { opacity: 1; visibility: visible; }' +
      '.gloss-tip-title { color: #F8A05F; font-weight: 700; font-size: 12px; letter-spacing: 0.4px; margin-bottom: 5px; }' +
      '.gloss-tip-def { font-weight: 400; }';
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function init() {
    injectStyles();
    annotate(document.body);
    bindEvents();
    /* Annotate content injected later (e.g. requirement detail modals). */
    var observer = new MutationObserver(function (mutations) {
      if (annotating) return;
      mutations.forEach(function (mu) {
        for (var i = 0; i < mu.addedNodes.length; i++) {
          var n = mu.addedNodes[i];
          if (n.nodeType === 1 && !n.closest('.gloss-tip') && !n.classList.contains('gloss')) {
            annotate(n);
          }
        }
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
