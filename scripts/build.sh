#!/bin/sh
# src/app.html（Artifact公開用の本文）を、単体で開けるHTMLに包んで dist/index.html に出力する
# あわせてインストール用（PWA）の manifest・service worker・アイコンを dist に置く
set -e
cd "$(dirname "$0")/.."
mkdir -p dist
{
  printf '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
  printf '<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#E8EFEA" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#172120" media="(prefers-color-scheme: dark)">\n'
  printf '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
  printf '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="HonHon">\n'
  printf '<script>if("serviceWorker" in navigator)addEventListener("load",function(){navigator.serviceWorker.register("/sw.js")})</script>\n'
  printf '</head><body>\n'
  cat src/app.html
  printf '\n</body></html>\n'
} > dist/index.html
cp src/pwa/*.png src/pwa/manifest.webmanifest dist/
BUILD=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
sed "s/__BUILD__/$BUILD/" src/pwa/sw.js > dist/sw.js
printf '/sw.js\n  Cache-Control: no-cache\n' > dist/_headers
echo "dist/index.html"
