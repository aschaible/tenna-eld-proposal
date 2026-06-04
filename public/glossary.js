/*
 * Glossary: hover definitions for acronyms and industry jargon.
 * Scans rendered text, wraps known terms, and shows a tooltip on
 * hover, keyboard focus, or tap. Shared by index.html and ecosystem.html.
 */
(function () {
  'use strict';

  /* Each entry: regex source (word-boundaried at runtime), short title, definition. */
  var TERMS = [
    /* Regulatory and compliance */
    { re: 'ELDs?', title: 'ELD: Electronic Logging Device', def: 'A federally required device, in practice a phone or tablet app paired with engine-connected hardware, that automatically records a commercial driver’s Hours of Service so logs can’t be falsified. Tenna currently resells a partner’s ELD under its own brand; this proposal covers building a Tenna-owned ELD as a standalone product integrated with the platform.' },
    { re: 'HOS', title: 'HOS: Hours of Service', def: 'The federal limits on how long a commercial driver may drive and work: 11 hours driving, a 14-hour on-duty window, a required 30-minute break, and a 60/70-hour weekly cycle. Recording HOS accurately is the core job of an ELD.' },
    { re: 'FMCSA', title: 'FMCSA: Federal Motor Carrier Safety Administration', def: 'The US DOT agency that regulates trucking. It maintains the public registry of self-certified ELDs and can revoke a device that fails the technical spec, instantly stranding every fleet that uses it. Staying on that registry is the long-term compliance work in this proposal.' },
    { re: 'DOT', title: 'DOT: Department of Transportation', def: 'The US federal transportation department and parent of FMCSA. A DOT officer is the roadside inspector who can demand a driver’s logs on the spot; failing that handoff can put a truck out of service immediately.' },
    { re: 'CFR', title: 'CFR: Code of Federal Regulations', def: 'The codified body of US federal rules. 49 CFR Part 395 defines Hours of Service and ELD requirements; its Appendix A is the detailed technical specification a device must implement to be listed.' },
    { re: 'Appendix A', title: 'Appendix A (of 49 CFR Part 395)', def: 'The technical specification section of the federal ELD rule. It defines every required event, data element, malfunction threshold, and the exact output file format. It is effectively the requirements document for this build.' },
    { re: 'eRODS', title: 'eRODS: Electronic Records of Duty Status', def: 'FMCSA’s own software that receives and displays a driver’s logs during an inspection or audit. At roadside, the ELD transfers its output file to eRODS via a web service or email; a failed transfer can mean an immediate out-of-service order.' },
    { re: 'DVIRs?', title: 'DVIR: Driver Vehicle Inspection Report', def: 'A federally required pre-trip and post-trip vehicle inspection with defect tracking. It is a separate regulation from the ELD rule but conventionally lives in the same driver app. Tenna already ships a DVIR module, which the new ELD app would surface rather than rebuild.' },
    { re: 'IFTA', title: 'IFTA: International Fuel Tax Agreement', def: 'A pact among US states and Canadian provinces that lets interstate carriers file one consolidated fuel tax return based on miles driven in each jurisdiction. Tenna’s existing IFTA module consumes the same mileage data the trackers and ELD feed would supply.' },
    { re: 'CDL', title: 'CDL: Commercial Driver’s License', def: 'The license class required to operate heavy commercial vehicles. Driver profiles in Tenna carry CDL information, and every ELD log entry is tied to a specific licensed driver.' },
    { re: 'CMVs?', title: 'CMV: Commercial Motor Vehicle', def: 'The regulatory term for trucks and other vehicles covered by federal trucking rules, generally over 10,001 pounds or carrying regulated cargo. The ELD mandate applies to drivers of CMVs who must keep duty logs.' },
    { re: 'UDRs?', title: 'UDR: Unidentified Driving Record', def: 'Driving captured while no driver was logged in. The rule requires these records to be surfaced so a driver can claim them or the carrier can investigate. More than 30 minutes of unassigned driving in 24 hours triggers a diagnostic flag.' },
    { re: 'UD Records', title: 'UD: Unidentified Driving records', def: 'Driving events captured while no driver was logged into the ELD. Drivers must be able to claim or reject each record, and unresolved accumulation triggers a compliance flag.' },
    { re: '[Pp]ersonal [Cc]onveyance', title: 'Personal Conveyance (PC)', def: 'An off-duty driving mode for using the truck personally, such as commuting home from a job site. Miles driven under Personal Conveyance do not count against HOS clocks. Misuse is an enforcement focus, so it requires carrier authorization and a written annotation.' },
    { re: 'PC', title: 'PC: Personal Conveyance', def: 'The off-duty driving mode for personal use of the truck, such as commuting from a job site. Exempt from HOS clocks, carrier-authorized, and annotation-required because it is an enforcement focus.' },
    { re: '[Yy]ard [Mm]oves?', title: 'Yard Move (YM)', def: 'An on-duty driving mode for repositioning a vehicle inside a yard or jobsite at low speed without consuming the 11-hour drive clock. Because Tenna already maps yards and sites as geofences, the app can suggest Yard Move automatically, something generic ELDs cannot do.' },
    { re: 'YM', title: 'YM: Yard Move', def: 'The on-duty driving mode for low-speed moves inside a yard or jobsite that are exempt from the driving clock. Tenna’s geofences let the app detect and suggest it automatically.' },
    { re: '[Ss]leeper [Bb]erth', title: 'Sleeper Berth (SB)', def: 'One of the four federal duty statuses (Off Duty, Sleeper Berth, Driving, On Duty). Time logged in a sleeper berth pauses parts of the HOS clock under specific split-rest rules.' },
    { re: 'Out-of-Service', title: 'Out-of-Service order', def: 'An enforcement order that immediately sidelines a driver or vehicle until a problem is fixed. A failed log transfer at roadside can trigger one, which is why inspection mode is the highest-stakes feature in the app.' },
    { re: '[Ss]elf-cert(?:ification|ifies|ified|ify)', title: 'Self-certification', def: 'FMCSA does not test ELDs before listing them. The manufacturer attests its device meets the spec, files a web form, and is listed within days. The catch: FMCSA audits later and revokes devices that fall short, so the real bar is engineering rigor, not the paperwork.' },

    /* Vehicle and hardware data */
    { re: 'ECM', title: 'ECM: Engine Control Module', def: 'The vehicle’s onboard engine computer. The ELD rule requires reading speed, odometer, engine hours, and power status directly from the ECM rather than inferring them from GPS, which is why the ELD app must pair with TennaFLEET hardware plugged into the truck.' },
    { re: 'ECUs?', title: 'ECU: Electronic Control Unit', def: 'The equipment-world equivalent of a truck’s engine computer. TennaCANbus trackers read engine hours and fault codes from a machine’s ECU so maintenance can be triggered by actual usage.' },
    { re: 'CAN-bus', title: 'CAN-bus: Controller Area Network', def: 'The standard wiring network that lets a vehicle’s computers talk to each other. Tapping the CAN-bus is how trackers pull engine hours, speed, and fault data straight from the machine instead of estimating it.' },
    { re: 'VBUS', title: 'VBUS: Vehicle Bus', def: 'A general term for a vehicle’s internal data connection (CAN, J1939, OBD-II). “ECM/VBUS data” means engine data read off this connection rather than inferred from GPS, which the ELD rule requires.' },
    { re: 'DTCs?', title: 'DTC: Diagnostic Trouble Code', def: 'A standardized fault code the engine computer emits when something is wrong. In Tenna, DTCs flow from trackers into the Maintenance module and become work orders automatically.' },
    { re: 'VINs?', title: 'VIN: Vehicle Identification Number', def: 'The unique 17-character serial number of a vehicle. The ELD reads the VIN from the engine and matches it to Tenna’s asset record to know exactly which truck a driver paired with.' },
    { re: 'GPS', title: 'GPS: Global Positioning System', def: 'Satellite positioning. The ELD rule requires location at each duty-status change to within about one mile, and Tenna’s trackers use GPS to power the live Master Map.' },
    { re: 'BLE', title: 'BLE: Bluetooth Low Energy', def: 'A short-range, battery-friendly radio standard. TennaBLE beacons use it to track unpowered assets like tools, attachments, and trench boxes that a GPS tracker would be overkill for.' },
    { re: 'PTO', title: 'PTO: Power Take-Off', def: 'A mechanism that diverts engine power to run attachments such as dump beds or compressors. PTO status is a utilization signal: the engine may be running because the machine is actually working, not idling.' },
    { re: 'QR', title: 'QR: Quick Response code', def: 'A scannable square barcode. TennaQR tags put one on small assets and consumables so a field worker can scan with the Tenna app to log location, condition, and requests.' },
    { re: '[Tt]elematics', title: 'Telematics', def: 'Remote transmission of vehicle data: GPS position plus engine signals like speed, hours, and fault codes. It is the umbrella term for what all Tenna trackers do. In ELD jargon, “telematics transfer” also names the electronic method of sending logs to FMCSA at roadside.' },
    { re: '[Gg]eofenc(?:es|e|ed|ing)', title: 'Geofence', def: 'A virtual boundary drawn on a map around a yard, project, or zone. Tenna fires events when assets enter or leave geofences, which powers job costing, alerts, and automatic Yard Move suggestions in the ELD.' },

    /* Software and engineering */
    { re: 'APIs?', title: 'API: Application Programming Interface', def: 'The defined way one system reads or writes another system’s data. The ELD integrates with Tenna through Asset, User, and telemetry APIs rather than sharing a database, which is what lets it stay a separate product while feeling native.' },
    { re: 'SSO', title: 'SSO: Single Sign-On', def: 'Logging into multiple applications with one identity. The proposed ELD authenticates against Tenna’s identity system, so drivers and managers use their existing Tenna login rather than a new account.' },
    { re: 'SaaS', title: 'SaaS: Software as a Service', def: 'Software sold as a subscription and delivered over the web rather than installed and owned. Tenna’s pricing is hardware plus a SaaS platform fee plus optional premium modules.' },
    { re: 'SOC 2(?: Type 1)?', title: 'SOC 2: System and Organization Controls', def: 'An independent audit of a software company’s security practices. Type 1 verifies the controls exist at a point in time. It is a common enterprise buying checkbox, and Tenna holds it.' },
    { re: 'ERP', title: 'ERP: Enterprise Resource Planning', def: 'Company-wide accounting and operations software (for contractors, systems like Sage, Viewpoint, or Foundation). Tenna pushes equipment costs, labor, and parts into the ERP so the books match the field without re-keying.' },
    { re: 'CMMS', title: 'CMMS: Computerized Maintenance Management System', def: 'Software for managing preventive maintenance, work orders, parts inventory, and mechanic time. Tenna’s Maintenance module is a CMMS built into the same platform as tracking, so shop work links directly to asset records.' },
    { re: 'PM', title: 'PM: Preventive Maintenance', def: 'Service performed on a schedule (by engine hours, mileage, or calendar) to prevent breakdowns. Tenna fires PM rules automatically from tracker data, such as creating a work order every 250 engine hours.' },
    { re: 'OEMs?', title: 'OEM: Original Equipment Manufacturer', def: 'The company that built the machine (Caterpillar, Komatsu, Volvo). Many OEMs ship equipment with factory telematics; Tenna pulls that data in so those machines show up on the platform without a Tenna tracker.' },
    { re: 'AEMP', title: 'AEMP: Association of Equipment Management Professionals', def: 'The industry group behind the AEMP/ISO 15143-3 telematics standard, a shared data format that lets one platform pull location and engine data from many different OEM systems.' },
    { re: 'UTC', title: 'UTC: Coordinated Universal Time', def: 'The global reference clock. An ELD’s internal clock must stay within 10 minutes of UTC or the device must declare a timing malfunction, so the app continuously synchronizes time.' },
    { re: 'NTP', title: 'NTP: Network Time Protocol', def: 'The standard internet mechanism for keeping a device’s clock accurate. The ELD anchors its clock to NTP, with GPS time as a fallback, to satisfy the 10-minute UTC drift rule.' },
    { re: 'CRC', title: 'CRC: Cyclic Redundancy Check', def: 'A checksum that proves a file was not corrupted or altered. The FMCSA output file ends with a CRC line, and getting it wrong is a known certification failure.' },
    { re: 'ASCII', title: 'ASCII: plain-text encoding', def: 'A basic plain-text character format. The FMCSA ELD output file must be a rigidly formatted ASCII text file with exact section ordering, which eRODS parses during inspections and audits.' },
    { re: '[Ii]dempotent', title: 'Idempotent', def: 'Safe to process more than once. If a flaky connection re-sends the same event, an idempotent ingestion API stores it exactly once. Essential for an ELD because drivers sync hours of queued events after working offline.' },
    { re: '[Ww]ebhooks?', title: 'Webhook', def: 'An automated HTTP callback that pushes an event to another system the moment it happens, instead of that system polling for changes. How Tenna can stream telemetry to the ELD backend, and how the ELD can push HOS events back.' },
    { re: '[Ss]tate machine', title: 'State machine', def: 'A software pattern where a system is always in exactly one defined state with strict rules for transitions. The HOS engine is a state machine over duty statuses, which makes the complex federal rules testable and auditable.' },
    { re: 'React Native', title: 'React Native', def: 'A framework from Meta for building iOS and Android apps from one JavaScript codebase, with the option to drop into native code where needed. The proposal recommends it, with native modules for Bluetooth pairing and background reliability.' },
    { re: 'IP handoff', title: 'IP handoff: Intellectual Property transfer', def: 'At the end of the engagement, AppAxis transfers full ownership of the code, designs, and documentation to Tenna, so Tenna owns its ELD outright with no ongoing license.' },

    /* Industry and market */
    { re: '[Ww]hite-label(?:ed|ing)?', title: 'White-label', def: 'Selling another company’s product under your own brand. Tenna’s current ELD is white-labeled from a partner, which caps margin, control, and integration depth. That is the reason this build is on the table.' },
    { re: '[Yy]ellow iron', title: 'Yellow iron', def: 'Construction slang for heavy earthmoving equipment (excavators, dozers, loaders), named for the signature yellow paint. Yellow iron has no road odometer and often sits idle, which is why it needs different trackers than trucks.' },
    { re: '[Cc]ost cod(?:es|e|ing)', title: 'Cost code', def: 'The construction accounting label that ties labor, equipment, and materials to a specific budget line on a job. Tagging tracker hours and mechanic time with cost codes is how Tenna data lands cleanly in the contractor’s ERP.' },
    { re: 'OTR', title: 'OTR: Over-the-Road', def: 'Long-haul trucking, the pattern of one driver living with one truck for days at a time. Incumbent ELDs are designed around OTR. Construction drivers hop between vehicles daily, which is the workflow gap a Tenna-native ELD can exploit.' },
    { re: 'SAP', title: 'SAP', def: 'The archetypal heavyweight enterprise software suite. Used here as shorthand: Tenna’s buyers have outgrown spreadsheets but do not want the cost and complexity of an SAP-scale system.' },
    { re: 'Motive', title: 'Motive (formerly KeepTruckin)', def: 'One of the big three general-purpose ELD and fleet-management platforms. Strong product and modern UX, but built for trucking fleets generally rather than construction specifically. A primary benchmark for this build.' },
    { re: 'Samsara', title: 'Samsara', def: 'A large publicly traded fleet-telematics platform and one of the big three incumbent ELDs. Like Motive, it treats construction as one vertical among many, which is the opening for a construction-native ELD.' },
    { re: 'Omnitracs(?: One)?', title: 'Omnitracs', def: 'The oldest of the big three ELD providers, with Qualcomm lineage, now owned by Solera. Strong in long-haul trucking, less modern UX. The third benchmark in the competitive review.' },
    { re: 'Geotab', title: 'Geotab', def: 'A major telematics platform known for its plug-in vehicle gateways and very large fleet deployments. Referenced as part of the broader ELD competitive landscape.' },

    /* Tenna products */
    { re: 'TennaCORE', title: 'TennaCORE', def: 'Tenna’s base platform and system of record: asset records, maps and geofences, utilization analytics, and the mobile app. Every module and tracker feeds it, and it holds the core data the ELD would integrate with.' },
    { re: 'TennaFLEET(?: II)?', title: 'TennaFLEET', def: 'Tenna’s GPS tracker for on-road trucks and vehicles. It plugs into the engine (ECM) and is the hardware the ELD app would pair with over Bluetooth for the required speed, odometer, and engine-hour data.' },
    { re: 'TennaCANbus', title: 'TennaCANbus', def: 'Tenna’s tracker for heavy equipment. It taps the machine’s CAN-bus to read engine hours and fault codes directly from the ECU, powering usage-based maintenance and equipment telemetry.' },
    { re: 'TennaCAM(?: 2\\.0| Fleet| Heavy Equipment)?', title: 'TennaCAM', def: 'Tenna’s AI dash cam line for trucks and heavy equipment. It detects events like harsh braking, feeds the Driver Scorecard, and provides video evidence for coaching and incident defense.' },
    { re: 'TennaINTEL', title: 'TennaINTEL', def: 'Solar-powered and portable GPS trackers for construction equipment without a usable data port. Keeps idle yellow iron on the map without wiring into the machine.' },
    { re: 'TennaMINI', title: 'TennaMINI', def: 'Plug-in and battery-powered GPS tracker for mid-sized equipment, with or without engines. Covers the middle of the fleet between heavy iron and hand tools.' },
    { re: 'TennaBLE', title: 'TennaBLE', def: 'Construction-grade Bluetooth (BLE) beacons for tools, attachments, concrete forms, and other small or unpowered assets. Nearby phones and gateways detect them and report last-seen locations.' },
    { re: 'TennaQR', title: 'TennaQR', def: 'Durable QR-coded tags and labels for small assets and consumables. Field workers scan them with the Tenna app to log location and condition and to submit requests.' }
  ];

  /* Containers where annotation would hurt the design or duplicate links. */
  var SKIP_SELECTOR = 'a, h1, h2, script, style, .nav, .kicker, .eyebrow, .nav-pill, .field-guide, .brand-row, .ico, .module-tag, .hw-class, .layer-label, .arch-flow, .gloss, .gloss-tip';

  var combined = new RegExp(TERMS.map(function (t) { return '\\b(?:' + t.re + ')\\b'; }).join('|'), 'g');
  var matchers = TERMS.map(function (t) { return { rx: new RegExp('^(?:' + t.re + ')$'), t: t }; });

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
