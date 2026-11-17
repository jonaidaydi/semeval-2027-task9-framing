const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const original = path.join(root, 'visualisierung', 'index.html');
  const output = path.join(root, 'outputs', 'visualization-browser-check');
  const copyDirectory = path.join(output, 'Standalone with spaces');
  fs.mkdirSync(copyDirectory, {recursive: true});
  const portable = path.join(copyDirectory, 'Framing Demo.html');
  fs.copyFileSync(original, portable);
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({viewport: {width: 980, height: 1250}, colorScheme: 'light'});
    const network = [], errors = [];
    await context.route(/^https?:/, route => {
      network.push(route.request().url());
      return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    const frame = page;
    for (const file of [original, portable]) {
      await page.goto(pathToFileURL(file).href);
      await frame.locator('#fg-graph circle').first().waitFor();
      assert.match(await frame.locator('#fg-graph').textContent(), /0,282/);
      assert.match(await frame.locator('#fg-pred').textContent(), /kein Frame/);
    }
    const evaluation = JSON.parse(fs.readFileSync(path.join(root, 'results', 'reference.json'), 'utf8'));
    const metricText = await frame.locator('#fg-metrics').textContent();
    assert.equal(await frame.locator('#fg-metrics tbody tr').count(), 5);
    for (const [key, value] of Object.entries(evaluation.metrics)) {
      const cells = await frame.locator(`#fg-metrics tr[data-model="${key}"] td`).allTextContents();
      assert.deepEqual(cells, ['micro_f1', 'macro_f1'].map(metric => value[metric].toLocaleString('de-DE', {
        minimumFractionDigits: 4, maximumFractionDigits: 4,
      })));
    }
    assert.match(await frame.locator('#fg-evaluation-scope').textContent(), /222 Absätze aus 20/);
    await frame.locator('#fg-theme').check();
    await page.waitForFunction(() => document.documentElement.style.colorScheme === 'dark');
    assert.equal(await frame.locator('html').evaluate(el => el.style.colorScheme), 'dark');
    await page.reload();
    await frame.locator('#fg-graph circle').first().waitFor();
    assert.equal(await frame.locator('#fg-theme').isChecked(), true);
    assert.equal(await page.locator('html').evaluate(el => el.style.colorScheme), 'dark');
    await frame.locator('#fg-theme').uncheck();
    await page.emulateMedia({colorScheme: 'dark'});
    assert.equal(await frame.locator('html').evaluate(el => el.style.colorScheme), 'light');
    await page.waitForFunction(() => document.documentElement.style.colorScheme === 'light');
    await page.emulateMedia({colorScheme: 'light'});
    await frame.locator('#fg-graph button').first().click();
    assert.match(await frame.locator('#fg-detail').textContent(), /public.*0,285/);
    await frame.locator('#fg-play').click();
    await frame.locator('#fg-play').filter({hasText: 'Anhalten'}).waitFor();
    await frame.locator('#fg-play').click();
    for (const caseId of ['0', '1', '3', '2']) {
      await frame.locator('#fg-case').selectOption(caseId);
      const labels = await frame.locator('#fg-frame option').evaluateAll(items => items.map(item => item.value));
      assert.equal(labels.length, 14);
      for (const label of labels) {
        await frame.locator('#fg-frame').selectOption(label);
        assert.match(await frame.locator('#fg-status').textContent(), /222\/222/);
        assert.equal(await frame.locator('#fg-metrics').textContent(), metricText);
      }
    }
    await frame.locator('#fg-case').selectOption('1');
    await frame.locator('#fg-frame').selectOption('Public_opinion');
    await frame.locator('#fg-graph button').last().click();
    await page.waitForFunction(() => Object.values(localStorage).some(value => {
      try {
        const state = JSON.parse(value).modelContent;
        return state?.caseId === '1' && state?.frame === 'Public_opinion' && state?.selected === 'Basiswert';
      } catch { return false; }
    }));
    await page.reload();
    await frame.locator('#fg-graph circle').first().waitFor();
    assert.equal(await frame.locator('#fg-case').inputValue(), '1');
    assert.equal(await frame.locator('#fg-frame').inputValue(), 'Public_opinion');
    assert.match(await frame.locator('#fg-detail').textContent(), /Basiswert/);
    await frame.locator('#fg-mode').selectOption('semantic');
    assert.match(await frame.locator('#fg-status').textContent(), /kein Transformer trainiert/);
    assert.match(await frame.locator('#fg-graph').textContent(), /Ergebnis offen/);
    assert.equal(await frame.locator('#fg-frame-control').isVisible(), false);
    assert.equal(await frame.locator('#fg-metrics').textContent(), metricText);
    await page.screenshot({path: path.join(output, 'semantic.png'), fullPage: true});
    await frame.locator('#fg-mode').selectOption('linear');
    await frame.locator('#fg-case').selectOption('2');
    await page.screenshot({path: path.join(output, 'desktop.png'), fullPage: true});
    const layout = [];
    for (const width of [1920, 780, 560, 390, 352]) {
      await page.setViewportSize({width, height: 1500});
      await page.waitForTimeout(100);
      const measurement = await frame.locator('#framing-netz-1711').evaluate(root => {
        const bounds = root.getBoundingClientRect();
        const outside = [...root.querySelectorAll('button,select,svg text,th,td')].filter(element => {
          if (!element.getClientRects().length) return false;
          const box = element.getBoundingClientRect();
          return box.left < bounds.left - 1 || box.right > bounds.right + 1;
        }).map(element => element.textContent.slice(0, 80));
        const wrappedNumbers = [...root.querySelectorAll('#fg-metrics td')].filter(element => {
          const range = document.createRange(); range.selectNodeContents(element);
          return range.getClientRects().length > 1;
        }).map(element => element.textContent);
        return {width: bounds.width, graphWidth: root.querySelector('svg').getBoundingClientRect().width,
          scroll: document.documentElement.scrollWidth, viewport: innerWidth,
          innerVerticalOverflow: document.documentElement.scrollHeight > innerHeight + 1, outside, wrappedNumbers};
      });
      assert.deepEqual(measurement.outside, [], JSON.stringify(measurement));
      assert(measurement.scroll <= measurement.viewport + 1);
      assert(measurement.width <= 1080);
      assert(measurement.graphWidth <= 960);
      assert.deepEqual(measurement.wrappedNumbers, []);
      layout.push(measurement);
      if (width === 390) await page.screenshot({path: path.join(output, 'mobile.png'), fullPage: true});
    }
    await frame.locator('#fg-theme').check();
    await page.emulateMedia({colorScheme: 'light', reducedMotion: 'reduce'});
    await frame.locator('#fg-play').click();
    assert.equal(await frame.locator('#fg-play').textContent(), 'Wortfluss abspielen');
    await page.setViewportSize({width: 980, height: 1250});
    await page.screenshot({path: path.join(output, 'dark.png'), fullPage: true});
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    const report = {passed: true, localFile: true, portableSingleFile: true, persistedState: true,
      caseFrameCombinations: 56, evaluationMatchesReport: true, themeSwitchAndPersistence: true,
      networkRequests: network, errors, layout};
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
