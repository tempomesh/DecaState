const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const FPS = 24;
const OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.join(__dirname, 'coding_film.html'));
  await p.waitForFunction('window.renderFrame && document.fonts.ready');
  await p.waitForTimeout(500);
  const dur = await p.evaluate('window.FILM_DURATION');
  const total = Math.round(dur * FPS);
  process.stdout.write(`frames ${total} @ ${FPS}fps (${dur.toFixed(1)}s)\n`);
  for (let i = 0; i < total; i++) {
    await p.evaluate((t) => window.renderFrame(t), i / FPS);
    await p.screenshot({ path: path.join(OUT, 'c' + String(i).padStart(4, '0') + '.png') });
  }
  await b.close();
  process.stdout.write('done\n');
})();
