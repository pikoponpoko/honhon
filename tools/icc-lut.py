# Japan Color 2001 Coated（Adobe の ICC プロファイル）から、src/app.html に埋め込む変換表を作る
# 使い方: python3 tools/icc-lut.py JapanColor2001Coated.icc > lut.js
#   プロファイルは Adobe の ICC Profiles（Windows/Mac 版）に含まれる。リポジトリには入れない
#   出力の2行を src/app.html の「JC_N1」で始まる行と置き換える
from PIL import Image, ImageCms
import base64, sys, itertools
jc = ImageCms.getOpenProfile(sys.argv[1])
srgb = ImageCms.createProfile('sRGB')
P = ImageCms.Intent.PERCEPTUAL; RC = ImageCms.Intent.RELATIVE_COLORIMETRIC
t1 = ImageCms.buildTransform(srgb, jc, 'RGB', 'CMYK', renderingIntent=P)
t2 = ImageCms.buildTransform(jc, srgb, 'CMYK', 'RGB', renderingIntent=RC, flags=ImageCms.Flags.BLACKPOINTCOMPENSATION)
N1 = 17; N2 = 11
def g(n): return [round(i * 255 / (n - 1)) for i in range(n)]
# RGB->CMYK, order r major, then g, then b
px = [(r, gg, b) for r in g(N1) for gg in g(N1) for b in g(N1)]
im = Image.new('RGB', (len(px), 1)); im.putdata(px)
out = ImageCms.applyTransform(im, t1)
lut1 = bytes(v for p in out.getdata() for v in p)
px2 = [(c, m, y, k) for c in g(N2) for m in g(N2) for y in g(N2) for k in g(N2)]
im2 = Image.new('CMYK', (len(px2), 1)); im2.putdata(px2)
out2 = ImageCms.applyTransform(im2, t2)
lut2 = bytes(v for p in out2.getdata() for v in p)
sys.stdout.write(
    f"/* Japan Color 2001 Coated（Adobe）のICCプロファイルから littleCMS で作った変換表。sRGB→CMYK（知覚的）{N1}³格子、CMYK→sRGB（相対的・黒点補正）{N2}⁴格子。tools/icc-lut.py で再生成 */\n"
    f"const JC_N1={N1},JC_N2={N2},JC_RGB2CMYK='{base64.b64encode(lut1).decode()}',JC_CMYK2RGB='{base64.b64encode(lut2).decode()}';\n")
