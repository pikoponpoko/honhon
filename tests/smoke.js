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

  // 入稿PDFの中身を確かめる：PDF/X-1a の OutputIntent、仕上がり（TrimBox）と塗り足し（BleedBox）の寸法、色空間、ページ数、フォント非埋め込み（ラスタ化）
  const pdfCheck = (buf, d, cs) => {
    const s = buf.toString('latin1'), MM = 72 / 25.4, near = (a, b) => Math.abs(a - b) < 0.6;
    expect(buf.subarray(0, 5).toString() === '%PDF-', 'PDFではない');
    expect(/\/GTS_PDFX/.test(s) && /\/OutputIntents/.test(s), 'PDF/X の OutputIntent がない');
    expect(/\/GTS_PDFXVersion\s*\(PDF\/X-1/.test(s) || /PDF\/X-1a/.test(s), 'PDF/X-1a の表記がない');
    expect(!/\/FontFile/.test(s), 'フォントが埋め込まれている（ラスタ化されていない）');
    expect(new RegExp('/' + cs).test(s), cs + ' の画像がない');
    const box = k => { const m = s.match(new RegExp('/' + k + '\\s*\\[\\s*([-\\d.]+)\\s+([-\\d.]+)\\s+([-\\d.]+)\\s+([-\\d.]+)')); return m && m.slice(1).map(Number); };
    const t = box('TrimBox'), b = box('BleedBox');
    expect(t && b, 'TrimBox／BleedBox がない');
    expect(near(t[2] - t[0], d.w * MM) && near(t[3] - t[1], d.h * MM), `仕上がりが ${d.w}×${d.h}mm でない: ${((t[2] - t[0]) / MM).toFixed(1)}×${((t[3] - t[1]) / MM).toFixed(1)}`);
    expect(near(t[0] - b[0], d.bleed * MM) && near(b[2] - t[2], d.bleed * MM), `塗り足しが ${d.bleed}mm でない`);
    const pages = (s.match(/\/Type\s*\/Page[^s]/g) || []).length;
    expect(pages === d.pages, `ページ数 ${pages}（期待 ${d.pages}）`);
  };
  const exportPdf = async () => {
    await page.getByRole('button', { name: '入稿データ書き出し' }).click();
    if (await page.locator('#x-dpi').isVisible()) await page.locator('#x-dpi').selectOption('350');
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 180000 }), page.locator('#x-go').click()]);
    const buf = require('fs').readFileSync(await dl.path());
    if (await page.locator('#x-cancel').isVisible()) await page.locator('#x-cancel').click();
    return buf;
  };
  const docSpec = () => page.evaluate(() => { const d = window.__thinbook.S.doc; return { w: d.kind === 'cover' ? null : d.trimW, h: d.trimH, bleed: d.bleed, pages: d.pages.length, kind: d.kind, spine: d.spine }; });

  await step('入稿PDF（モノクロ本文）が PDF/X-1a・仕上がり・塗り足し・ページ数どおり', async () => {
    const d = await docSpec();
    pdfCheck(await exportPdf(), d, 'DeviceGray');
  });

  await step('新規作成にスライドがない', async () => {
    await page.locator('#mNew .mb').click();
    const names = await page.locator('#mNew .mp button').allTextContents();
    await page.keyboard.press('Escape');
    expect(!names.some(n => /スライド/.test(n)), names.join(','));
    expect(!(await page.locator('#bPptx, #bPres, #bOutline, #bMaster, [data-tab=notes]').count()), 'スライド用のボタンが残っている');
  });

  await step('スライドの書類を開くと PowerPoint を案内して、今の書類は残る', async () => {
    const before = await page.evaluate(() => window.__thinbook.S.doc.name);
    const j = JSON.stringify({ app: 'honhon', version: 1, doc: { kind: 'slide', name: '古いスライド', trimW: 254, trimH: 142.875, bleed: 0, binding: 'left', color: 'cmyk', margins: { top: 10, bottom: 10, inner: 10, outer: 10 }, nombre: { mode: 'none', start: 1, size: 8, font: 'Noto Sans JP', offset: 8 }, pages: [{ id: 'p1', items: [] }] }, images: {} });
    await page.locator('#fOpen').setInputFiles({ name: '古いスライド.honhon.json', mimeType: 'application/json', buffer: Buffer.from(j) });
    await page.waitForFunction(() => /PowerPoint/.test(document.querySelector('#toast').textContent), null, { timeout: 5000 });
    const after = await page.evaluate(() => window.__thinbook.S.doc.name);
    expect(after === before, '書類が切り替わった: ' + after);
  });

  await step('入稿PDF（カラー表紙）が CMYK・背幅込みの仕上がりどおり', async () => {
    await page.evaluate(() => { const T = window.__thinbook; T.S.doc = T.newDoc({ kind: 'cover', name: '表紙テスト', printer: 'generic', w: 148, h: 210, binding: 'right', color: 'cmyk', pages: 1, spine: 5 }); T.S.images = {}; T.S.sel = null; T.S.page = 0; T.rebuild(); });
    const d = await docSpec();
    d.w = 148 * 2 + d.spine;
    pdfCheck(await exportPdf(), d, 'DeviceCMYK');
  });

  // カラー画像の版：RGB画像は Japan Color 2001 Coated のインキ量に、CMYKのPSDは元の版のまま入稿PDFに入る
  const cmykPsd = (w, h, ink) => { // 非圧縮 8bit CMYK の PSD（PSDの版は 255＝インキなし）
    const head = Buffer.alloc(26); head.write('8BPS', 0); head.writeUInt16BE(1, 4); head.writeUInt16BE(4, 12); head.writeUInt32BE(h, 14); head.writeUInt32BE(w, 18); head.writeUInt16BE(8, 22); head.writeUInt16BE(4, 24);
    const z = Buffer.alloc(4), comp = Buffer.alloc(2), planes = ink.map(v => Buffer.alloc(w * h, 255 - v));
    return Buffer.concat([head, z, z, z, comp, ...planes]);
  };
  const pdfInkAt = (buf, fx, fy) => {
    const s = buf.toString('latin1'), m = s.match(/\/Width (\d+) \/Height (\d+) \/ColorSpace \/DeviceCMYK[^>]*\/Length (\d+) >>\s*stream\r?\n/);
    expect(m, 'CMYKの画像がない');
    const st = m.index + m[0].length, raw = require('zlib').inflateSync(buf.subarray(st, st + +m[3])), W = +m[1], H = +m[2];
    const o = (Math.round(H * fy) * W + Math.round(W * fx)) * 4;
    return [...raw.subarray(o, o + 4)].map(v => Math.round(v / 2.55));
  };
  const placeAndExport = async (file) => {
    await page.evaluate(async ({ name, type, b64 }) => {
      const T = window.__thinbook, bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
      const im = await T.readImage(new File([u], name, { type }));
      T.S.doc = T.newDoc({ kind: 'body', name: '色テスト', printer: 'generic', w: 148, h: 210, binding: 'right', color: 'cmyk', pages: 2 });
      const d = T.S.doc; T.S.images = { pic: im }; T.S.sel = null; T.S.page = 0;
      d.pages[0].items.push({ id: 'pic1', type: 'image', x: -d.bleed, y: -d.bleed, w: 148 + 2 * d.bleed, h: 210 + 2 * d.bleed, imageId: 'pic', fit: 'cover' });
      T.rebuild();
    }, file);
    return exportPdf();
  };

  await step('CMYKのPSDは元の版のまま入稿PDFに入る', async () => {
    const ink = [30, 60, 10, 5].map(v => Math.round(v * 2.55));
    const pdf = await placeAndExport({ name: 'cmyk.psd', type: 'image/vnd.adobe.photoshop', b64: cmykPsd(40, 40, ink).toString('base64') });
    const got = pdfInkAt(pdf, 0.5, 0.25);
    expect(JSON.stringify(got) === JSON.stringify([30, 60, 10, 5]), 'インキ量が変わった: ' + got.join('/'));
  });

  await step('RGB画像は Japan Color 2001 Coated のインキ量になる', async () => {
    const png = await page.evaluate(() => { const c = document.createElement('canvas'); c.width = c.height = 40; const x = c.getContext('2d'); x.fillStyle = 'rgb(29,139,86)'; x.fillRect(0, 0, 40, 40); return c.toDataURL('image/png').split(',')[1]; });
    const got = pdfInkAt(await placeAndExport({ name: 'rgb.png', type: 'image/png', b64: png }), 0.5, 0.25);
    const want = [81, 32, 83, 0]; // littleCMS（sRGB→Japan Color 2001 Coated、知覚的）
    expect(got.every((v, i) => Math.abs(v - want[i]) <= 2), `インキ量 ${got.join('/')}（期待 ${want.join('/')}）`);
    const black = await page.evaluate(() => window.__thinbook.hexC('#000000'));
    expect(black.k === 100 && !black.c && !black.m && !black.y, '黒の文字色がスミ1色でない');
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

  await step('縦書きの約物・小書きの仮名はフォントの縦書き字形で組む', async () => {
    const r = await page.evaluate(() => {
      const { layout } = window.__thinbook;
      const it = { id: 'vtest', type: 'text', x: 0, y: 0, w: 10, h: 120, text: '「あ」、ぁー', font: 'Noto Serif JP', weight: 400,
        size: 9, leading: 175, track: 0, dir: 'v', align: 'start', color: { c: 0, m: 0, y: 0, k: 100 } };
      const g = layout(it).glyphs;
      const loc = Object.assign({}, it, { id: 'vtest2', font: 'この端末にないフォント' });
      return { vg: g.map(x => !!x.vg), rot: layout(loc).glyphs.map(x => x.rot) };
    });
    expect(r.vg.join() === 'true,false,true,true,true,true', '同梱フォントの縦書き字形 ' + r.vg.join());
    expect(r.rot[0] && r.rot[5], '縦書き字形のないフォントは回転で組む ' + r.rot.join());
  });

  await step('見出しの大きさの文字は文節の途中で改行しない', async () => {
    const r = await page.evaluate(() => {
      const { layout } = window.__thinbook;
      const lines = o => { const g = layout(Object.assign({ id: 'phr' + Math.random(), type: 'text', x: 0, y: 0, w: 60, h: 200,
        text: 'アニメーション作家の個展「ねこと暮らす日々」', font: 'Noto Sans JP', weight: 700, leading: 130, track: 0, dir: 'h',
        align: 'start', color: { c: 0, m: 0, y: 0, k: 100 } }, o)).glyphs, ys = [...new Set(g.map(x => x.y.toFixed(2)))];
        return ys.map(y => g.filter(x => x.y.toFixed(2) === y).map(x => x.s).join('')); };
      return { big: lines({ size: 20 }), body: lines({ size: 9 }) };
    });
    expect(r.big[r.big.length - 1] === '暮らす日々」', '見出し ' + r.big.join(' / '));
    expect(r.body[0] === 'アニメーション作家の個展「ねこと暮ら', '本文は字単位で詰める ' + r.body.join(' / '));
  });

  await step('禁則（JLREQ）とルビ', async () => {
    const r = await page.evaluate(() => {
      const { layout } = window.__thinbook;
      const base = { type: 'text', x: 0, y: 0, h: 200, font: 'Noto Sans JP', weight: 400, size: 10, leading: 175, track: 0,
        dir: 'h', align: 'start', color: { c: 0, m: 0, y: 0, k: 100 } };
      const lines = o => { const g = layout(Object.assign({ id: 'k' + Math.random() }, base, o)).glyphs.filter(x => !x.fs),
        ys = [...new Set(g.map(x => x.y.toFixed(2)))]; return ys.map(y => g.filter(x => x.y.toFixed(2) === y).map(x => x.s).join('')); };
      const em = 10 * 25.4 / 72;
      const rb = layout(Object.assign({ id: 'rb' }, base, { w: 60, text: '｜古本屋《ふるほんや》と東京《とうきょう》' })).glyphs;
      return {
        close: lines({ w: em * 5.5, text: 'あいうえお。」かきく' }),
        word: lines({ w: em * 5, text: 'あいうえhello world' }),
        rubyBase: rb.filter(x => !x.fs).map(x => x.s).join(''), ruby: rb.filter(x => x.fs).map(x => x.s).join(''),
      };
    });
    expect(r.close[1].startsWith('お。」'), '句点と閉じ括弧は追い出す ' + r.close.join(' / '));
    expect(r.word[0].trim() === 'あいうえ' && r.word[1].trim() === 'hello', '英単語の途中で切らない ' + r.word.join(' / '));
    expect(r.rubyBase === '古本屋と東京' && r.ruby === 'ふるほんやとうきょう', 'ルビ ' + r.rubyBase + ' / ' + r.ruby);
  });

  // ag-psd はCDNから読む。ネットに出られない環境では AG_PSD_BUNDLE に ag-psd@34.1.0 の dist/bundle.js を指定する
  if (process.env.AG_PSD_BUNDLE) await page.route('https://cdn.jsdelivr.net/npm/ag-psd@34.1.0/dist/bundle.js',
    r => r.fulfill({ path: process.env.AG_PSD_BUNDLE, contentType: 'text/javascript' }));
  await step('合成画像のないPSD・PSBはレイヤーから読む（ag-psd）', async () => {
    const r = await page.evaluate(async () => {
      const T = window.__thinbook, A = await loadAgPsd();
      const cnv = (col, w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); g.fillStyle = col; g.fillRect(0, 0, w, h); return c; };
      const px = (c, x, y) => Array.from(c.getContext('2d').getImageData(x, y, 1, 1).data.slice(0, 3));
      const ab = b => b instanceof ArrayBuffer ? b : b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
      const noComp = await T.readPSD(ab(A.writePsd({ width: 100, height: 80, canvas: cnv('#fff', 100, 80), children: [
        { name: 'a', canvas: cnv('#f00', 60, 80), left: 0, top: 0 }, { name: 'b', canvas: cnv('#00f', 40, 80), left: 60, top: 0, opacity: 0.5 },
        { name: 'c', canvas: cnv('#0f0', 100, 80), left: 0, top: 0, hidden: true }] })));
      const psb = await T.readPSD(ab(A.writePsd({ width: 50, height: 50, canvas: cnv('#0a0', 50, 50), children: [{ name: 'a', canvas: cnv('#0a0', 50, 50) }] }, { psb: true })));
      return { a: px(noComp, 10, 10), b: px(noComp, 90, 10), psb: px(psb, 5, 5) };
    });
    expect(r.a.join() === '255,0,0', '合成画像なしのPSD（左） ' + r.a);
    expect(Math.abs(r.b[0] - 128) < 4 && r.b[2] === 255, '合成画像なしのPSD（不透明度50%） ' + r.b);
    expect(r.psb.join() === '0,170,0', 'PSB ' + r.psb);
  });

  await step('スクリプトエラーが出ない', async () => {
    const js = errors.filter(e => !e.startsWith('native dialog'));
    expect(!js.length, js.join(' / '));
  });

  await browser.close();
  console.log(failed ? failed + ' 件失敗' : 'すべて成功');
  process.exit(failed ? 1 : 0);
})();
