// Screenshot page elements with the installed Google Chrome, for confluence_export.py.
// Usage: node tools/wf_shots.js <url> <list.json>
// list.json: [{ "selector": "#d1 .wf-frame-col", "out": "/abs/path/d1.png" }, ...]
// Needs puppeteer-core (npm install --save-dev puppeteer-core).
'use strict';
const fs = require('fs');
const puppeteer = require('puppeteer-core');

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const [, , url, listPath] = process.argv;
const list = JSON.parse(fs.readFileSync(listPath, 'utf8'));

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1360, height: 1000, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 90000 });
  // No scroll-reveal animation, no fixed revision control, no change marks.
  await page.addStyleTag({ content:
    '.reveal{opacity:1!important;transform:none!important;transition:none!important}' +
    '.revbar{display:none!important}' +
    'body.rev-marks *{box-shadow:none!important;outline:none!important}' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  let missing = 0;
  for (const { selector, out } of list) {
    // several nodes can match (one per revision); take the first one that is laid out
    let el = null;
    for (const cand of await page.$$(selector)) {
      if (await cand.boundingBox()) { el = cand; break; }
    }
    if (!el) { console.log('MISSING ' + selector); missing++; continue; }
    try {
      await el.evaluate(e => e.scrollIntoView({ block: 'center' }));
      await new Promise(r => setTimeout(r, 60));
      await el.screenshot({ path: out });
    } catch (e) {
      console.log('FAILED ' + selector + ': ' + e.message.split('\n')[0]); missing++;
    }
  }
  await browser.close();
  console.log(`${list.length - missing} screenshots, ${missing} missing`);
  process.exit(missing ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
