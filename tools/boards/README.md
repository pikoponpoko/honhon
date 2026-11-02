# スライドのひな型データの作り方

## ボードのひな型（src/boards.json）

Pinterestボードを再現したスライド（共有フォルダ `presentation-templates/ボード全種/`）を、新規スライドの「デザイン」と属性の「後ろに追加」で使うデータにする。

1. 生成スクリプトをキーカラー赤・対比色青で実行する（色の役割を見分けるため）。画像フォルダは渡さない（画像は空の枠になる）
   - ピン01〜09：`ピン01-09/tools/run.py g1.pptx --key=FF0000 --sub=0000FF`
   - ピン10〜18：`tools/board_p10_18.py g2.pptx --key=FF0000 --sub=0000FF`
   - ピン19〜27：`tools/board_19-27.py g3.pptx --key=FF0000 --sub=0000FF`
2. `python3 tools/boards/convert.py src/boards.json g1.pptx g2.pptx g3.pptx`

赤系の色はキーカラー、青系は対比色、黒・灰・白は固定色として保存する。飾りのPNG（水玉・筆の塗り）もアプリで画素ごとにキーカラーへ塗り直す。

`boards.json` は本体とは別ファイルで、スライドの新規作成・属性パネルを開いたときに読み込む。`scripts/build.sh` が `dist/` にコピーする。Artifactのお試し版に載せるときは `files` に `boards.json` を加える。

## 構成のひな形（自己紹介・作品紹介 × 5〜20分）

`presentation-templates/tools/content.py` から作る。

```
python3 tools/boards/flows.py /mnt/project-files/presentation-templates/tools
```

出力の `/*FLOWS-DUR*/…/*FLOWS-DUR-END*/` と `/*FLOW_NOTES-DUR*/…/*FLOW_NOTES-DUR-END*/` を `src/app.html` の同じ印の範囲と置き換える。

## 自分の企画書・面談資料・発表資料（作者のPowerPoint資料のデザイン）

`tools/boards/own.py` に元資料の配置（mm）・文字サイズ・書体（游ゴシック）を写してある。中身は差し替え用の文字と空の画像枠だけで、元資料の文章や画像は入れない。

```
python3 tools/boards/own.py src/boards.json
```

`boards.json` の先頭に「自分の企画書」（id `own`）「自分の面談資料」（`own_meet`、地はキーカラーの淡色）「自分の発表資料」（`own_talk`）を入れ直す。各スライドの `r` は役割（cover/sec/text/list/table/img/imgs/person/profile/quote/video/end）。ボードを作り直したときは convert.py のあとにもう一度実行する。
