# -*- coding: utf-8 -*-
"""画像・映像／タイトル／連絡先のスライドを src/boards.json に入れる。

python3 tools/boards/media.py src/boards.json

画像は裁ち落とし（スライドの端まで）を基本に、空の画像枠（i）・動画枠（v）だけで組む。
文字は本文18pt・ラベル14pt・飾り9pt以上。色は役割（k＝キーカラー、on@k＝その上の文字）で書き、キーカラーに追従させる。
動画の上には文字を重ねない（発表中は動画が最前面に出るため）。
"""
import sys, json

W, H = 338.7, 190.5
INK, GRY, LN, WH = '#1a1a1a', '#666666', '#cccccc', '#ffffff'
MONO = 'Noto Sans Mono'
CIRCLE = 'M1000 500C1000 776 776 1000 500 1000C224 1000 0 776 0 500C0 224 224 0 500 0C776 0 1000 224 1000 500Z'

def r1(v): return round(v, 1)
def img(x, y, w, h, g=None):
    o = {'t': 'i', 'b': [r1(x), r1(y), r1(w), r1(h)]}
    if g: o['g'] = g
    return o
def vid(x, y, w, h):
    return {'t': 'v', 'b': [r1(x), r1(y), r1(w), r1(h)]}
def box(x, y, w, h, f=None, s=None, sw=None, g=None):
    o = {'t': 'r', 'b': [r1(x), r1(y), r1(w), r1(h)]}
    if f: o['f'] = f
    if s: o['s'] = s; o['sw'] = sw or 0.5
    if g: o['g'] = g
    return o
def txt(x, y, w, h, s, z, c=INK, wt=None, al=None, an=None, ld=120, tr=None, f=None, ps=None):
    o = {'t': 'x', 'b': [r1(x), r1(y), r1(w), r1(h)], 's': s, 'z': z, 'c': c, 'ld': ld}
    if wt: o['wt'] = wt
    if al: o['al'] = al
    if an: o['an'] = an
    if tr: o['tr'] = tr
    if f: o['f'] = f
    if ps: o['ps'] = ps
    return o
def para(*qs):
    out = []
    for q in qs:
        d = {'r': q[0], 'b': q[1]}
        if len(q) > 2: d['cr'] = q[2]
        out.append(d)
    return out
def poly(*pts):
    """0〜1000 の座標で多角形の切り抜き形を作る"""
    return 'M' + 'L'.join('%d %d' % p for p in pts) + 'Z'

def grid(cols, rows, x=0, y=0, w=W, h=H, gap=0, kind=img):
    cw, rh = (w - gap * (cols - 1)) / cols, (h - gap * (rows - 1)) / rows
    return [kind(x + c * (cw + gap), y + r * (rh + gap), cw, rh) for r in range(rows) for c in range(cols)]

PINS = []
def pin(pid, name):
    p = {'id': pid, 'name': name, 'slides': []}; PINS.append(p)
    def add(n, it, bg=WH, note=None):
        sl = {'n': n, 'bg': bg, 'it': it}
        if note: sl['note'] = note
        p['slides'].append(sl)
    return add

# =====================================================================
# 画像・映像
# =====================================================================
add = pin('media', '画像・映像')

add('全面：1枚を端まで', [img(0, 0, W, H)])
add('黒帯：全面＋下にキャプション', [
    img(0, 0, W, H - 20),
    txt(12, H - 20, W - 24, 20, 'キャプション　作品タイトル（2026）', 14, c=WH, an='ctr')], bg=INK)
add('白帯：全面＋下に見出しと説明', [
    img(0, 0, W, 148),
    txt(12, 152, 120, 34, '見出し', 28, wt=700, an='ctr'),
    txt(136, 152, W - 148, 34, '説明を1〜2行で書く。場面・技法・制作時期など。', 18, c=GRY, an='ctr')])
add('色の札：全面＋左下に場面名', [
    img(0, 0, W, H),
    box(0, H - 40, 132, 40, f='k'),
    txt(12, H - 40, 112, 40, '場面の名前\nScene 01', 20, c='on@k', wt=700, an='ctr', ld=115, ps=para((1, 1), (0.7, 0)))])
add('番号：全面＋右に番号', [
    img(0, 0, W - 40, H),
    txt(W - 40, 12, 40, 40, '01', 32, c='k', wt=700, al='c', f=MONO),
    txt(W - 38, H - 46, 36, 34, '場面\n名前', 14, al='c', an='b', ld=115)])
add('2枚：左右に裁ち落とし', [img(0, 0, W / 2, H), img(W / 2, 0, W / 2, H)])
add('2枚大小：左右に大小', [img(0, 0, 216, H), img(216, 0, W - 216, H)])
add('2段：上下に横長の帯', [img(0, 0, W, H / 2), img(0, H / 2, W, H / 2)])
add('3列：縦長に裁ち落とし', grid(3, 1))
add('4列：縦長に裁ち落とし', grid(4, 1))
add('大1小2：左に大きく、右に2枚', [img(0, 0, 226, H), img(226, 0, W - 226, H / 2), img(226, H / 2, W - 226, H / 2)])
add('大1小3：左に大きく、右に3枚', [img(0, 0, 226, H)] + grid(1, 3, x=226, w=W - 226))
add('大1下4：上に大きく、下に4枚', [img(0, 0, W, 130)] + grid(4, 1, y=130, h=H - 130))
add('2×2：裁ち落とし', grid(2, 2))
add('3×2：裁ち落とし', grid(3, 2))
add('4×2：裁ち落とし', grid(4, 2))
add('3×3：裁ち落とし', grid(3, 3))
add('4×3：裁ち落とし', grid(4, 3))
add('6×2：12枚を裁ち落とし', grid(6, 2))
add('黒い目地：3×2', grid(3, 2, x=4, y=4, w=W - 8, h=H - 8, gap=2.5), bg=INK)
add('白い目地：4×3', grid(4, 3, x=6, y=6, w=W - 12, h=H - 12, gap=3))
add('モザイク：大きさ違いの6枚', [
    img(0, 0, 150, 120), img(150, 0, 110, 70), img(260, 0, W - 260, 70),
    img(150, 70, W - 150, 50), img(0, 120, 200, H - 120), img(200, 120, W - 200, H - 120)])

# コマ割り：枠線は少し大きい同じ形の図形を画像の下に敷いて描く（上に重ねると画像枠をタップできなくなる）
def koma(cells, bg=WH, line=INK, t=0.8):
    out = []
    for x, y, w, h, g in cells:
        out.append(box(x - t, y - t, w + 2 * t, h + 2 * t, f=line, g=g))
        out.append(img(x, y, w, h, g))
    return out
M = 5
def P(*pts):
    """スライド上の座標（mm）の多角形を、枠（x,y,w,h）と切り抜き形にする"""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x, y, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    return (x, y, w, h, poly(*[(round((a - x) / w * 1000), round((b - y) / h * 1000)) for a, b in pts]))
def Q(x, y, w, h): return (x, y, w, h, None)
R, B = W - M, H - M
add('斜め3コマ：コマ割り', koma([
    P((M, M), (155, M), (128, B), (M, B)),
    P((158.5, M), (R, M), (R, 90), (145.8, 90)),
    P((145.2, 94), (R, 94), (R, B), (131.5, B))]))
add('4コマ：横長1＋下に3コマ', koma([
    Q(M, M, W - 2 * M, 84),
    Q(M, 94, 104, H - 94 - M), Q(M + 107, 94, 104, H - 94 - M), Q(M + 214, 94, W - 2 * M - 214, H - 94 - M)]))
add('斜め2コマ：コマ割り', koma([
    P((M, M), (205, M), (133, B), (M, B)),
    P((209, M), (R, M), (R, B), (137, B))]))
add('5コマ：縦長の大ゴマ＋4コマ', koma([
    Q(M, M, 120, H - 2 * M),
    Q(128, M, 100, 88), Q(231, M, R - 231, 88),
    P((128, 96), (278, 96), (263, B), (128, B)),
    P((282, 96), (R, 96), (R, B), (267, B))]))
add('黒地4コマ：段違いのコマ割り', koma([
    (M, M, 164, 88, None), (172, M, W - M - 172, 88, None),
    (M, 96, 110, H - 96 - M, None), (118, 96, W - M - 118, H - 96 - M, None)], line=WH), bg=INK)

# フィルム：黒地に送り穴（白の小さな四角）とコマ
def holes(y, n=26, w=6, h=4.2):
    step = W / n
    return [box(i * step + (step - w) / 2, y, w, h, f=WH) for i in range(n)]
def film_h(n, label=True, fh=118, y0=None):
    y0 = (H - fh) / 2 if y0 is None else y0
    gap = 4
    fw = (W - gap * (n + 1)) / n
    out = holes(y0 - 13) + holes(y0 + fh + 8.8)
    out += [img(gap + i * (fw + gap), y0, fw, fh) for i in range(n)]
    if label:
        out += [txt(gap + i * (fw + gap), y0 + fh + 15, fw, 10, '%02d' % (i + 1), 9, c=WH, f=MONO) for i in range(n)]
    return out
add('フィルム3：横に3コマ', film_h(3), bg=INK)
add('フィルム4：横に4コマ', film_h(4), bg=INK)
add('フィルム5：横に5コマ＋見出し', film_h(5, False) + [
    txt(12, 6, W - 24, 18, 'コマ送り　Scene 01', 14, c=WH, an='ctr')], bg=INK)
def film_v(x, n=3):
    fw = 100; out = []
    sh = H / 14
    for i in range(14):
        out.append(box(x - 10, i * sh + (sh - 4.2) / 2, 5, 4.2, f=WH))
        out.append(box(x + fw + 5, i * sh + (sh - 4.2) / 2, 5, 4.2, f=WH))
    gap = 4; fh = (H - gap * (n + 1)) / n
    out += [img(x, gap + i * (fh + gap), fw, fh) for i in range(n)]
    return out
add('縦フィルム：左に帯、右に文字', [box(0, 0, 130, H, f=INK)] + film_v(15) + [
    txt(152, 24, W - 172, 30, '見出し', 32, wt=700),
    txt(152, 64, W - 172, 100, '使った技法や、コマの流れを説明する。\n1コマごとの動き、枚数、撮影の工夫など。', 18, ld=150)])
add('コマ送り6：番号付き', sum([[img(8 + c * 109, 14 + r * 88, 104, 66),
    txt(8 + c * 109, 82 + r * 88, 104, 12, '%02d' % (r * 3 + c + 1), 14, c='k', wt=700, f=MONO)] for r in range(2) for c in range(3)], []))
add('コマ送り8：1列に並べる', [img(4 + i * 41.8, 64, 38.5, 54) for i in range(8)] + [
    txt(4 + i * 41.8, 122, 38.5, 10, '%02d' % (i + 1), 9, c=GRY, f=MONO) for i in range(8)] + [
    txt(12, 20, W - 24, 24, '動きの分解', 28, wt=700)])

# 動画：16:9 の枠。上に文字を重ねない
add('動画全面：端まで', [vid(0, 0, W, H)], bg=INK, note='動画枠をクリックして動画を入れる')
add('動画＋字幕：黒地＋下にキャプション', [
    vid(36, 8, 266.7, 150),
    txt(36, 162, 266.7, 24, '作品タイトル（2026）　3分20秒', 18, c=WH, an='ctr')], bg=INK)
add('動画＋番号：下に見出しと説明', [
    vid(0, 0, 266.7, 150),
    box(266.7, 0, W - 266.7, 150, f='k'),
    txt(274, 8, W - 282, 30, '01', 32, c='on@k', wt=700, f=MONO),
    txt(12, 154, 160, 32, '作品タイトル', 28, wt=700, an='ctr'),
    txt(176, 154, W - 188, 32, '2026年／3分20秒／手描き', 18, c=GRY, an='ctr')])
add('動画＋文：左に動画、右に文字', [
    vid(0, 33.6, 218, 122.6),
    txt(230, 34, W - 242, 26, '作品タイトル', 28, wt=700),
    txt(230, 70, W - 242, 86, '作品の説明を3〜4行で。\n\n2026年／3分20秒', 18, ld=150)])
add('動画2本：比べる', [
    vid(6, 46, 160, 90), vid(W - 166, 46, 160, 90),
    txt(6, 140, 160, 12, 'Before', 14, c=WH), txt(W - 166, 140, 160, 12, 'After', 14, c=WH),
    txt(6, 16, W - 12, 22, '比べる', 24, c=WH, wt=700)], bg=INK)
add('動画4本：2×2', grid(2, 2, kind=vid), bg=INK)
add('動画3本：横に並べる', grid(3, 1, x=4, y=63, w=W - 8, h=60.3, gap=4, kind=vid) + [
    txt(4 + i * 111.6, 127, 106.9, 12, t, 14, c=WH) for i, t in enumerate(['作品タイトル1', '作品タイトル2', '作品タイトル3'])], bg=INK)
add('動画＋静止画：右に3枚', [vid(0, 0, 254, 142.9)] + grid(1, 3, x=254, w=W - 254, h=142.9) + [
    txt(12, 148, W - 24, 36, '作品タイトル　2026年／3分20秒', 18, an='ctr')])
add('縦動画：中央、左右に文字', [
    vid((W - 107.2) / 2, 0, 107.2, H),
    txt(12, 16, (W - 107.2) / 2 - 24, 60, '作品タイトル', 32, c=WH, wt=700),
    txt((W + 107.2) / 2 + 12, H - 76, (W - 107.2) / 2 - 24, 60, '縦型の映像。\nSNS用・展示用など。', 18, c=WH, an='b', ld=150)], bg=INK)
add('縦動画3本：横に並べる', grid(3, 1, x=(W - 3 * 90 - 2 * 8) / 2, y=8, w=3 * 90 + 2 * 8, h=160, gap=8, kind=vid) + [
    txt((W - 286) / 2 + i * 98, 172, 90, 12, t, 14, c=WH, al='c') for i, t in enumerate(['01', '02', '03'])], bg=INK)

# =====================================================================
# タイトル
# =====================================================================
add = pin('titles', 'タイトル')
TT, ET, AU = '作品タイトル', 'English Title', '作者名'

add('黒帯：全面画像＋下にタイトル', [
    img(0, 0, W, 140), box(0, 140, W, H - 140, f=INK),
    txt(14, 140, 220, H - 140, TT, 40, c=WH, wt=700, an='ctr'),
    txt(234, 140, W - 248, H - 140, ET + '\n' + AU, 18, c=WH, al='e', an='ctr', ld=140)])
add('色の箱：全面画像＋左下に', [
    img(0, 0, W, H), box(14, 104, 170, 72, f='k'),
    txt(24, 110, 150, 40, TT, 36, c='on@k', wt=700, an='ctr'),
    txt(24, 150, 150, 20, ET + '　' + AU, 14, c='on@k', an='ctr')])
add('白い箱：全面画像＋中央に', [
    img(0, 0, W, H), box(W / 2 - 100, H / 2 - 36, 200, 72, f=WH),
    txt(W / 2 - 96, H / 2 - 32, 192, 44, TT, 40, wt=700, al='c', an='ctr'),
    txt(W / 2 - 96, H / 2 + 12, 192, 20, ET, 18, c=GRY, al='c', an='ctr')])
add('白帯：全面画像＋上にタイトル', [
    img(0, 44, W, H - 44),
    txt(14, 0, 210, 44, TT, 36, wt=700, an='ctr'),
    txt(224, 0, W - 238, 44, AU, 18, al='e', an='ctr')])
add('白文字：全面画像に重ねる', [
    img(0, 0, W, H),
    txt(16, 120, W - 32, 54, TT, 60, c=WH, wt=700, an='b', ld=105),
    txt(16, 14, W - 32, 14, ET + '　／　' + AU, 14, c=WH)],
    note='絵の明るい部分に文字が重なるときは、文字色を黒に変えるか、上の「白い箱」型を使う')
add('色の縦帯：右にタイトル', [
    img(0, 0, 232, H), box(232, 0, W - 232, H, f='k'),
    txt(244, 20, W - 256, 100, TT, 36, c='on@k', wt=700, ld=115),
    txt(244, H - 50, W - 256, 36, ET + '\n' + AU, 18, c='on@k', an='b', ld=140)])
add('左に文字：右2/3に絵', [
    img(112, 0, W - 112, H),
    txt(12, 20, 92, 110, TT, 32, wt=700, ld=115),
    txt(12, H - 50, 92, 36, ET + '\n' + AU, 14, an='b', ld=140)])
add('上に文字：下半分に絵', [
    txt(14, 14, W - 28, 50, TT, 48, wt=700, an='ctr'),
    txt(14, 64, W - 28, 20, ET + '　' + AU, 18, c=GRY, an='ctr'),
    img(0, 92, W, H - 92)])
add('3枚＋帯：中央にタイトル', grid(3, 1, h=H) + [
    box(0, H / 2 - 30, W, 60, f=WH),
    txt(14, H / 2 - 30, W - 28, 40, TT, 40, wt=700, al='c', an='ctr'),
    txt(14, H / 2 + 8, W - 28, 20, ET + '　' + AU, 14, c=GRY, al='c', an='ctr')])
add('丸い絵：下にタイトル', [
    img(W / 2 - 58, 12, 116, 116, CIRCLE),
    txt(14, 134, W - 28, 32, TT, 36, wt=700, al='c', an='ctr'),
    txt(14, 166, W - 28, 16, ET + '　' + AU, 14, c=GRY, al='c', an='ctr')])
add('白地：大きなタイトルだけ', [
    txt(14, 40, W - 28, 80, TT, 72, wt=700, al='c', an='ctr', ld=105),
    txt(14, 126, W - 28, 20, ET, 20, c=GRY, al='c', an='ctr'),
    txt(14, 160, W - 28, 16, AU, 14, al='c', an='ctr')])
add('黒地：大きなタイトルだけ', [
    txt(14, 40, W - 28, 80, TT, 72, c=WH, wt=700, al='c', an='ctr', ld=105),
    txt(14, 126, W - 28, 20, ET, 20, c=WH, al='c', an='ctr'),
    txt(14, 160, W - 28, 16, AU, 14, c=WH, al='c', an='ctr')], bg=INK)
add('色地：左下にタイトル', [
    txt(16, 80, W - 32, 70, TT, 64, c='on@k', wt=700, an='b', ld=105),
    box(16, 156, 60, 1.2, f='on@k'),
    txt(16, 162, W - 32, 18, ET + '　' + AU, 18, c='on@k', an='ctr')], bg='k')
add('英題：大きな英題＋日本語', [
    txt(14, 24, W - 28, 90, 'ENGLISH\nTITLE', 66, c='k', wt=700, ld=95, tr=20),
    txt(14, 128, W - 28, 30, TT, 28, wt=700, an='ctr'),
    txt(14, 160, W - 28, 16, AU, 14, c=GRY, an='ctr')])
add('作品データ：タイトル＋罫線', [
    txt(14, 30, W - 28, 70, TT, 60, wt=700, al='c', an='ctr'),
    txt(14, 100, W - 28, 20, ET, 20, al='c', an='ctr'),
    box(60, 138, W - 120, 0.5, f=INK), box(60, 168, W - 120, 0.5, f=INK),
    txt(60, 138, W - 120, 30, '2026　｜　3分20秒　｜　手描きアニメーション　｜　' + AU, 14, al='c', an='ctr')])
add('フィルム：上にタイトル', film_h(4, False, fh=76, y0=60) + [
    txt(14, 8, W - 28, 30, TT, 28, c=WH, wt=700, an='ctr'),
    txt(14, 158, W - 28, 24, ET + '　' + AU, 14, c=WH, an='ctr')], bg=INK)
add('縦長の絵：右にタイトルと線', [
    img(0, 0, 120, H),
    box(136, 40, 4, 76, f='k'),
    txt(150, 40, W - 164, 50, TT, 44, wt=700, an='ctr'),
    txt(150, 92, W - 164, 24, ET, 20, c=GRY, an='ctr'),
    txt(150, H - 36, W - 164, 20, AU, 18, an='ctr')])
add('シネスコ：下の黒帯にタイトル', [
    img(0, 24, W, 141.7),
    txt(14, 165.7, 220, 24.8, TT, 24, c=WH, wt=700, an='ctr'),
    txt(234, 165.7, W - 248, 24.8, AU, 14, c=WH, al='e', an='ctr')], bg=INK)
add('2枚＋箱：境目にタイトル', [
    img(0, 0, W / 2, H), img(W / 2, 0, W / 2, H),
    box(W / 2 - 80, H - 58, 160, 40, f=INK),
    txt(W / 2 - 76, H - 58, 152, 40, TT, 32, c=WH, wt=700, al='c', an='ctr')])
add('章扉：大きな番号＋見出し', [
    txt(14, 20, 140, 110, '01', 120, c='k', wt=700, f=MONO, ld=90),
    txt(14, 132, W - 28, 32, '章の見出し', 36, wt=700, an='ctr'),
    txt(14, 164, W - 28, 18, 'Chapter Title', 18, c=GRY, an='ctr'),
    img(200, 0, W - 200, 128)])

# =====================================================================
# 連絡先
# =====================================================================
add = pin('contact', '連絡先')
MAIL, WEB, SNS = 'mail@example.com', 'https://example.com', '@account'

def rows(x, y, w, items, lz=14, vz=20, lc='k', step=24, lw=56, vc=INK):
    out = []
    for i, (l, v) in enumerate(items):
        out.append(txt(x, y + i * step, lw, step, l, lz, c=lc, an='ctr'))
        out.append(txt(x + lw, y + i * step, w - lw, step, v, vz, c=vc, an='ctr'))
    return out
LIST = [('Mail', MAIL), ('Website', WEB), ('Instagram', SNS), ('X', SNS)]

add('中央揃え：名前と連絡先', [
    txt(14, 28, W - 28, 36, AU, 40, wt=700, al='c', an='ctr'),
    txt(14, 66, W - 28, 18, 'Animation Director', 18, c=GRY, al='c', an='ctr'),
    txt(14, 100, W - 28, 70, MAIL + '\n' + WEB + '\nInstagram　' + SNS, 20, al='c', an='ctr', ld=150,
        ps=para((1, 0, 'k'), (1, 0), (1, 0)))])
add('丸い写真：右に一覧', [
    img(24, (H - 100) / 2, 100, 100, CIRCLE),
    txt(150, 28, W - 164, 30, AU, 32, wt=700, an='ctr')] + rows(150, 72, W - 164, LIST))
add('左に絵：右に連絡先', [
    img(0, 0, W / 2, H),
    txt(W / 2 + 16, 24, W / 2 - 30, 30, '連絡先', 32, wt=700, an='ctr')] + rows(W / 2 + 16, 70, W / 2 - 30, LIST, vz=18))
add('白い箱：全面画像＋連絡先', [
    img(0, 0, W, H), box(W - 168, 20, 150, H - 40, f=WH),
    txt(W - 156, 30, 126, 26, AU, 28, wt=700, an='ctr'),
    txt(W - 156, 62, 126, 104, 'Mail\n' + MAIL + '\nWebsite\n' + WEB + '\nInstagram\n' + SNS, 18, ld=150, an='ctr',
        ps=para((14 / 18, 0, 'k'), (1, 0), (14 / 18, 0, 'k'), (1, 0), (14 / 18, 0, 'k'), (1, 0)))])
add('お礼：下に連絡先', [
    txt(14, 30, W - 28, 80, 'ありがとうございました', 54, wt=700, al='c', an='ctr'),
    box(W / 2 - 30, 120, 60, 1.2, f='k'),
    txt(14, 134, W - 28, 40, MAIL + '　／　' + WEB, 20, al='c', an='ctr')])
add('QR3つ：並べる', [
    txt(14, 14, W - 28, 30, '連絡先', 32, wt=700, an='ctr')] + sum([[
    img(34 + i * 98, 56, 74, 74),
    txt(14 + i * 98, 136, 114, 14, l, 14, c='k', al='c', an='ctr'),
    txt(14 + i * 98, 152, 114, 16, v, 18, al='c', an='ctr')] for i, (l, v) in enumerate([('Website', 'example.com'), ('Instagram', SNS), ('X', SNS)])], []))
add('メール：黒地に大きく', [
    txt(14, 30, W - 28, 20, 'Contact', 20, c='k', an='ctr'),
    txt(14, 60, W - 28, 60, MAIL, 48, c=WH, wt=700, an='ctr'),
    txt(14, 140, W - 28, 30, WEB + '　Instagram ' + SNS, 18, c=WH, an='ctr')], bg=INK)
add('色地：名前と連絡先', [
    txt(16, 24, W - 32, 50, AU, 48, c='on@k', wt=700, an='ctr'),
    box(16, 82, W - 32, 0.6, f='on@k'),
    txt(16, 94, 150, 80, 'Mail\n' + MAIL + '\nWebsite\n' + WEB, 20, c='on@k', ld=150, ps=para((0.7, 0), (1, 0), (0.7, 0), (1, 0))),
    txt(176, 94, W - 192, 80, 'Instagram\n' + SNS + '\nX\n' + SNS, 20, c='on@k', ld=150, ps=para((0.7, 0), (1, 0), (0.7, 0), (1, 0)))], bg='k')
add('表：罫線で区切る', [
    txt(14, 14, W - 28, 30, '連絡先', 32, wt=700, an='ctr')] + sum([[
    box(14, 54 + i * 26, W - 28, 0.5, f=LN),
    txt(14, 54 + i * 26, 90, 26, l, 14, c=GRY, an='ctr'),
    txt(104, 54 + i * 26, W - 118, 26, v, 20, an='ctr')] for i, (l, v) in enumerate([('名前', AU)] + LIST)], []) + [
    box(14, 54 + 5 * 26, W - 28, 0.5, f=LN)])
add('URL：大きく＋QRコード', [
    txt(14, 40, W - 120, 20, 'Website', 18, c='k', an='ctr'),
    txt(14, 62, W - 120, 50, 'example.com', 54, wt=700, an='ctr'),
    txt(14, 130, W - 120, 30, MAIL + '　Instagram ' + SNS, 18, c=GRY, an='ctr'),
    img(W - 98, 52, 76, 76)])
add('絵3枚：下に連絡先', grid(3, 1, h=104) + [
    txt(14, 112, 140, 30, AU, 28, wt=700, an='ctr'),
    txt(14, 144, 140, 36, 'Animation Director', 18, c=GRY),
    txt(160, 112, W - 174, 70, MAIL + '\n' + WEB + '\nInstagram　' + SNS, 18, ld=140)])
add('SNS：アカウントを大きく', [
    txt(14, 20, W - 28, 20, 'Instagram', 20, c='k', al='c', an='ctr'),
    txt(14, 44, W - 28, 60, SNS, 60, wt=700, al='c', an='ctr'),
    box(W / 2 - 30, 116, 60, 0.6, f=LN),
    txt(14, 126, W - 28, 44, 'X　' + SNS + '\n' + MAIL, 20, al='c', an='ctr', ld=150)])
add('黒地：丸い写真＋一覧', [
    img(24, (H - 100) / 2, 100, 100, CIRCLE),
    txt(150, 28, W - 164, 30, AU, 32, c=WH, wt=700, an='ctr')] + rows(150, 72, W - 164, LIST, vc=WH), bg=INK)
add('色の帯：上に絵、下に連絡先', [
    img(0, 0, W, 100), box(0, 100, W, H - 100, f='k'),
    txt(16, 108, 150, 74, AU + '\nAnimation Director', 28, c='on@k', wt=700, an='ctr', ld=130, ps=para((1, 1), (18 / 28, 0))),
    txt(176, 108, W - 192, 74, MAIL + '\n' + WEB + '\nInstagram　' + SNS, 18, c='on@k', an='ctr', ld=150)])
add('右に絵：左に名前と一覧', [
    img(W - 120, 0, 120, H),
    txt(16, 24, W - 152, 46, AU, 44, wt=700, an='ctr'),
    box(16, 76, 40, 3, f='k')] + rows(16, 90, W - 152, LIST))


def main():
    out = sys.argv[1]
    d = json.load(open(out))
    ids = {p['id'] for p in PINS}
    rest = [p for p in d['pins'] if p['id'] not in ids]
    k = next((i + 1 for i, p in enumerate(rest) if p['id'] == 'own'), 0)
    d['pins'] = rest[:k] + PINS + rest[k:]
    open(out, 'w').write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    for p in PINS: print(p['id'], p['name'], len(p['slides']))

main()
