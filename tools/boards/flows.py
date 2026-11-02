# -*- coding: utf-8 -*-
"""過去のパワポから作ったプレゼンひな型（presentation-templates/tools/content.py）を、
アプリの「構成のひな形」（FLOWS・FLOW_NOTES）の書き方に変換して標準出力に出す。

python3 tools/boards/flows.py /mnt/project-files/presentation-templates/tools > /tmp/flows.js
出力を src/app.html の「/*FLOWS-DUR*/」と「/*FLOW_NOTES-DUR*/」の間に貼る（tools/boards/README.md）。
"""
import sys, os, json
sys.path.insert(0, sys.argv[1])
import content

TAG = {'cover': '表紙画像', 'pic_text': '画像', 'video': '全面画像', 'photo_cap': '全面画像', 'photo': '全面画像',
       'pic4': '画像6枚', 'pic6': '画像6枚', 'statement': '一文左', 'number': '数字左', 'section': '区切り番号',
       'pic2': '画像大小', 'pic_pair': '画像大小', 'pic_vert': '画像大', 'content': '', 'table': '', 'col3': 'カード', 'contact': ''}

def block(k, story_no):
    b = content.B[k]; lay, t = b[0], b[1]
    title = t.get('title') or ('あらすじ%d' % story_no if k.startswith('story') else '画像')
    tag = TAG[lay]
    lines = [('[%s] ' % tag if tag else '') + title]
    if lay == 'cover': lines += t.get('sub', '').split('\n')
    elif lay == 'number': lines += [t.get('num', '00'), t.get('body', '')]
    elif lay == 'pic_vert': lines.append(t.get('body', ''))
    elif lay == 'contact': lines = ['連絡先'] + ['・' + x for x in [t.get('title', '')] + t.get('body', '').split('\n') if x]
    elif lay == 'col3': lines += ['・' + t[h] for h in ('head1', 'head2', 'head3')]
    elif lay == 'pic2': lines.append(t.get('cap1', ''))
    elif lay == 'table' and len(b) > 3:
        rows = b[3]
        for r in rows[1:]:
            if r[0]: lines.append('・' + r[0])
        if len(lines) == 1: lines.append('・' + '／'.join(rows[0]))
    if lay in ('content', 'table') and len(lines) == 1: lines.append('・項目')   # 本文のない行は区切りと見なされるので項目を置く
    return '\n'.join(l for l in lines if l is not None)

flows, notes = [], []
for (kind, mins), seq in content.SEQ.items():
    name = f'{kind}（{mins}分）'
    slides, tot = content.deck(seq, f'{mins}分')
    blocks = []; sn = 0
    for k, _ in seq:
        if k.startswith('story'): sn += 1
        blocks.append(block(k, sn))
    flows.append('%s:%s' % (json.dumps(name, ensure_ascii=False), json.dumps('\n\n'.join(blocks), ensure_ascii=False)))
    notes.append('%s:%s' % (json.dumps(name, ensure_ascii=False), json.dumps([s['note'] for s in slides], ensure_ascii=False)))
print('/*FLOWS-DUR*/' + ',\n'.join(flows) + ',/*FLOWS-DUR-END*/')
print('/*FLOW_NOTES-DUR*/' + ',\n'.join(notes) + ',/*FLOW_NOTES-DUR-END*/')
