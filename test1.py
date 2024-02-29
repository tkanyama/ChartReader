from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl
from reportlab.pdfgen import canvas
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import portrait, landscape, A3, A4, A5, A6, B3, B4, B5, B6

in_path = "PDF/構造図テストデータのコピー.pdf"
out_path = "PDF_OUTPUT/構造図テストデータのコピーOUT.pdf"

# 保存先PDFデータを作成
print(portrait(A3))
cc = canvas.Canvas(out_path)
# cc = canvas.Canvas(out_path,pagesize=portrait(A3))
cc = canvas.Canvas(out_path,pagesize=landscape(A3))

# cc.setPageSize = pagesize=portrait(A3)
cc.setPageSize = pagesize=landscape(A3)

# cc.rotate(90)
# PDFを読み込む
pdf = PdfReader(in_path, decompress=False)

# PDFのページデータを取得
page = pdf.pages[0]

page.Rotate = 90
# PDFデータへのページデータの展開
pp = pagexobj(page) #ページデータをXobjへの変換
rl_obj = makerl(cc, pp) # ReportLabオブジェクトへの変換  
cc.doForm(rl_obj) # 展開

# 円の描画
cc.setFillColorRGB(0.5, 0, 1, 0.5)
cc.setLineWidth(5 * mm)
cc.circle(200 * mm, -50 * mm, 50, fill=1)

# 線の描画
cc.setLineWidth(10 * mm)
cc.setStrokeColor("green")
cc.line(10 * mm, 20 * mm, 200 * mm, 274 * mm)

# 長方形の描画
cc.setFillColor("white", 0.5)
cc.setStrokeColorRGB(1.0, 0, 0)
cc.rect(0 * mm, 0 * mm, 100 * mm, 100 * mm, fill=1)

# 英語の描画
cc.setFillColor("purple")
cc.drawString(10 * mm, 10 * mm, "Hello, World")

# 日本語の描画
cc.setFillColorRGB(0, 1, 1, 0.5)
font_name = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(font_name))
cc.setFont(font_name, 30)
cc.drawString(10 * mm, 10 * mm, "こんにちは、世界")

# ページデータの確定
# cc.rotate(-90)
cc.showPage()


# PDFの保存
cc.save()