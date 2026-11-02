# -*- coding: utf-8 -*-
"""ボード再現スライド（python-pptx で作った PPTX）を、アプリのスライドひな型データ src/boards.json に変換する。

python3 tools/boards/convert.py 出力.json 入力1.pptx [入力2.pptx ...]

入力は生成スクリプトを --key=FF0000 --sub=0000FF で実行したもの（tools/boards/README.md）。
赤系の色はキーカラー、青系の色は対比色として役割に置き換えるので、アプリでキーカラーを変えると追従する。
  'k' / 'k2'            キーカラー／対比色
  'k@t@LL'              キーカラーを灰色 LL（16進2桁）に t の割合で混ぜた色（ff なら淡色、00 なら濃色）
  'on@<役割>'           その色の面の上に置く文字（白か黒のうち読みやすい方）
  '#rrggbb'             固定色（黒・灰・白）
"""
import sys, re, math, json, io, base64, zipfile, hashlib
from lxml import etree
from PIL import Image

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
A = '{%s}' % NS['a']; P = '{%s}' % NS['p']; R = '{%s}' % NS['r']
EMU = 36000.0  # mm

def mm(v): return round(int(v) / EMU, 1)

# ---------- 色 → 役割 ----------
def role(hexs):
    h = hexs.upper()
    if h == 'EC0000': return 'k2'
    if h == '1D8B56': return 'k'
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if r == g == b: return '#' + h.lower()
    def fam(main, o1, o2):
        if abs(o1 - o2) > 2 or main < o1: return None
        t = 1 - (main - o1) / 255.0   # 灰色の割合
        if t < 0.004: return ''
        L = min(255, round(o1 / t)) if t > 0 else 0
        return '@%s@%02x' % (round(t, 3), L)
    k = fam(r, g, b)
    if k is not None: return 'k' + k
    k = fam(b, r, g)
    if k is not None: return 'k2' + k
    return '#' + h.lower()

def hexof(el):
    if el is None: return None
    s = el.find(A + 'srgbClr')
    if s is not None: return s.get('val')
    return None

def fill_of(spPr):
    if spPr is None: return None
    if spPr.find(A + 'noFill') is not None: return None
    sf = spPr.find(A + 'solidFill')
    h = hexof(sf)
    return role(h) if h else None

def line_of(spPr):
    ln = spPr.find(A + 'ln') if spPr is not None else None
    if ln is None or ln.find(A + 'noFill') is not None: return None
    h = hexof(ln.find(A + 'solidFill'))
    if not h: return None
    o = {'s': role(h), 'sw': round(int(ln.get('w', '12700')) / EMU, 2)}
    d = ln.find(A + 'prstDash')
    if d is not None and d.get('val') != 'solid': o['dash'] = d.get('val')
    if ln.get('cap') == 'rnd': o['cap'] = 1
    return o

# ---------- 形 → パス（枠を 0〜1000 にした座標） ----------
K = 0.5523
def P2(x, y): return '%d %d' % (round(x), round(y))

def ell(cx, cy, rx, ry, rev=False):
    k = K
    if not rev:
        return ('M%s C%s %s %s C%s %s %s C%s %s %s C%s %s %sZ' % (
            P2(cx + rx, cy), P2(cx + rx, cy + ry * k), P2(cx + rx * k, cy + ry), P2(cx, cy + ry),
            P2(cx - rx * k, cy + ry), P2(cx - rx, cy + ry * k), P2(cx - rx, cy),
            P2(cx - rx, cy - ry * k), P2(cx - rx * k, cy - ry), P2(cx, cy - ry),
            P2(cx + rx * k, cy - ry), P2(cx + rx, cy - ry * k), P2(cx + rx, cy)))
    return ('M%s C%s %s %s C%s %s %s C%s %s %s C%s %s %sZ' % (
        P2(cx + rx, cy), P2(cx + rx, cy - ry * k), P2(cx + rx * k, cy - ry), P2(cx, cy - ry),
        P2(cx - rx * k, cy - ry), P2(cx - rx, cy - ry * k), P2(cx - rx, cy),
        P2(cx - rx, cy + ry * k), P2(cx - rx * k, cy + ry), P2(cx, cy + ry),
        P2(cx + rx * k, cy + ry), P2(cx + rx, cy + ry * k), P2(cx + rx, cy)))

def poly(pts, close=True):
    return 'M' + 'L'.join(P2(x, y) for x, y in pts) + ('Z' if close else '')

def arcpts(cx, cy, rx, ry, a0, a1, n=None):
    """a0→a1（度、時計回り＝y下向き）"""
    n = n or max(6, int(abs(a1 - a0) / 6))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

def rrect(w, h, rs):
    """rs=[左上,右上,右下,左下] の半径（mm）。0〜1000 の座標で返す"""
    sx, sy = 1000 / w, 1000 / h
    pts = []
    corners = [(rs[0], 0, 0, 180), (rs[1], w, 0, 270), (rs[2], w, h, 0), (rs[3], 0, h, 90)]
    out = ''
    for i, (r, x, y, a) in enumerate(corners):
        cx = x + (r if x == 0 else -r); cy = y + (r if y == 0 else -r)
        if r <= 0: seg = [(x, y)]
        else: seg = arcpts(cx, cy, r, r, a, a + 90, 8)
        pts += seg
    return poly([(x * sx, y * sy) for x, y in pts])

def adjs(el):
    out = []
    av = el.find('.//' + A + 'avLst')
    if av is not None:
        for gd in av.findall(A + 'gd'):
            m = re.search(r'val (-?\d+)', gd.get('fmla', ''))
            out.append((gd.get('name'), int(m.group(1)) if m else 0))
    return dict(out)

def preset(prst, w, h, av):
    """主要なプリセット形状を 0〜1000 のパスにする。rect は None"""
    ss = min(w, h)
    def a(name, d): return av.get(name, d)
    X = lambda v: v / w * 1000; Y = lambda v: v / h * 1000
    if prst in ('rect', None): return None
    if prst == 'ellipse': return ell(500, 500, 500, 500)
    if prst == 'roundRect':
        r = ss * a('adj', 16667) / 100000; return rrect(w, h, [r] * 4)
    if prst == 'round2SameRect':
        r1 = ss * a('adj1', 16667) / 100000; r2 = ss * a('adj2', 0) / 100000; return rrect(w, h, [r1, r1, r2, r2])
    if prst == 'parallelogram':
        o = X(ss * a('adj', 25000) / 100000); return poly([(o, 0), (1000, 0), (1000 - o, 1000), (0, 1000)])
    if prst == 'trapezoid':
        o = X(ss * a('adj', 25000) / 100000); return poly([(0, 1000), (o, 0), (1000 - o, 0), (1000, 1000)])
    if prst == 'triangle':
        return poly([(a('adj', 50000) / 100, 0), (1000, 1000), (0, 1000)])
    if prst == 'homePlate':
        dx = X(ss * a('adj', 50000) / 100000); return poly([(0, 0), (1000 - dx, 0), (1000, 500), (1000 - dx, 1000), (0, 1000)])
    if prst == 'rightArrow':
        t = a('adj1', 50000) / 100000 * 1000; dx = X(ss * a('adj2', 50000) / 100000)
        y0, y1 = 500 - t / 2, 500 + t / 2
        return poly([(0, y0), (1000 - dx, y0), (1000 - dx, 0), (1000, 500), (1000 - dx, 1000), (1000 - dx, y1), (0, y1)])
    if prst == 'flowChartDelay':
        return poly([(0, 0), (500, 0)] + arcpts(500, 500, 500, 500, -90, 90, 16) + [(0, 1000)])
    if prst == 'flowChartPunchedCard':
        return poly([(200, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 200)])
    if prst == 'donut':
        dr = ss * a('adj', 25000) / 100000
        return ell(500, 500, 500, 500) + ell(500, 500, 500 - X(dr), 500 - Y(dr), True)
    if prst in ('blockArc', 'chord'):
        if prst == 'chord':
            a0, a1 = a('adj1', 2700000) / 60000, a('adj2', 16200000) / 60000
            if a1 <= a0: a1 += 360
            return poly(arcpts(500, 500, 500, 500, a0, a1))
        a0, a1 = a('adj1', 10800000) / 60000, a('adj2', 0) / 60000
        if a1 <= a0: a1 += 360
        dr = ss * a('adj3', 25000) / 100000
        o = arcpts(500, 500, 500, 500, a0, a1); i = arcpts(500, 500, 500 - X(dr), 500 - Y(dr), a1, a0)
        return poly(o + i)
    if prst in ('star4', 'star5'):
        n = 4 if prst == 'star4' else 5
        ir = a('adj', 12500 if n == 4 else 19098) / 50000 * 500
        pts = []
        for i in range(2 * n):
            ang = -90 + i * 180 / n; r = 500 if i % 2 == 0 else ir
            pts.append((500 + r * math.cos(math.radians(ang)), 500 + r * math.sin(math.radians(ang)) * (1 if n == 4 else 1.05)))
        return poly(pts)
    if prst == 'heart':
        return ('M500 250C500 0 0 0 0 300C0 550 300 750 500 1000C700 750 1000 550 1000 300C1000 0 500 0 500 250Z')
    if prst in ('wedgeEllipseCallout', 'wedgeRectCallout'):
        tx, ty = 500 + a('adj1', -20833) / 100, 500 + a('adj2', 62500) / 100
        ang = math.degrees(math.atan2(ty - 500, tx - 500))
        if prst == 'wedgeEllipseCallout':
            pts = arcpts(500, 500, 500, 500, ang + 10, ang + 350, 60)
            return poly(pts + [(tx, ty)])
        # 四角の吹き出し：先端に近い辺に三角を出す
        bx = min(max(tx, 0), 1000); by = min(max(ty, 0), 1000)
        if by >= 1000: return poly([(0, 0), (1000, 0), (1000, 1000), (650, 1000), (tx, ty), (350, 1000), (0, 1000)])
        if by <= 0: return poly([(0, 0), (350, 0), (tx, ty), (650, 0), (1000, 0), (1000, 1000), (0, 1000)])
        if bx <= 0: return poly([(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 650), (tx, ty), (0, 350)])
        return poly([(0, 0), (1000, 0), (1000, 350), (tx, ty), (1000, 650), (1000, 1000), (0, 1000)])
    if prst in ('wave', 'doubleWave'):
        amp = a('adj1', 12500 if prst == 'wave' else 6250) / 100000 * 1000
        nwave = 1 if prst == 'wave' else 2
        top = [(x, amp + amp * math.sin(-math.pi * 2 * nwave * x / 1000)) for x in range(0, 1001, 25)]
        bot = [(x, 1000 - amp + amp * math.sin(-math.pi * 2 * nwave * x / 1000)) for x in range(1000, -1, -25)]
        return poly(top + bot)
    if prst == 'cloud':
        # 楕円の周りにこぶを並べた雲
        pts = []
        n = 9
        for i in range(n):
            c = -90 + i * 360 / n; d = 360 / n
            mx, my = 500 + 380 * math.cos(math.radians(c + d / 2)), 500 + 360 * math.sin(math.radians(c + d / 2))
            pts += arcpts(mx, my, 160, 150, c + d / 2 - 100, c + d / 2 + 100, 10)
        return poly(pts)
    sys.stderr.write('未対応の形：%s\n' % prst)
    return None

def custgeom(cg):
    out = ''
    for pth in cg.findall('.//' + A + 'path'):
        pw = int(pth.get('w', '1')) or 1; ph = int(pth.get('h', '1')) or 1
        f = lambda pt: P2(int(pt.get('x')) / pw * 1000, int(pt.get('y')) / ph * 1000)
        for c in pth:
            t = etree.QName(c).localname
            pts = c.findall(A + 'pt')
            if t == 'moveTo': out += 'M' + f(pts[0])
            elif t == 'lnTo': out += 'L' + f(pts[0])
            elif t == 'cubicBezTo': out += 'C' + ' '.join(f(p) for p in pts)
            elif t == 'quadBezTo': out += 'Q' + ' '.join(f(p) for p in pts)
            elif t == 'close': out += 'Z'
    return out or None

def flip(d, fh, fv):
    if not (fh or fv) or not d: return d
    nums = iter(re.findall(r'-?\d+', d))
    def rep(m):
        return m.group(0)
    out = []; toks = re.findall(r'[MLCQZ]|-?\d+', d); i = 0; xy = 0
    for t in toks:
        if t.isalpha(): out.append(t); continue
        v = int(t)
        if xy % 2 == 0 and fh: v = 1000 - v
        if xy % 2 == 1 and fv: v = 1000 - v
        out.append(str(v)); xy += 1
    s = ''
    for t in out:
        if t.isalpha(): s += t
        else: s += (t if s and s[-1].isalpha() else ' ' + t)
    return s

def compact(d):
    return re.sub(r' (?=-)', '', d) if d else d

# ---------- 文字 ----------
def font_of(rPr):
    lat = rPr.find(A + 'latin') if rPr is not None else None
    n = lat.get('typeface') if lat is not None else ''
    if 'Consolas' in n or 'Mono' in n: return 'Noto Sans Mono', None
    if 'Times' in n: return 'Noto Serif JP', None
    if 'Light' in n: return None, 300
    return None, None

def text_item(sp, box):
    tb = sp.find(P + 'txBody')
    paras = tb.findall(A + 'p')
    lines = []; runs = []
    for p_ in paras:
        rs = p_.findall(A + 'r')
        lines.append(''.join((r.findtext(A + 't') or '') for r in rs))
        runs.append(rs)
    txt = '\n'.join(lines)
    if not txt.strip(): return None
    allr = [r for rs in runs for r in rs if (r.findtext(A + 't') or '').strip()]
    # 文字数の多い色を代表色にする
    cnt = {}
    for r in allr:
        rp = r.find(A + 'rPr'); h = hexof(rp.find(A + 'solidFill')) if rp is not None else None
        cnt[h] = cnt.get(h, 0) + len(r.findtext(A + 't') or '')
    col = max(cnt, key=cnt.get) if cnt else '1A1A1A'
    r0 = allr[0].find(A + 'rPr')
    size = int(r0.get('sz', '1800')) / 100
    bold = r0.get('b') == '1'
    fnt, wt = font_of(r0)
    weight = 700 if bold else (wt or 400)
    # PowerPoint は枠からはみ出た文字も描くが、アプリは枠に入らない行を出さない。
    # 字形の違いで行が増えても消えないよう、揃え（上・中央・下）の基準を保ったまま枠を広げる
    box = list(box)
    bp0 = tb.find(A + 'bodyPr')
    an0 = bp0.get('anchor') if bp0 is not None else None
    vert0 = bp0 is not None and bp0.get('vert') in ('eaVert', 'vert')
    k = 2 if vert0 else 3
    ex = max(box[k] * 0.6, size * 0.353 * 1.6)
    if an0 == 'b': box[k - 2] = round(box[k - 2] - ex, 1)
    elif an0 == 'ctr': box[k - 2] = round(box[k - 2] - ex / 2, 1)
    box[k] = round(box[k] + ex, 1)
    o = {'t': 'x', 'b': box, 's': txt, 'z': size, 'c': role(col or '1A1A1A')}
    if weight != 400: o['wt'] = weight
    if fnt: o['f'] = fnt
    if r0.get('i') == '1': o['i'] = 1
    spc = r0.get('spc')
    if spc: o['tr'] = round(int(spc) / 100 / size * 1000)
    bp = tb.find(A + 'bodyPr')
    if bp is not None:
        an = bp.get('anchor')
        if an in ('ctr', 'b'): o['an'] = an
        if bp.get('vert') in ('eaVert', 'vert'): o['v'] = 1
    pPr = paras[0].find(A + 'pPr')
    if pPr is not None:
        al = pPr.get('algn')
        if al == 'ctr': o['al'] = 'c'
        elif al == 'r': o['al'] = 'e'
        ls = pPr.find(A + 'lnSpc/' + A + 'spcPct')
        if ls is not None: o['ld'] = round(int(ls.get('val')) / 1000 * 1.2)
    if 'ld' not in o: o['ld'] = 120
    # 段落ごとの文字サイズ・太さが違うとき
    if len(paras) > 1:
        ps = []
        for rs in runs:
            rr = rs[0].find(A + 'rPr') if rs else None
            z = int(rr.get('sz', str(int(size * 100)))) / 100 if rr is not None else size
            b = 1 if (rr is not None and rr.get('b') == '1') else 0
            q = {'r': round(z / size, 3), 'b': b}
            pc = {}
            for r in rs:
                rp = r.find(A + 'rPr'); h = hexof(rp.find(A + 'solidFill')) if rp is not None else None
                if (r.findtext(A + 't') or '').strip(): pc[h] = pc.get(h, 0) + len(r.findtext(A + 't'))
            if pc:
                h = max(pc, key=pc.get)
                if h and h != col: q['cr'] = role(h)
            ps.append(q)
        if any(q['r'] != 1 or bool(q['b']) != bold or 'cr' in q for q in ps): o['ps'] = ps
    return o

# ---------- 画像（生成された飾り） ----------
IMGS = {}
def gen_image(blob):
    im = Image.open(io.BytesIO(blob)).convert('RGBA')
    m = max(im.size)
    if m > 320: im = im.resize((max(1, round(im.width * 320 / m)), max(1, round(im.height * 320 / m))), Image.LANCZOS)
    q = im.quantize(colors=48, method=Image.FASTOCTREE)
    bio = io.BytesIO(); q.save(bio, 'PNG', optimize=True)
    data = bio.getvalue()
    key = hashlib.sha1(data).hexdigest()[:10]
    IMGS[key] = 'data:image/png;base64,' + base64.b64encode(data).decode()
    return key

# ---------- スライド ----------
def xfrm_of(sp):
    x = sp.find('.//' + A + 'xfrm')
    off, ext = x.find(A + 'off'), x.find(A + 'ext')
    box = [mm(off.get('x')), mm(off.get('y')), mm(ext.get('cx')), mm(ext.get('cy'))]
    return box, int(x.get('rot', '0')) / 60000, x.get('flipH') == '1', x.get('flipV') == '1'

def conv_slide(z, path, rels):
    root = etree.fromstring(z.read(path))
    bg = root.find('.//' + P + 'bg')
    bgc = role(hexof(bg.find('.//' + A + 'solidFill')) or 'FFFFFF') if bg is not None else '#ffffff'
    items = []
    for sp in root.find('.//' + P + 'spTree'):
        tag = etree.QName(sp).localname
        if tag not in ('sp', 'cxnSp', 'pic'): continue
        box, rot, fh, fv = xfrm_of(sp)
        spPr = sp.find(P + 'spPr')
        nv = sp.find('.//' + P + 'cNvPr')
        name = nv.get('name', '') if nv is not None else ''
        pg = spPr.find(A + 'prstGeom'); cg = spPr.find(A + 'custGeom')
        prst = pg.get('prst') if pg is not None else None
        w, h = max(box[2], 0.01), max(box[3], 0.01)
        geo = custgeom(cg) if cg is not None else (('M0 0L1000 1000' if True else None) if prst == 'line' else preset(prst, w, h, adjs(spPr)))
        geo = compact(flip(geo, fh, fv)) if geo else None
        o = None
        if tag == 'pic':
            emb = sp.find('.//' + A + 'blip').get(R + 'embed')
            o = {'t': 'g', 'b': box, 'img': gen_image(z.read(rels[emb]))}
            if geo: o['g'] = geo
        elif name == '画像':
            o = {'t': 'i', 'b': box}
            if geo: o['g'] = geo
        else:
            fl = fill_of(spPr); ln = line_of(spPr)
            if fl or ln:
                o = {'t': 'r', 'b': box}
                if fl: o['f'] = fl
                if ln: o.update(ln)
                if geo: o['g'] = geo
                if prst == 'line' or (cg is not None and not fl): o['open'] = 1
            if tag == 'sp' and sp.find(P + 'txBody') is not None:
                t = text_item(sp, box)
                if t:
                    if rot: t['rot'] = round(rot, 1)
                    if o:
                        if rot: o['rot'] = round(rot, 1)
                        items.append(o); o = None
                    items.append(t); continue
        if o:
            if rot: o['rot'] = round(rot, 1)
            items.append(o)
    # 色の面の上に置いた白・黒の文字は、面の色に合わせて白／黒を選ぶ
    for i, t in enumerate(items):
        if t['t'] != 'x' or t['c'] not in ('#ffffff', '#1a1a1a'): continue
        cx, cy = t['b'][0] + t['b'][2] / 2, t['b'][1] + t['b'][3] / 2
        for s in reversed(items[:i]):
            if s['t'] == 'r' and s.get('f') and s['b'][0] <= cx <= s['b'][0] + s['b'][2] and s['b'][1] <= cy <= s['b'][1] + s['b'][3]:
                if s['f'].startswith('k'): t['c'] = 'on@' + s['f']
                break
        else:
            if bgc.startswith('k'): t['c'] = 'on@' + bgc
    return bgc, items

def notes_of(z, spath):
    rp = spath.replace('slides/', 'slides/_rels/') + '.rels'
    rels = {}
    if rp in z.namelist():
        for r in etree.fromstring(z.read(rp)):
            tgt = r.get('Target')
            full = tgt.replace('../', 'ppt/') if tgt.startswith('../') else 'ppt/slides/' + tgt
            rels[r.get('Id')] = full
    note = ''
    for k, v in rels.items():
        if 'notesSlide' in v:
            nr = etree.fromstring(z.read(v))
            for sp in nr.iter(P + 'sp'):
                ph = sp.find('.//' + P + 'ph')
                if ph is not None and ph.get('type') == 'body':
                    note = '\n'.join(''.join(t.text or '' for t in p_.iter(A + 't')) for p_ in sp.iter(A + 'p'))
    return rels, note

PIN_NAMES = {'p1': 'ポートフォリオ', 'p2': '色の見出し', 'p3': '手描き線', 'p4': '冊子のページ', 'p5': '線画', 'p6': '方眼と帯',
             'p7': 'モノクロ写真と手描き線', 'p8': '図形', 'p9': '帯と番号', 'p10': '大きな英題', 'p11': '大きな小文字', 'p12': '写真アルバム',
             'p13': '数字と縦長画像', 'p14': '巨大な見出し', 'p15': '波形の枠', 'p16': '線画と色の塊', 'p17': '見出しと画像', 'p18': '1色刷り',
             'p19': '水玉', 'p20': '手描きの曲線', 'p21': '手描き枠', 'n1': '巨大な数字', 'n2': '筆の色面', 'n3': '黒地と手描き文字',
             'n4': '筆記体', 'n5': 'ガイドライン', 'n6': '章扉'}

def main():
    out, files = sys.argv[1], sys.argv[2:]
    pins = {}; order = []
    for f in files:
        z = zipfile.ZipFile(f)
        pres = etree.fromstring(z.read('ppt/presentation.xml'))
        prels = {r.get('Id'): 'ppt/' + r.get('Target') for r in etree.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
        for sid in pres.find(P + 'sldIdLst'):
            spath = prels[sid.get(R + 'id')]
            rels, note = notes_of(z, spath)
            bg, items = conv_slide(z, spath, rels)
            ls = note.split('\n')
            m = re.search(r'【(.*?)】', note)
            title = m.group(1) if m else ''
            pm = re.match(r'([pPnN]\d+)', title)
            pid = pm.group(1).lower() if pm else 'x'
            name = re.sub(r'^[pPnN]\d+(-\d+)?\s*', '', title)
            name = re.sub(r'^\d+/\d+\s*', '', name)
            name = re.sub(r'^\S+(\s\S+)?\s\d{2}\s', '', name)
            body = '\n'.join(l for l in ls if not l.startswith('色：') and not l.startswith('【') and not l.startswith('元ピン') and not l.startswith('参考：'))
            if pid not in pins: pins[pid] = []; order.append(pid)
            sl = {'n': name, 'bg': bg, 'it': items}
            if body.strip(): sl['note'] = body.strip()
            pins[pid].append(sl)
    data = {'v': 1, 'pins': [{'id': p, 'name': PIN_NAMES.get(p, p), 'slides': pins[p]} for p in order], 'img': IMGS}
    s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    open(out, 'w').write(s)
    print(out, len(s) // 1024, 'KB', {p: len(pins[p]) for p in order})

main()
