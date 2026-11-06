// HonHon の主要な流れを実ブラウザで確かめるスモークテスト
// 使い方: sh scripts/build.sh で dist/ を作り、dist/ を http://localhost:8765/ で配信してから node tests/smoke.js
const { chromium } = require('playwright');
const URL = process.env.HONHON_URL || 'http://localhost:8765/';

let failed = 0;
const step = async (name, fn) => {
  try { await fn(); console.log('ok   ' + name); }
  catch (e) { failed++; console.log('FAIL ' + name + '\n     ' + (e && e.message || e).split('\n')[0]); }
};
const expect = (cond, msg) => { if (!cond) throw new Error(msg); };

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('dialog', d => { errors.push('native dialog: ' + d.message()); d.dismiss(); });

  await step('起動すると新規作成が出る', async () => {
    await page.goto(URL);
    await page.getByRole('dialog').getByText('新規作成').waitFor({ timeout: 10000 });
  });

  await step('サンプル冊子を開ける', async () => {
    await page.getByRole('button', { name: 'サンプル冊子を開く' }).click();
    await page.waitForFunction(() => window.__thinbook.S.doc.name === 'サンプル冊子');
    const n = await page.locator('#pages .thumb').count();
    expect(n >= 8, 'ページのサムネイルが ' + n + ' 枚');
  });

  await step('ページをドラッグで並べ替えられる', async () => {
    const before = await page.evaluate(() => window.__thinbook.S.doc.pages.map(p => p.plan && p.plan.title || ''));
    await page.locator('#pages .thumb[data-i="1"]').dragTo(page.locator('#pages .thumb[data-i="2"]'));
    const after = await page.evaluate(() => window.__thinbook.S.doc.pages.map(p => p.plan && p.plan.title || ''));
    expect(after[2] === before[1] && after[1] === before[2], '並びが変わっていない: ' + after.slice(0, 4).join(','));
    await page.keyboard.press('Control+z');
  });

  await step('自動保存して開き直すと同じ書類が開く', async () => {
    await page.waitForFunction(() => document.querySelector('#saveStatus') && document.querySelector('#saveStatus').textContent === 'この端末に保存済み', null, { timeout: 10000 });
    await page.reload();
    await page.waitForFunction(() => window.__thinbook.S.doc && window.__thinbook.S.doc.name === 'サンプル冊子', null, { timeout: 10000 });
  });

  await step('入稿データ（PDF）を書き出せる', async () => {
    await page.getByRole('button', { name: '入稿データ書き出し' }).click();
    await page.locator('#x-dpi').selectOption('350');
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 120000 }), page.locator('#x-go').click()]);
    const path = await dl.path();
    const head = require('fs').readFileSync(path).subarray(0, 5).toString();
    expect(head === '%PDF-', 'PDFではない: ' + head);
    if (await page.locator('#x-cancel').isVisible()) await page.locator('#x-cancel').click();
  });

  await step('新規スライドを作るとフォントの代替表示の通知が出ない', async () => {
    await page.locator('#mNew .mb').click();
    await page.locator('#bNewS').click();
    await page.getByRole('button', { name: '作成' }).click();
    await page.waitForFunction(() => window.__thinbook.S.doc.kind === 'slide');
    await page.waitForTimeout(800);
    const t = await page.locator('#toast').textContent();
    const shown = await page.locator('#toast').isVisible();
    expect(!(shown && /代替表示/.test(t)), t);
  });

  await step('スライドが画面に収まる', async () => {
    const r = await page.evaluate(() => { const c = document.querySelector('#spreads canvas').getBoundingClientRect(), s = document.querySelector('#stage').getBoundingClientRect(); return { cr: c.right, sr: s.right }; });
    expect(r.cr <= r.sr, 'スライドの右端がはみ出している');
  });

  await step('ブラウザ標準の確認ダイアログを使わない', async () => {
    expect(!errors.some(e => e.startsWith('native dialog')), errors.join(' / '));
  });

  await step('スマホ幅で横スクロールが出ない', async () => {
    const m = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const p = await m.newPage();
    p.on('pageerror', e => errors.push(e.message));
    await p.goto(URL);
    await p.getByRole('button', { name: 'サンプル冊子を開く' }).click();
    await p.waitForTimeout(800);
    expect(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)), '横スクロールがある');
    await m.close();
  });

  await step('スクリプトエラーが出ない', async () => {
    const js = errors.filter(e => !e.startsWith('native dialog'));
    expect(!js.length, js.join(' / '));
  });

  await browser.close();
  console.log(failed ? failed + ' 件失敗' : 'すべて成功');
  process.exit(failed ? 1 : 0);
})();
