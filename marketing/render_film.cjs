// Deterministic frame renderer for the DecaState launch film.
// Usage: NODE_PATH=<peerknown>/node_modules node render_film.cjs <framesDir>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const FPS = 30;
const OUT = process.argv[2] || path.join(__dirname, 'frames');
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'film.html'));
  await page.waitForFunction('window.renderFrame && document.fonts.ready');
  await page.waitForTimeout(600); // let webfonts settle
  const duration = await page.evaluate('window.DURATION');
  const total = Math.round(duration * FPS);
  process.stdout.write(`Rendering ${total} frames @ ${FPS}fps (${duration}s)\n`);
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    await page.evaluate((tt) => window.renderFrame(tt), t);
    const name = 'f' + String(i).padStart(5, '0') + '.png';
    await page.screenshot({ path: path.join(OUT, name) });
    if (i % 60 === 0) process.stdout.write(`  ${i}/${total}\n`);
  }
  await browser.close();
  process.stdout.write('frames done\n');
})();
