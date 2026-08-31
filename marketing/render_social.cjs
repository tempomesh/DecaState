const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const FPS = 18, OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1080 } });
  await p.goto('file://' + path.join(__dirname, 'social_film3.html'));
  await p.waitForFunction('window.renderFrame && document.fonts.ready');
  await p.waitForTimeout(600);
  const dur = await p.evaluate('window.FILM_DURATION');
  const total = Math.round(dur * FPS);
  process.stdout.write(`duration ${dur.toFixed(1)}s → ${total} frames\n`);
  for (let i = 0; i < total; i++) {
    await p.evaluate((t) => window.renderFrame(t), i / FPS);
    if (i % 40 === 0) await p.waitForTimeout(30); // let transitions settle occasionally
    await p.screenshot({ path: path.join(OUT, 'f' + String(i).padStart(4, '0') + '.png') });
  }
  // stills: hero + stats (transitions forced complete)
  await p.evaluate((t) => window.renderFrame(t), 2.0); await p.waitForTimeout(600);
  await p.screenshot({ path: path.join(OUT, 'still_hero.png') });
  await p.evaluate((t) => window.renderFrame(t), dur - 3.4); await p.waitForTimeout(700);
  await p.screenshot({ path: path.join(OUT, 'still_stats.png') });
  await b.close();
  process.stdout.write('done\n');
})();
