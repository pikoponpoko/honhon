#!/usr/bin/env python3
"""縦書き字形の表（src/app.html の VG_DATA）を作る。

HarfBuzz（uharfbuzz、MIT）で同梱フォントを縦方向（ttb、vert）に組み、
約物・小書きの仮名・長音などの縦書き用字形とその位置を、1字＝1000の座標で書き出す。
横組みの字形を回転・反転・平行移動しただけの字形は向きと位置だけ、それ以外は輪郭（SVGパス）を持つ。
プロポーショナルなフォント（BIZ UDP）の縦送りは全角の枠に置き直す（始め括弧は下寄せ、終わり括弧・句読点は上寄せ）。

使い方: pip install uharfbuzz
        python3 tools/vert-glyphs.py <フォントのフォルダ>
フォントは Google Fonts のリポジトリ（github.com/google/fonts の ofl/）から取得する:
  notoserifjp/NotoSerifJP[wght].ttf  notosansjp/NotoSansJP[wght].ttf
  shipporimincho/ShipporiMincho-{Regular,Bold}.ttf  bizudpmincho/BIZUDPMincho-{Regular,Bold}.ttf
  bizudpgothic/BIZUDPGothic-{Regular,Bold}.ttf  zenmarugothic/ZenMaruGothic-{Regular,Bold}.ttf
"""
import uharfbuzz as hb, sys, json, os
D=sys.argv[1]
FONTS=[('Noto Serif JP','NotoSerifJP[wght].ttf',{400:None,700:None}),
 ('Noto Sans JP','NotoSansJP[wght].ttf',{300:None,400:None,700:None}),
 ('Shippori Mincho',None,{400:'ShipporiMincho-Regular.ttf',700:'ShipporiMincho-Bold.ttf'}),
 ('BIZ UDPMincho',None,{400:'BIZUDPMincho-Regular.ttf',700:'BIZUDPMincho-Bold.ttf'}),
 ('BIZ UDPGothic',None,{400:'BIZUDPGothic-Regular.ttf',700:'BIZUDPGothic-Bold.ttf'}),
 ('Zen Maru Gothic',None,{400:'ZenMaruGothic-Regular.ttf',700:'ZenMaruGothic-Bold.ttf'})]
E=set('、。，．：；！？‥…―—‐－ー～〜（）「」『』【】〔〕［］｛｝〈〉《》＜＞＝｜＿￣〝〟“”‘’・ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶ←↑→↓')
# 字形の向き（フォント座標 y上向き）。0 は向きそのまま
OPEN=set('「『（〔［｛〈《【〘〖〝‘“｟')
CLOSE=set('」』）〕］｝〉》】〙〗〟’”｠、。，．')
def shift(p,dy):
  # 先頭の相対 m の y をずらす
  import re
  m=re.match(r'm(-?\d+)(?: |(?=-))(-?\d+)',p)
  return 'm%d %d'%(int(m.group(1)),int(m.group(2))+dy)+p[m.end():]
MS=[(1,0,0,1),(0,1,-1,0),(0,-1,1,0),(-1,0,0,-1),(1,0,0,-1),(-1,0,0,1),(0,1,1,0),(0,-1,-1,0)]
class P:
  def __init__(s):s.c=[]
  def moveTo(s,a):s.c.append(('M',[a]))
  def lineTo(s,a):s.c.append(('L',[a]))
  def curveTo(s,*a):s.c.append(('C',list(a)))
  def qCurveTo(s,*a):
    a=list(a)
    for i in range(len(a)-1):
      b=a[i+1] if i==len(a)-2 else ((a[i][0]+a[i+1][0])/2,(a[i][1]+a[i+1][1])/2)
      s.c.append(('Q',[a[i],b]))
  def closePath(s):s.c.append(('Z',[]))
  endPath=closePath
def outline(font,g):
  p=P();font.draw_glyph_with_pen(g,p);return p.c
def shape(font,c,d):
  b=hb.Buffer();b.add_str(c);b.guess_segment_properties();b.direction=d
  hb.shape(font,b,{});return b.glyph_infos[0].codepoint,b.glyph_positions[0]
def rel(cmds,tf):
  # 相対座標のSVGパス。z のあとの現在点は輪郭の始点に戻る
  o=[];cx=cy=0;sx=sy=0
  for k,a in cmds:
    if k=='Z':o.append('z');cx,cy=sx,sy;continue
    q=[tf(*p) for p in a]
    o.append(k.lower()+' '.join('%d %d'%(x-cx,y-cy) for x,y in q))
    cx,cy=q[-1]
    if k=='M':sx,sy=cx,cy
  return ''.join(o).replace(' -','-')
out={}
for name,var,ws in FONTS:
  for w,f in ws.items():
    face=hb.Face(hb.Blob.from_file_path(os.path.join(D,f or var)));font=hb.Font(face);upm=face.upem;k=1000/upm
    if var:font.set_variations({'wght':w})
    m={}
    for u in sorted(face.unicodes):
      c=chr(u)
      if c not in E:continue
      g0,_=shape(font,c,'ltr');g1,p=shape(font,c,'ttb')
      if g0==g1:continue
      adv=-p.y_advance;cyc=-adv/2
      cell=lambda x,y:(round((p.x_offset+x)*k),round(-((p.y_offset+y)-cyc)*k))
      a=outline(font,g0);b=outline(font,g1);ent=None
      A=[q for _,v in a for q in v];B=[q for _,v in b for q in v]
      if A and [x for x,_ in a]==[x for x,_ in b]:
        for i,M in enumerate(MS):
          T=lambda x,y:(M[0]*x+M[1]*y,M[2]*x+M[3]*y)
          q=T(*A[0]);t=(B[0][0]-q[0],B[0][1]-q[1])
          if all(abs(T(ax,ay)[0]+t[0]-bx)<1.5 and abs(T(ax,ay)[1]+t[1]-by)<1.5 for (ax,ay),(bx,by) in zip(A,B)):
            X,Y=cell(*t);ent=[i,X,Y];break
      if ent is None and A and B:
        # 形は同じで位置だけ違う字形（小書きの仮名など）は、外接矩形を合わせて平行移動として扱う
        bb=lambda P:(min(x for x,_ in P),min(y for _,y in P),max(x for x,_ in P),max(y for _,y in P))
        a0,b0=bb(A),bb(B)
        if all(abs((a0[i+2]-a0[i])-(b0[i+2]-b0[i]))<=8*upm/1000 for i in (0,1)) and abs(len(A)-len(B))<=len(A)*0.1:
          X,Y=cell(b0[0]-a0[0],b0[1]-a0[1]);ent=[0,X,Y]
      if ent is None:
        ent=rel(b,cell)
      av=round(adv*k)
      if av!=1000:
        sh=(1000-av)/2*(1 if c in OPEN else -1 if c in CLOSE else 0)
        if isinstance(ent,list):ent[2]=round(ent[2]+sh)
        elif sh:ent='m0 %d'%round(sh)+ent if not ent.startswith('m') else shift(ent,round(sh))
      m[c]=ent
    out[name+'|'+str(w)]=m
    print(name,w,len(m),len(json.dumps(m,ensure_ascii=False,separators=(',',':'))),file=sys.stderr)
APP=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','src','app.html')
t=open(APP,encoding='utf-8').read().split('\n')
i=[j for j,l in enumerate(t) if l.startswith('const VG_DATA=')]
assert len(i)==1,'src/app.html に const VG_DATA= の行がない'
t[i[0]]='const VG_DATA='+json.dumps(out,ensure_ascii=False,separators=(',',':'))+';'
open(APP,'w',encoding='utf-8').write('\n'.join(t))
print('src/app.html を更新しました',file=sys.stderr)
