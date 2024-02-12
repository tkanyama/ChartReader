#********************************************************************
#
#   PDFの部材リストからデータを読み取るクラス
#
#********************************************************************

# pip install pdfplumber
import pdfplumber
from io import StringIO
import time

# pip install numpy matplotlib scipy
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import re
import sys,csv,os

# pip install reportlab ja_cvu_normalizer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from ja_cvu_normalizer.ja_cvu_normalizer import JaCvuNormalizer

# 自作ツールの読み込み
from pattenCheck import PatternCheck

cc = 25.4/72.0
Climit = 3
DbPrint = False
# DbPrint = True



class ChartReader:
    def __init__(self):

        self.MemberPosition = {}    # 部材符号と諸元データの辞書
        self.BeamData = []
        self.ColumnData = []
        # self.makePattern()
        # 源真ゴシック等幅フォント
        # GEN_SHIN_GOTHIC_MEDIUM_TTF = "/Library/Fonts/GenShinGothic-Monospace-Medium.ttf"
        GEN_SHIN_GOTHIC_MEDIUM_TTF = "./Fonts/GenShinGothic-Monospace-Medium.ttf"
        self.fontname1 = 'GenShinGothic'
        # IPAexゴシックフォント
        # IPAEXG_TTF = "/Library/Fonts/ipaexg.ttf"
        IPAEXG_TTF = "./Fonts/ipaexg.ttf"
        self.fontname2 = 'ipaexg'
        
        # フォント登録
        pdfmetrics.registerFont(TTFont(self.fontname1, GEN_SHIN_GOTHIC_MEDIUM_TTF))
        pdfmetrics.registerFont(TTFont(self.fontname2, IPAEXG_TTF))
    #end def

        
    def Sort_Element(self, E_data, ItemName="梁符号", sc=-1):
        # BeamDataを階数の降順で並び替える
        E_data1 = E_data
        E_data2 = []
        L2 = []
        for i in range(len(E_data)):
            floor = E_data1[i][0]["階"]
            if floor == "R":
                L2.append(1000)
            else:
                if "," in floor:
                    floor2 = floor.split(",")
                    L2.append(int(floor2[0]))
                else:
                    L2.append(int(floor))
                #end if
            #end if
            # L2.append(BeamData[i][0][0])
        #next
        VArray = np.array(L2)      # リストをNumpyの配列に変換
        index1 = np.argsort(sc * VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        L22 = []
        for j in range(len(index1)):
            E_data2.append(E_data1[index1[j]])
        #next
        E_data1 = E_data2

        # BeamDataを階毎に梁符号の昇順で並び替える
        E_data2 = []
        L2 = []
        foor = E_data1[0][0]["階"]
        bn = E_data1[0][0][ItemName]
        bn = re.sub(r"\D", "", bn)
        L2.append(int(bn))
        Beams = []
        Beams.append(E_data1[0])
        for i in range(1,len(E_data1)):
            if foor == E_data1[i][0]["階"]:
                Beams.append(E_data1[i])
                bn = E_data1[i][0][ItemName]
                bn = re.sub(r"\D", "", bn)
                L2.append(int(bn))
            else:
                VArray = np.array(L2)      # リストをNumpyの配列に変換
                index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                Beam2 = []
                for j in range(len(index1)):
                    Beam2.append(Beams[index1[j]])
                #next
                E_data2 += Beam2

                L2 = []
                foor = E_data1[i][0]["階"]
                bn = E_data1[i][0][ItemName]
                bn = re.sub(r"\D", "", bn)
                L2.append(int(bn))
                Beams = []
                Beams.append(E_data1[i])
            #end if
        #next
        if len(Beams)>0:
            VArray = np.array(L2)      # リストをNumpyの配列に変換
            index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
            Beam2 = []
            for j in range(len(index1)):
                Beam2.append(Beams[index1[j]])
            #next
            E_data2 += Beam2
        #end if
        return E_data2
    
    #end def

    def Read_Word_From_Page(self, page):
        # wordデータを高さy1の順に並び替え
        page_word = []
        Lheight = []
        for obj in page.extract_words():
            text = obj['text']
            x0, y0, x1, y1 = obj['x0'], obj['top'], obj['x1'], obj['bottom']
            page_word.append({'text': text, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'xm': (x0 +x1)/2})
            Lheight.append(y1)
        #end if

        VArray = np.array(Lheight)      # リストをNumpyの配列に変換
        index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        page_word2 = []    
        for j in range(len(index1)):
            page_word2.append(page_word[index1[j]])
        #next
        page_word = page_word2
        row = 1
        line_word = []

        # 同じy1のwordを同じ行のリストにまとめる
        page_lines = []
        Lheight0 = page_word[0]["y1"]
        page_word[0]["row"] = row
        line_word.append(page_word[0])
        for i in range(1,len(page_word)):
            if (page_word[i]["y1"] - Lheight0)< 0.1 :
                page_word[i]["row"] = row
                line_word.append(page_word[i])
            else:
                page_lines.append(line_word)
                row += 1
                line_word = []
                Lheight0 = page_word[i]["y1"]
                page_word[i]["row"] = row
                line_word.append(page_word[i])
            #end if
        #next
        if len(line_word)>0:
            page_lines.append(line_word)
        #end if
        a=0

        # 同じ行のwordをx0の順に並べ替える。
        page_lines2 = []
        for line in page_lines:
            line2 = []
            xx = []
            for d1 in line:
                xx.append(d1["x0"])
            #next
            VArray = np.array(xx)      # リストをNumpyの配列に変換
            index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
            for j in range(len(index1)):
                line2.append(line[index1[j]])
            #next
            page_lines2.append(line2)
        #next
        page_lines = page_lines2


        # 各行の近接するwordをひとつのワードに統合する。
        # 結合条件は 文字ピッチ×spaceN 以内の距離
        spaceN = 1.5
        page_lines3 = []
        for line in page_lines:
            if DbPrint:
                t1 = ""
                for L1 in line:
                    t1 += L1["text"]+","
                print(t1,len(line))

            if len(line)>1 :
                line2 = []
                # word0 = {}
                wn = len(line)
                wi = 0
                while wi < wn - 1:
                    word0 = line[wi]
                    pitch = (word0["x1"] - word0["x0"]) / len(word0["text"])
                    word1 = line[wi + 1]
                    if len(word0["text"]) <= Climit:
                        c = 2.2
                    elif "・" in word0["text"] or "・" in word1["text"]:
                        c = 5.0
                    else:
                        c = 1.0
                    #end if
                    if word0["y0"] == word1["y0"] and word1["x0"] - word0["x1"] <= pitch * spaceN * c:
                        word0["text"] =  word0["text"] + " " + word1["text"]
                        word0["x1"] = word1["x1"]
                        word0["xm"] = (word0["x0"] + word0["x1"])/2
                        line2.append(word0)
                        wi += 1
                    else:
                        line2.append(word0)
                    #end if
                    wi += 1
                #end while
                if wi < wn:
                    line2.append(line[wi])
                #end if
            else:
                line2=line
            #end if
            if DbPrint:
                t2 = ""
                for L1 in line2:
                    t2 += L1["text"]+","
                print(t2,len(line2))

            #     line2 = []
            #     word0 = {}
            #     for word in line:
            #         if len(word0) == 0:     # 各行の最初の単語の処理
            #             # words.append(word)
            #             word0 = word
            #             # word0["text"] = word["text"]
            #             # word0["x0"] = word["x0"]
            #             # word0["x1"] = word["x1"]
            #             # word0["y0"] = word["y0"]×|x|ｘ
            #             # word0["y1"] = word["y1"]
            #             # word0["xm"] = word["xm"]
            #             pitch = (word0["x1"] - word0["x0"]) / len(word0["text"])
            #             # print("pirch = {}".format(pitch))
            #         else:
            #             if len(word0["text"]) <= Climit:
            #                 c = 1.5
            #             # elif "×" in word0["text"] or "x" in word0["text"] or "ｘ" in word0["text"] or "×" in word["text"] or "x" in word["text"] or "ｘ" in word["text"]:
            #             #     c = 1.2
            #             elif "・" in word0["text"] or "・" in word["text"]:
            #                 c = 5.0
            #             else:
            #                 c = 1.0
            #             #end if
            #             if word0["y0"] == word["y0"] and word["x0"] - word0["x1"] <= pitch * spaceN * c:
            #                 word0["text"] =  word0["text"] + " " + word["text"]
            #                 word0["x1"] = word["x1"]
            #                 word0["xm"] = (word0["x0"] + word0["x1"])/2
            #             else:
            #                 line2.append(word0)
            #                 # print(word0["text"])
            #                 word0 = word
            #                 pitch = (word0["x1"] - word0["x0"]) / len(word0["text"])
            #             #end if
            #         #end if
            #     #end if
            # else:
            #     line2=line
            # #end if
                



            # print(line)
            # print(line2)
            if len(line2)>1:
                line3 = []
                wn = len(line2)
                # for word in line2:
                    
                wi = 0
                
                pt1 = "(\s*\d+\s*)|(\s*\d+,\d+\s*)"
                pt2 = "((\s*(×|x|ｘ)\s*\d+(\s*\(\S+\))*\s*))|(\s*\d+\s*(×|x|ｘ)\s*\d+,\d+(\s*\(\S+\))*\s*)"
                pt3 = "(\s*\d+\s*(×|x|ｘ)\s*)|(\s*\d+,\d+\s*(×|x|ｘ)\s*)"

                pt4 = "(\s*\w+\s*)"
                pt5 = "((\s*(×|x|ｘ)\s*\S+\s*))"
                pt6= "(\s*\S+\s*(×|x|ｘ)\s*)"

                pt7 = "(\s*\d{1,2}-D\d{2}\s*)"
                pt8 = "(\s*\+\s*\d{1,2}-D\d{2}\s*)"
                pt9= "(\s*\d{1,2}-D\d{2}\s*\+\s*)"
                
                while wi < wn - 1 :

                    word1 = line2[wi]
                    text1 = word1["text"]
                    # if text1 == "位 置" :
                    #     a=0
                    # #end if
                    x10 = word1["x0"]
                    x11 = word1["x1"]
                    y10 = word1["y0"]

                    word2 = line2[wi+1]
                    text2 = word2["text"]
                    x20 = word2["x0"]
                    x21 = word2["x1"]
                    y20 = word2["y0"]

                    # print (text1,text2)

                    # flag01 = re.match(pt1,text1) != None
                    # flag02 = re.match(pt2,text1) != None
                    # flag03 = re.match(pt3,text1) != None
                    # flag04 = re.match(pt1,text2) != None
                    # flag05 = re.match(pt2,text2) != None
                    # flag06 = re.match(pt3,text2) != None
                    # print(flag01,flag02,flag03,flag04,flag05,flag06)

                    # (500)  (x 1500)
                    flag1 = (re.match(pt1,text1) != None )and (re.match(pt2,text2) != None)
                    # (500 x )  (500)
                    flag2 = (re.match(pt3,text1) != None) and (re.match(pt1,text2) != None)

                    # (B)  (x D)
                    flag3 = (re.match(pt4,text1) != None )and (re.match(pt5,text2) != None)
                    # (B x )  (D)
                    flag4 = (re.match(pt6,text1) != None) and (re.match(pt4,text2) != None)

                    # (2-D25)  (+ 4-D35)
                    flag5 = (re.match(pt7,text1) != None )and (re.match(pt8,text2) != None)
                    # (2-D25 + )  (4-D35)
                    flag6 = (re.match(pt9,text1) != None) and (re.match(pt7,text2) != None)

                    # print(flag1,flag2)
                    
                    if (y10 == y20) and (x20 > x11 and (x20 - x11) < pitch * spaceN * 1.0):
                        if flag1 or flag2 or flag3 or flag4 or flag5 or flag6:
                            word = word1
                            word["text"] = text1 + " " + text2
                            word["x1"] = x21
                            word["xm"] = (x10 + x21)/2.0
                            line3.append(word)
                            if DbPrint:
                                print(word["text"])
                            wi += 1

                        else:
                            line3.append(word1)
                        #end if
                    else:
                        line3.append(word1)
                    #end if
                        
                    # line3.append(word1)
                    wi += 1
                #end while
                if wi < wn:
                    line3.append(line2[wi])
                #end if
                #end if
                    
                #next for word in line2:
                
            else:
                line3 = line2
            # end if
            if len(line3)>0:
                page_lines3.append(line3)
            #end if
            if DbPrint:
                t3 = ""
                for L1 in line3:
                    t3 += L1["text"]+","
                print(t3,len(line3))
                print()
            
        #next
        page_lines = page_lines3

        return page_lines
    
    #end def
        
    def Read_Elements_from_pdf(self, pdf_path):

        # CR = ChartReader()
        with pdfplumber.open(pdf_path) as pdf:

            BeamData = []
            ColumnData = []
            for pageN, page in enumerate(pdf.pages):

                if pageN >= 0:
                    print("page = {}".format(pageN+1),end="")

                    # if pageN == 33:
                    #     a=0
                    # Page_Width = page.width
                    # Page_Height = page.height

                    page_lines = self.Read_Word_From_Page(page)

                    BeamData1, ColumnData1 = CR.ElementFinder(page_lines)

                    print("  梁データ:{}個 , 柱データ:{}個".format(len(BeamData1), len(ColumnData1)))
                    if len(BeamData1) > 0:
                        BeamData += BeamData1
                    #end if
                    if len(ColumnData1) > 0:
                        ColumnData += ColumnData1
                    #end if
            #next
        #end with
        
        # 階および符号名でデータの並び替え
                    
        BeamData = self.Sort_Element(BeamData, ItemName="梁符号", sc=-1)    # sc=-1:降順,sc=1:昇順

        ColumnData = self.Sort_Element(ColumnData, ItemName="柱符号",sc=-1)  # sc=-1:降順,sc=1:昇順

        return BeamData, ColumnData

    # #end def




    def ElementFinder(self,PageWordData):
        """
        
        """

        # 文字列パターンを用いてデータの種類を判別するオブジェクトの作成
        pCheck = PatternCheck()
        # データの種類リスト（例：断面寸法）
        KeyNames = pCheck.KeyNames
        
        
        # 異体字正規化モジュール
        ja_cvu_normalizer = JaCvuNormalizer()
                        
        words = []
        wordsByKind = {}
        for keyname in KeyNames:
            wordsByKind[keyname] = []
        #next

        ypitch = 0
        for i, LineWord in enumerate(PageWordData):
            # line = []
            for j, word in enumerate(LineWord):
                t1 = word["text"]
                kind = pCheck.checkPattern(t1)
                if kind != "":
                    word2 = {}
                    word2["text"] = word["text"]
                    word2["kind"] = kind
                    word2["row"] = word["row"]
                    word2["x0"] = word["x0"]
                    word2["x1"] = word["x1"]
                    word2["xm"] = word["xm"]
                    word2["y0"] = word["y0"]
                    word2["y1"] = word["y1"] 
                    # line.append(word2)
                    wordsByKind[kind].append(word2)
                    if abs(word["y0"]-word["y1"])>ypitch:
                        ypitch = abs(word["y0"]-word["y1"])
                    #end if
                #end if
            #next
            # if len(line)>0:
            #     wordsByKind[kind].append(line)
            # #end if
        #next

        rowmax = len(PageWordData)

        梁符号1 = wordsByKind["梁符号1"]
        梁符号2 = wordsByKind["梁符号2"]
        梁符号 = []
        if len(梁符号1) > 0:
            梁符号 = 梁符号1
        else:
            if len(梁符号2) > 0:
                flag = False
                for d in 梁符号2:
                    if "FG" in d["text"]:
                        flag = True
                    #end if
                #next
                if flag:
                    梁符号 = 梁符号2
                    梁符号2 = []
                #end if
            #end if
        #end if
        for i in range(len(梁符号)):
            梁符号[i]["kind"] = "梁符号"
        #next

        小梁符号 = wordsByKind["小梁符号"]
        片持梁符号 = wordsByKind["片持梁符号"]

        if len(梁符号)>0:
            梁断面位置 = wordsByKind["梁断面位置"]
            if len(梁断面位置) > 0:
                beamPitch = 0
                xm1 = 梁断面位置[0]["xm"]
                row1 = 梁断面位置[0]["row"]
                for i in range(1,len(梁断面位置)):
                    xm2 = 梁断面位置[i]["xm"]
                    row2 = 梁断面位置[i]["row"]
                    if row2 == row1 :
                        beamPitch = abs(xm1 - xm2)
                        break
                    #end if
                #next
            else:
                beamPitch = 72
            #end if
        else:
            梁断面位置 = []
        #end if ja_cvu_normalizer.normalize(Line) 
        if len(梁断面位置):
            梁断面位置2 = []
            for data in 梁断面位置:
                data["text"] = ja_cvu_normalizer.normalize(data["text"]) 
                梁断面位置2.append(data)
            #next
            梁断面位置 = 梁断面位置2

            # 梁断面位置のうちすぐ上に片持梁符号や小梁符号があるものは削除する。
            梁断面位置2 = []
            for d in 梁断面位置:
                # print(d["text"])
                row = d["row"]
                xm = d["xm"]
                flag = True
                for d1 in 片持梁符号:
                    row1 = d1["row"]
                    xm1 = d1["xm"]
                    if abs(row - row1) <=3 and abs(xm - xm1)<beamPitch:
                        flag = False
                    #end if
                #next
                for d1 in 小梁符号:
                    row1 = d1["row"]
                    xm1 = d1["xm"]
                    if abs(row - row1) <=3 and abs(xm - xm1)<beamPitch:
                        flag = False
                    #end if
                #next
                if flag :
                    梁断面位置2.append(d)
                #end if
            #next
            梁断面位置 = 梁断面位置2

            # 梁断面位置の並び整える
            梁断面位置2=[]
            y0 = 梁断面位置[0]["y0"]
            yy = []
            yy.append(y0)
            for i in range(1,len(梁断面位置)):
                yy0 = 梁断面位置[i]["y0"]
                for yy1 in yy:
                    flag = False
                    if abs(yy0 - yy1) > ypitch:
                        flag = True
                    #end if
                #end if
                if flag :
                    yy.append(yy0)
                #end if
            #next
            a=0
            
            for yy1 in yy:
                data = []
                for d in 梁断面位置:
                    if abs(d["y0"] - yy1) < 0.5:
                        data.append(d)
                    #end if
                #end if
                L2 = []
                for d in data:
                    L2.append(d["x0"])
                #next
                VArray = np.array(L2)      # リストをNumpyの配列に変換
                index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                data2 = []
                for j in range(len(index1)):
                    data2.append(data[index1[j]])
                #next
                梁断面位置2 += data2
            #next
            梁断面位置 = 梁断面位置2
        #end if

                

        項目名1 = wordsByKind["項目名1"]
        項目名2 = wordsByKind["項目名2"]
        断面寸法 = wordsByKind["断面寸法"]
        コンクリート強度 = wordsByKind["コンクリート強度"]
        フープ筋 = wordsByKind["フープ筋"]
        主筋 = wordsByKind["主筋"]
        腹筋 = wordsByKind["腹筋"]
        材料 = wordsByKind["材料"]
        階 = wordsByKind["階"]
        壁 = wordsByKind["壁"]
        日付 = wordsByKind["日付"]
        かぶり = wordsByKind["かぶり"]
        柱符号 = wordsByKind["柱符号"]
        柱符号2 = wordsByKind["柱符号2"]
        構造計算書 = wordsByKind["構造計算書"]
        断面リスト = wordsByKind["断面リスト"]
        
        if len(構造計算書)>0:
            if len(断面リスト)==0 :
                BeamData = []
                ColumnData = []
                return BeamData,ColumnData
            #end if
        #end if

        if len(主筋) == 0 or (len(梁符号) == 0 and len(柱符号) == 0):
            BeamData = []
            ColumnData = []
            return BeamData,ColumnData
        #end if
        # 各部材の項目名Itemに名称を追加
        ItemName = ["梁符号","梁断面位置","梁符号2","主筋","階","断面寸法","かぶり",
                    "柱符号","柱符号2","腹筋","フープ筋","材料"]
        for Item in ItemName:
            if len(locals()[Item])>0:
                for j in range(len(locals()[Item])):
                    locals()[Item][j]["item"] = ""
                #next
            #end if
        #next

        # フープ筋と材料については表の左側の項目名を追加（あば筋、帯筋等）
        ItemName = ["主筋","フープ筋","材料"]
        for Item in ItemName:
            if len(locals()[Item])>0:
                # flag = [0]*len(locals()[Item])
                for j in range(len(locals()[Item])):
                    # if flag[j] == 0:
                    dataDic1 = locals()[Item][j]
                    row = dataDic1["row"]
                    xm = dataDic1["xm"]
                    left0 = dataDic1["x0"]
                    right0 = dataDic1["x1"]
                    top0 = dataDic1["y0"]
                    bottom0 = dataDic1["y1"]
                    d2 = []
                    for d in 項目名1:
                        row1 = d["row"]
                        left1 = d["x0"]
                        right1 = d["x1"]
                        top1 = d["y0"]
                        bottom1 = d["y1"]
                        if right1<left0 and top1-ypitch*2.0 < top0 and bottom1+ypitch*2.0 > bottom0:
                            if "筋" in d["text"] or "フープ" in d["text"] or "HOOP" in d["text"]:
                                d2.append(d)
                            #end if
                        #end if
                    #next
                            
                    # 項目名の決定
                    if len(d2) == 1:
                        # 近くにある項目名がひとつの場合はそれを選択する
                        if Item == "主筋" :
                            if not("主" in d2[0]["text"] and "筋" in d2[0]["text"]):
                            # if re.fullmatch("\s*主\s*\筋\s*\S*\s*",d2[0]["text"]) == None :
                                locals()[Item][j]["item"] = d2[0]["text"]
                            else:
                                locals()[Item][j]["item"] = ""
                            #end if
                        else:
                            locals()[Item][j]["item"] = d2[0]["text"]
                        #end if
                        # flag[j] = 1
                    elif len(d2) > 1:
                        # 近くにある項目名が複数有るときはもっとの高低差が小さいものを選択する
                        h1 = 10000
                        im = -1
                        for k, d1 in enumerate(d2):
                            top1 = d1["y0"]
                            if abs(top0 - top1)< h1:
                                h1 = abs(top0 - top1)
                                im = k
                            #end if
                        #next
                        if im > -1 :
                            if Item == "主筋":
                                if not("主" in d2[im]["text"] and "筋" in d2[im]["text"]) :
                                # if re.fullmatch("\s*主\s*\筋\s*\S*\s*",d2[im]["text"]) == None :
                                    locals()[Item][j]["item"] = d2[im]["text"]
                                else:
                                    locals()[Item][j]["item"] = ""
                                #end if
                            else:
                                locals()[Item][j]["item"] = d2[im]["text"]
                            #end if
                            # locals()[Item][j]["item"] = d2[im]["text"]
                            # flag[j] = 1
                        #end if
                    #end if
                #next for j in range(len(locals()[Item])):
            #end if
        #next for Item in ItemName:
        a=0

        # 梁符号または柱符号の最初のデータのx0を階データの閾値とする
        floorXmin1= 10000.0
        if len(梁符号)>0:
            floorXmin1 = 梁符号[0]["x0"]
        #end if
        floorXmin2 = 10000.0
        if len(柱符号)>0:
            floorXmin2 = 柱符号[0]["x0"]
        #end if
        if floorXmin1 < floorXmin2:
            floorXmin = floorXmin1 - 36
        else:
            floorXmin = floorXmin2 - 36
        #end if


        if len(階) > 0:
            # 階のデータのうち、上端３行と下端３行およびfloorXminより右側ののデータは除外する
            階2 = []
            for d in 階:
                if d["row"] > 3 and d["row"] < rowmax-3 and d["x1"] < floorXmin:
                    階2.append(d)
                #end if
            #next
            階 = 階2        
            
            if len(階) > 0:
                # 階データのうち、上下２段（行の差が５行以内）で表記されているものは１つのデータのまとめる
                階2 = []
                row0 = 階[0]["row"]
                xm0 = 階[0]["xm"]
                階2.append(階[0])
                for i in range(1, len(階)):
                    row = 階[i]["row"]
                    xm = 階[i]["xm"]
                    if row - row0 > 6 or abs(xm - xm0) > 72:
                        階2.append(階[i])
                    else:
                        階2[i-1]["text"] += " , " + 階[i]["text"]
                    #end if
                    row0 = row
                    xm0 = xm
                #end if
                階 = 階2
            #end if
        #end if

        # かぶりデータを行で並び替え
        L2 = []
        for i in range(len(かぶり)):
            L2.append(かぶり[i]["row"])
        #next
        VArray = np.array(L2)      # リストをNumpyの配列に変換
        index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        L22 = []
        for j in range(len(index1)):
            L22.append(かぶり[index1[j]])
        #next
        かぶり = L22

        #===================================
        # 梁部材の抽出
        #===================================
        
        dn = len(梁断面位置)
        Section = []
        Section2 = []
        BeamData = []
        if dn > 0 and len(梁符号) > 0:
            flag = [0] * dn
            for i in range(dn):
                if flag[i] == 0 :
                    text0 = 梁断面位置[i]["text"]
                    row0 = 梁断面位置[i]["row"]  # 行位置を記憶
                    xm0 = 梁断面位置[i]["xm"]    # 梁断面位置Ｘ座標を記憶
                    y00 = 梁断面位置[i]["y0"]  # 行位置を記憶
                    
                    sn2 = []
                    if "全断" in text0 :
                        Section.append([梁断面位置[i]])
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        Section2.append(sn2)
                        # Section2.append([[梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]]])
                        flag[i] = 1
                    elif "端部" in text0 or "両端" in text0 :
                        sn = [梁断面位置[i]]
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]    # 梁断面位置Ｘ座標を記憶
                                if text1 == "中央" and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*1.2:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    # break
                                #end if
                            #end if
                        #next
                        Section.append(sn)
                        Section2.append(sn2)
                    elif "端部" in text0 or "両端" in text0 :
                        sn = [梁断面位置[i]]
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]    # 梁断面位置Ｘ座標を記憶
                                if text1 == "中央" and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*1.2:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    # break
                                #end if
                            #end if
                        #next
                        Section.append(sn)
                        Section2.append(sn2)
                    elif "元端" in text0  :
                        sn = [梁断面位置[i]]
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if text1 == "先端" and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*1.2:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    # break
                                #end if
                            #end if
                        #next
                        Section.append(sn)
                        Section2.append(sn2)
                    elif "左端" in text0 :
                        sn = [梁断面位置[i]]
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if "中央" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*1.2:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if "右端" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*2.4:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        Section.append(sn)
                        Section2.append(sn2)
                    elif "通端" in text0 :
                        sn = [梁断面位置[i]]
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if "中央" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*1.2:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if "通端" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*2.4:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        Section.append(sn)
                        Section2.append(sn2)

                    elif "端" in text0 :
                        sn = [梁断面位置[i]]
                        dic = {}
                        dic["kind"] = 梁断面位置[i]["kind"]
                        dic["text"] = 梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = 梁断面位置[i]["row"]
                        dic["xm"] = 梁断面位置[i]["xm"]
                        dic["y0"] = 梁断面位置[i]["y0"]
                        dic["item"] = 梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if "中央" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*1.2:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = 梁断面位置[j]["text"]
                                row1 = 梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = 梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = 梁断面位置[j]["y0"]
                                if "端" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < beamPitch*2.4:
                                    sn.append(梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = 梁断面位置[j]["kind"]
                                    dic["text"] = 梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = 梁断面位置[j]["row"]
                                    dic["xm"] = 梁断面位置[j]["xm"]
                                    dic["y0"] = 梁断面位置[j]["y0"]
                                    dic["item"] = 梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        Section.append(sn)
                        Section2.append(sn2)
                    #next
                #end if
            #next
            xpitch = 0.0
            for Sec in Section:
                if len(Sec)>1 :
                    xpitch = Sec[1]["xm"] - Sec[0]["xm"]
                    break
                #end if
            #next
            if xpitch == 0.0 :
                xpitch = 72.0
            #end if
            
            #
            for i in range(len(Section)):
                for j in range(len(Section[i])):
                    Section[i][j]["rmax"] = -1
                #next
                row0 = Section[i][0]["row"]  # 行位置を記憶
                xm0 = Section[i][0]["xm"]    # 梁断面位置Ｘ座標を記憶

                # 同じ列に再び梁断面位置がある場合は別の梁部材表であると判断し、データの終端行位置をその行−２とする。
                for j in range(i + 1, len(Section)): # 次の梁断面位置から比較する。
                    row = Section[j][0]["row"]
                    xm = Section[j][0]["xm"]
                    if row != row0 and abs(xm - xm0) < xpitch*1.5:
                        for k in range(len(Section[i])):
                            Section[i][k]["rmax"] = row - 1
                        #next
                        break
                    #end if
                #next
                
                # 梁断面位置の代わりに柱符号または小梁符号または片持梁符号があった場合も別の梁部材表であると判断し、データの終端行位置をその行−1とする。
                ItemName = ["柱符号","小梁符号","片持梁符号","壁"]
                for Item in ItemName:
                    if Section[i][0]["rmax"] == -1:
                        for j in range(len(locals()[Item])):
                            dataDic1 = locals()[Item][j]
                            row = dataDic1["row"]
                            xm = dataDic1["xm"]
                            if row > row0 and abs(xm - xm0) < xpitch*1.5:
                                for k in range(len(Section[i])):
                                    Section[i][k]["rmax"] = row - 1
                                #next
                                break
                            #end if
                        #next
                    #end if
                #next

                # 最後までデータの終端行位置が-1の場合は別の梁部材表がないと判断し、データの終端行位置をページの最終行-3とする。
                if Section[i][0]["rmax"] == -1:
                    for j in range(len(Section[i])):
                        Section[i][j]["rmax"] = rowmax 
                    #next
                #end if
            #next

            # 梁断面位置の記号があってもその上に梁符号がないものは削除する。
            Section01 = []
            Section02 = []
            
            for i, Sec in enumerate(Section):
                if len(Sec)==0:
                    row0 = Sec[0]["row"]
                    xmin = Sec[0]["xm"]-xpitch/2
                    xmax = Sec[0]["xm"]+xpitch/2
                else:
                    row0 = Sec[0]["row"]
                    xmin = Sec[0]["x0"]-20
                    xmax = Sec[len(Sec)-1]["x1"]+20
                #end if
                for d in 梁符号:
                    row1 = d["row"]
                    xm1 = d["xm"]
                    if row1 < row0 and xm1 >= xmin and xm1 <= xmax:
                        Section01.append(Sec)
                        Section02.append(Section2[i])
                        break
                    #end if
                #next
            #next
            Section = Section01
            Section2 = Section02


            for i in range(len(Section)):
                bn = len(Section[i])
                if bn == 1:
                    xm0 = Section[i][0]["xm"]
                    row0 = Section[i][0]["row"]
                    xmin = Section[i][0]["xm"]-xpitch/2
                    xmax = Section[i][0]["xm"]+xpitch/2
                else:
                    xm0 = (Section[i][0]["xm"] + Section[i][bn - 1]["xm"])/2
                    row0 = Section[i][0]["row"]
                    xmin = Section[i][0]["x0"]-20
                    xmax = Section[i][bn-1]["x1"]+20
                #end if
                
                for j in range(len(Section[i])):
                    Section[i][j]["xm0"] = xm0
                #nextj , d2 in enumerate(梁符号1)
                    
                # xmin = Section[i][0]["x0"]
                # xmax = Section[i][bn-1]["x1"]

                row1 = Section[i][0]["row"]
                rmax = Section[i][0]["rmax"]
                
                data = []
                flag1 = True
                for k,d1 in enumerate(梁符号):   # ローカル変数を名前で指定する関数
                    xm = d1["xm"]
                    row = d1["row"]
                    if abs(row1 - row) < 4 and xm >= xmin and xm <= xmax:
                        dic = {}
                        dic["kind"] = d1["kind"]
                        dic["text"] = d1["text"]
                        dic["number"] = k
                        dic["row"] = d1["row"]
                        dic["xm"] = d1["xm"]
                        dic["y0"] = d1["y0"]
                        dic["item"] = d1["item"]
                        data.append(dic)
                        flag1 = False   # 梁符号1が見つかった場合はFlag1をFalseにする。
                    #end if
                #next
                
                if flag1 :      # 梁断面位置のすぐ上に梁符号がない場合は一番上にある梁符号を割り当てる。
                    for k,d1 in enumerate(梁符号):   # ローカル変数を名前で指定する関数
                        xm = d1["xm"]
                        row = d1["row"]
                        if row1 > row and xm >= xmin and xm <= xmax:
                            # data.append(d1)
                            dic = {}
                            dic["kind"] = d1["kind"]
                            dic["text"] = d1["text"]
                            dic["number"] = k
                            dic["row"] = d1["row"]
                            dic["xm"] = d1["xm"]
                            dic["y0"] = d1["y0"]
                            dic["item"] = d1["item"]
                            data.append(dic)
                            # Section2[i][j].append(dic)
                            flag1 = False
                        #end if
                    #next
                #end if
                
                if len(data) >0 :
                    if len(data) == len(Section2[i]):
                        for j in range(len(Section2[i])):
                            Section2[i][j].append(data[j])
                        #next
                    else:
                        for j in range(len(Section2[i])):
                            Section2[i][j].append(data[0])
                        #next
                    #end if
                #enf if
                
                
                ItemName = ["梁符号2","断面寸法","主筋","フープ筋","かぶり","材料","腹筋"]
                # ItemName = ["主筋","フープ筋","かぶり","材料","コンクリート強度","腹筋"]
                
                for Item in ItemName:
                    data = []
                    s2 = []
                    for k, d1 in enumerate(locals()[Item]):   # ローカル変数を名前で指定する関数
                        xm = d1["xm"]
                        row = d1["row"]
                        if row >= row1 and row <= rmax and xm >= xmin and xm <= xmax:
                            dic = {}
                            dic["kind"] = d1["kind"]
                            dic["text"] = d1["text"]
                            dic["number"] = k
                            dic["row"] = d1["row"]
                            dic["xm"] = d1["xm"]
                            dic["y0"] = d1["y0"]
                            dic["item"] = d1["item"]
                            data.append(dic)
                            
                        #end if
                    #next
                    
                    if len(data)>0:
                        if len(data) == 1:
                            dic = {}
                            dic["kind"] = data[0]["kind"]
                            dic["text"] = data[0]["text"]
                            dic["number"] = 0
                            dic["row"] = data[0]["row"]
                            dic["xm"] = data[0]["xm"]
                            dic["y0"] = data[0]["y0"]
                            dic["item"] = data[0]["item"]
                            s2.append(dic)
                            for j in range(len(Section2[i])):
                                Section2[i][j].append(data[0])
                            #next
                        else:
                            r1 = data[0]["row"]
                            data2 = []
                            data1 = [data[0]]
                            for j in range(1,len(data)):
                                r2 = data[j]["row"]
                                if r1 == r2 :
                                    data1.append(data[j])
                                else:
                                    data2.append(data1)
                                    r1 = data[j]["row"]
                                    data1 = [data[j]]
                                #end if
                            #next
                            if len(data1)>0:
                                data2.append(data1)
                            #end if
                            for data in data2:
                                if len(data) == len(Section2[i]):
                                    for j in range(len(Section2[i])):
                                        Section2[i][j].append(data[j])
                                    #next
                                else:
                                    for j in range(len(Section2[i])):
                                        Section2[i][j].append(data[0])
                                    #next
                                #end if
                            #end if
                        #end if :(if len(data) == 1:)
                                        
                    #end if :(if len(data)>0:)
                    
                #next :(for Item in ItemName:)
                
                if len(階)>0:
                    ItemName2 = ["階"]
                    
                    for j in range(len(Section[i])):
                        row1 = Section[i][j]["row"]
                        rmax = Section[i][j]["rmax"]
                        xm1 = Section[i][0]["xm"]
                        for Item in ItemName2:
                            # data = []
                            for k, d1 in enumerate(locals()[Item]):   # ローカル変数を名前で指定する関数
                                xm = d1["xm"]
                                row = d1["row"]
                                if row >= row1 and row <= rmax and xm < xm1:
                                    # data.append(d1)
                                    dic = {}
                                    dic["kind"] = d1["kind"]
                                    floor = d1["text"]
                                    if floor[0] == "R":
                                        floor = "R"
                                    else:
                                        if "," in floor:
                                            floor2 = floor.split(",")
                                            floor = ""
                                            for f in floor2:
                                                floor += re.sub(r"\D", "", f) + ","
                                            #next
                                            floor = floor[0:len(floor)-1]
                                        else:
                                            floor = re.sub(r"\D", "", floor)
                                        #end if
                                    #end if
                                    # dic["text"] = d1["text"]
                                    dic["text"] = floor
                                    dic["number"] = k
                                    dic["row"] = d1["row"]
                                    dic["xm"] = d1["xm"]
                                    dic["y0"] = d1["y0"]
                                    dic["item"] = d1["item"]
                                    Section2[i][j].append(dic)
                                #end if
                            #next
                            # Section[i][j][Item] = data
                        #next
                    #next
                
                #end if

            #next :(for i in range(len(Section)):)
        
            # Section2を行の順番に並び替える
            Section22 = []
            for Sec in Section2:
                Sec2 = Sec[0]
                L2 = []
                for dic in Sec2:
                    L2.append(dic["row"])
                #next
                VArray = np.array(L2)      # リストをNumpyの配列に変換
                index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                Sec1 = []
                for d1 in Sec:
                    L22 = []
                    for j in range(len(index1)):
                        L22.append(d1[index1[j]])
                    #next
                    Sec1.append(L22)
                #next
                Section22.append(Sec1)
            #next
            Section2 = Section22
        
            # 部材表は複数の部材が縦に並んでいるので部材毎に分割する処理
            for Sec in Section2:
                for bdata in Sec:
                    
                    # データの種類を取得
                    kind = []
                    for bd in bdata:
                        if bd["item"] !="":
                            keyname = bd["item"]+":"+bd["kind"]
                        else:
                            keyname = bd["kind"]  
                        #end if
                        if not(keyname in kind):
                            kind.append(keyname)
                        #end if
                    #next
                            
                    # 同じ種類の番号を格納する辞書を作成
                    kindSameN = {}
                    for k in kind:
                        kindSameN[k] = []
                    #next
                    
                    # 同じ種類毎に番号を格納する
                    for j, bd in  enumerate(bdata):
                        if bd["item"] !="":
                            keyname = bd["item"]+":"+bd["kind"]
                        else:
                            keyname = bd["kind"]  
                        #end if
                        for kind1 in kind:
                            if keyname == kind1:
                                kindSameN[kind1].append([j,bd["y0"]])
                                break
                            #end if
                        #next
                    #next
                    
                    # 同じ種類のデータがypitchの2倍以内に並ぶ場合は1組のデータとする。
                    kindSameN2 = {}
                    for j, kind1 in enumerate(kind):
                        ln3 = []
                        ln = kindSameN[kind1]
                        if len(ln) == 1:
                            kindSameN2[kind1] = [[ln[0][0]]]
                        else:
                            ln2 = []
                            n0 = ln[0][0]
                            y0 = ln[0][1]
                            ln2.append(n0)
                            for k in range(1,len(ln)):
                                n1 = ln[k][0]
                                y1 = ln[k][1]
                                if abs(y0-y1) < ypitch*3 :
                                    ln2.append(ln[k][0])
                                    n0 = ln[k][0]
                                    y0 = ln[k][1]
                                else:
                                    ln3.append(ln2)
                                    ln2 = []
                                    n0 = ln[k][0]
                                    y0 = ln[k][1]
                                    ln2.append(n0)
                                #end if
                            #next
                            if len(ln2)>0 :
                                ln3.append(ln2)
                            #end if
                            
                        #end if
                        if len(ln3)>0 :
                            kindSameN2[kind1] = ln3
                        #end if
                    #next
                        
                            
                    # 主筋の数を1列にあるデータ数とする。
                    kindSameNMax = len(kindSameN2["主筋"])

                    # 材料は主筋とフープ筋の2カ所に記載される場合があり、そのときは材料1と材料2に分ける。
                    # if len(材料)>0:
                    #     if len(kindSameN2["材料"]) == kindSameNMax*2:
                    #         d0 = kindSameN2["材料"]
                    #         d1 = []
                    #         d2 = []
                    #         for j, d in enumerate(d0):
                    #             if j % 2 == 0:
                    #                 d1.append(d)
                    #             else:
                    #                 d2.append(d)
                    #             #end if
                    #         #next
                    #         kindSameN2["材料1"] = d1
                    #         kindSameN2["材料2"] = d2
                    #     else:
                    #         kindSameN2["材料1"] = kindSameN2["材料"]
                    #     #end if
                    #     removed_value = kindSameN2.pop('材料')
                    # #end if :(if len(材料)>0:)

                    # キーの順番が乱れているので再度行の順番に並び替える。
                    keys = list(kindSameN2.keys())
                    L2 = []
                    for key in keys:
                        L2.append(kindSameN2[key][0][0])
                    #next
                    VArray = np.array(L2)      # リストをNumpyの配列に変換
                    index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                    keys1 = []
                    for j in range(len(index1)):
                        keys1.append(keys[index1[j]])
                    #next
                    keys = keys1
                    
                    # 同じ梁のデータを梁断面位置の順番でひとつにまとめる。
                    beam2 = []            
                    for bdata in Sec:
                        beam = []
                        for Beami in range(kindSameNMax):
                            dataDic1 = []
                            for key in keys:
                                nn = kindSameN2[key]
                                if len(nn) == 1:
                                    n2 = 0
                                    n1 = nn[0]
                                    for n in n1:
                                        n2 += 1
                                        data = bdata[n]
                                        if len(nn[0])>1 :
                                            if not("階" in key) and not("梁符号" in key):
                                                key2 = key + "-" + str(n2)
                                            else:
                                                key2 = key
                                            #end if
                                        else:
                                            key2 = key
                                        #end if
                                        dataDic1.append([key2,data["text"]])
                                    #nex
                                else:
                                    n2 = 0
                                    n1 = nn[Beami]
                                    for n in n1:
                                        n2 += 1
                                        data = bdata[n]
                                        if len(nn[Beami])>1 :
                                            if not("階" in key) and not("梁符号" in key):
                                                key2 = key + "-" + str(n2)
                                            else:
                                                key2 = key
                                            #end if
                                        else:
                                            key2 = key
                                        #end if
                                        dataDic1.append([key2,data["text"]])
                                    #next
                                #next
                                #end if
                            next
                        
                            # 表に階のデータが無い場合は梁符号から作成し、追加する。
                            # FG1 -> 1FL  4G1 -> 4FL
                            if not("階" in keys):
                                hname = bdata[kindSameN2["梁符号"][0][0]]["text"]
                                if hname[0] == "F":
                                    floorName = "1"
                                elif hname[0] == "R":
                                    floorName = "R"
                                else:
                                    floorName = re.sub(r"\D", "", hname)
                                #end if
                                dataDic1.append(["階",floorName])
                            #end if
                            beam.append(dataDic1)

                        #next :(for j in range(kindSameNMax):)
                            
                        beam2.append(beam)

                    #next :(for bdata in Sec:)
                        
                #next :(for bdata in Sec:)
                
                n = len(beam2[0])
                m = len(beam2)
                for i in range(n):
                    beam3= []
                    for j in range(m):
                        beam3.append(beam2[j][i])
                    #next
                    BeamData.append(beam3)
                #next
                
            
            #next :(for Sec in Section2:)
            
        #end if : (if dn > 0 and len(梁符号) > 0:)
        

        #=====================================================================
        # 梁データを辞書形式に変換する処理
        #=====================================================================
        
        BeamData2 = []
        for i,beam in enumerate(BeamData):
            # 梁データ毎にkeyを取り出す。
            keys = []
            for j, data in enumerate(beam):
                for k in range(len(data)):
                    if not(data[k][0] in keys):
                        keys.append(data[k][0])
                    #end if
                #next
            #next
            # keyの先頭を"階"データにする。
            keys2 = []
            for key in keys:
                if key == "階":
                    keys2.append(key)
                    break
                #end if
            #next
            for key in keys:
                if key == "梁符号":
                    keys2.append(key)
                    break
                #end if
            #next
            if len(梁符号2)>0:
                for key in keys:
                    if key == "梁符号2":
                        keys2.append(key)
                        break
                    #end if
                #next    
            #end if
            for key in keys:
                if key != "階" and key != "梁符号" and key != "梁符号2":
                    keys2.append(key)
                #end if
            #next
            keys = keys2

            # 各keyのデータが何番目にあるかを抽出する。
            NumberOfKey = []
            for j, key in enumerate(keys):
                n1 = []
                for k in range(len(data)):
                    if key == data[k][0]:
                        n1.append(k)
                    #end if
                #next
                NumberOfKey.append(n1)
            #next

            beam2 = []
            for j, data in enumerate(beam):
                dic = {}
                for k ,Number in enumerate(NumberOfKey):
                    for num in Number:
                        dic[keys[k]] = data[num][1]
                    #next
                #next
                beam2.append(dic)
            #next
            BeamData2.append(beam2)
            
        #next
        BeamData = BeamData2


        #===================================
        # 柱部材の抽出
        #===================================
        Section = []
        Section2 = []
        ColumnData = []
        dn = len(柱符号)
        if dn > 0 :
            flag = [0] * dn
            for i in range(dn):
                if flag[i] == 0 :
                    text0 = 柱符号[i]["text"]
                    row0 = 柱符号[i]["row"]  # 行位置を記憶
                    xm0 = 柱符号[i]["xm"]    # 梁断面位置Ｘ座標を記憶
                    sn2 = []
                    Section.append([柱符号[i]])
                    dic = {}
                    dic["kind"] = 柱符号[i]["kind"]
                    dic["text"] = 柱符号[i]["text"]
                    dic["number"] = i
                    dic["row"] = 柱符号[i]["row"]
                    dic["xm"] = 柱符号[i]["xm"]
                    dic["y0"] = 柱符号[i]["y0"]
                    dic["item"] = 柱符号[i]["item"]
                    sn2.append([dic])
                    Section2.append(sn2)
                    flag[i] = 1
                    
                #end if
            #next
            xpitch = 0.0
            for Sec in Section:
                if len(Sec)>1 :
                    xpitch = Sec[1]["xm"] - Sec[0]["xm"]
                    break
                #end if
            #next
            if xpitch == 0.0 :
                xpitch = 72.0
            #end if
            #
            for i in range(len(Section)):
                for j in range(len(Section[i])):
                    Section[i][j]["rmax"] = -1
                #next
                row0 = Section[i][0]["row"]  # 行位置を記憶
                xm0 = Section[i][0]["xm"]    # 梁断面位置Ｘ座標を記憶

                # 同じ列に再び梁断面位置がある場合は別の梁部材表であると判断し、データの終端行位置をその行−２とする。
                for j in range(i + 1, len(Section)): # 次の梁断面位置から比較する。
                    row = Section[j][0]["row"]
                    xm = Section[j][0]["xm"]
                    if row != row0 and abs(xm - xm0) < xpitch/2:
                        for k in range(len(Section[i])):
                            Section[i][k]["rmax"] = row - 2
                        #next
                        break
                    #end if
                #next
                
                # 梁断面位置の代わりに梁断面位置または小梁符号または片持梁符号があった場合も別の梁部材表であると判断し、データの終端行位置をその行−1とする。
                ItemName = ["柱符号","梁符号","梁断面位置","小梁符号","片持梁符号","壁"]
                for Item in ItemName:
                    if Section[i][0]["rmax"] == -1:
                        for j in range(len(locals()[Item])):
                            dataDic1 = locals()[Item][j]
                            row = dataDic1["row"]
                            xm = dataDic1["xm"]
                            if row > row0 and abs(xm - xm0) < xpitch*5:
                                for k in range(len(Section[i])):
                                    Section[i][k]["rmax"] = row - 1
                                #next
                                break
                            #end if
                        #next
                    #end if
                #next

                # 最後までデータの終端行位置が-1の場合は別の梁部材表がないと判断し、データの終端行位置をページの最終行-3とする。
                if Section[i][0]["rmax"] == -1:
                    for j in range(len(Section[i])):
                        Section[i][j]["rmax"] = rowmax
                    #next
                #end if
            #next        

            ElementData = []
            for i in range(len(Section)):
                bn = len(Section[i])
                if bn == 1:
                    xm0 = Section[i][0]["xm"]
                    row0 = Section[i][0]["row"]
                    xmin = Section[i][0]["xm"]-xpitch/2
                    xmax = Section[i][0]["xm"]+xpitch/2
                else:
                    xm0 = (Section[i][0]["xm"] + Section[i][bn - 1]["xm"])/2
                    row0 = Section[i][0]["row"]
                    xmin = Section[i][0]["x0"]-20
                    xmax = Section[i][bn-1]["x1"]+20
                #end if
                
                for j in range(len(Section[i])):
                    Section[i][j]["xm0"] = xm0
                #next  
                
                row1 = Section[i][0]["row"]
                rmax = Section[i][0]["rmax"]
                
                ItemName = ["柱符号2","断面寸法","主筋","フープ筋","かぶり","材料"]
                
                for Item in ItemName:
                    if len(locals()[Item]) > 0:
                        data = []
                        s2 = []
                            
                        for k, d1 in enumerate(locals()[Item]):   # ローカル変数を名前で指定する関数
                            xm = d1["xm"]
                            row = d1["row"]
                            if row >= row1-2 and row <= rmax and xm >= xmin and xm <= xmax:
                                # data.append(d1)
                                dic = {}
                                dic["kind"] = d1["kind"]
                                dic["text"] = d1["text"]
                                dic["number"] = k
                                dic["row"] = d1["row"]
                                dic["xm"] = d1["xm"]
                                dic["y0"] = d1["y0"]
                                dic["item"] = d1["item"]
                                data.append(dic)
                                # Section2[i][j].append(dic)
                            #end if
                            
                        if len(data)>0:
                            if len(data) == 1:
                                dic = {}
                                dic["kind"] = data[0]["kind"]
                                dic["text"] = data[0]["text"]
                                dic["number"] = 0
                                dic["row"] = data[0]["row"]
                                dic["xm"] = data[0]["xm"]
                                dic["y0"] = d1["y0"]
                                dic["item"] = d1["item"]
                                s2.append(dic)
                                for j in range(len(Section2[i])):
                                    Section2[i][j].append(data[0])
                                #next
                            else:
                                r1 = data[0]["row"]
                                data2 = []
                                data1 = [data[0]]
                                for j in range(1,len(data)):
                                    r2 = data[j]["row"]
                                    if r1 == r2 :
                                        data1.append(data[j])
                                    else:
                                        data2.append(data1)
                                        r1 = data[j]["row"]
                                        data1 = [data[j]]
                                    #end if
                                #next
                                if len(data1)>0:
                                    data2.append(data1)
                                #end if
                                for data in data2:
                                    if len(data) == len(Section2[i]):
                                        for j in range(len(Section2[i])):
                                            Section2[i][j].append(data[j])
                                        #next
                                    else:
                                        for j in range(len(Section2[i])):
                                            Section2[i][j].append(data[0])
                                        #next
                                    #end if
                                #end if
                            #end if :(if len(data) == 1:)
                                        
                    #end if :(if len(locals()[Item]) > 0:)
                    
                #next :(for Item in ItemName:)
                                            

                if len(階)>0:
                    ItemName2 = ["階"]
                    
                    for j in range(len(Section[i])):
                        row1 = Section[i][j]["row"]
                        rmax = Section[i][j]["rmax"]
                        xm1 = Section[i][0]["xm"]
                        for Item in ItemName2:
                            # data = []
                            for k, d1 in enumerate(locals()[Item]):   # ローカル変数を名前で指定する関数
                                xm = d1["xm"]
                                row = d1["row"]
                                if row >= row1 and row <= rmax and xm < xm1:
                                    # data.append(d1)
                                    dic = {}
                                    dic["kind"] = d1["kind"]
                                    floor = d1["text"]
                                    if floor[0] == "R":
                                        floor = "R"
                                    else:
                                        if "," in floor:
                                            floor2 = floor.split(",")
                                            floor = ""
                                            for f in floor2:
                                                floor += re.sub(r"\D", "", f) + ","
                                            #next
                                            floor = floor[0:len(floor)-1]
                                        else:
                                            floor = re.sub(r"\D", "", floor)
                                        #end if
                                    #end if
                                    dic["text"] = floor
                                    # dic["text"] = d1["text"]
                                    dic["number"] = k
                                    dic["row"] = d1["row"]
                                    dic["xm"] = d1["xm"]
                                    dic["y0"] = d1["y0"]
                                    dic["item"] = d1["item"]
                                    Section2[i][j].append(dic)
                                #end if
                            #next
                            # Section[i][j][Item] = data
                        #next
                    #next
                
                #end if

            Section22 = []
            for Sec in Section2:
                Sec2 = Sec[0]
                L2 = []
                for dic in Sec2:
                    L2.append(dic["row"])
                #next
                VArray = np.array(L2)      # リストをNumpyの配列に変換
                index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                Sec1 = []
                for d1 in Sec:
                    L22 = []
                    for j in range(len(index1)):
                        L22.append(d1[index1[j]])
                    #next
                    Sec1.append(L22)
                #next
                Section22.append(Sec1)
            #next
            Section2 = Section22

            # 部材表は複数の部材が縦に並んでいるので部材毎に分割する処理
            for Sec in Section2:
                for bdata in Sec:
                    
                    # データの種類を取得
                    kind = []
                    for bd in bdata:
                        if bd["item"] !="":
                            keyname = bd["item"]+":"+bd["kind"]
                        else:
                            keyname = bd["kind"]  
                        #end if
                        if not(keyname in kind):
                            kind.append(keyname)
                        #end if
                        # if not(bd["kind"] in kind):
                        #     kind.append(bd["kind"])
                        # #end if
                    #next
                            
                    # 同じ種類の番号を格納する辞書を作成
                    kindSameN = {}
                    for k in kind:
                        kindSameN[k] = []
                    #next
                    
                    # 同じ種類毎に番号を格納する
                    for j, bd in  enumerate(bdata):
                        if bd["item"] !="":
                            keyname = bd["item"]+":"+bd["kind"]
                        else:
                            keyname = bd["kind"]  
                        #end if
                        for kind1 in kind:
                            if keyname == kind1:
                                kindSameN[kind1].append([j,bd["y0"]])
                                break
                            #end if
                        #next
                    #next
                    
                    # 同じ種類のデータがypitchの2倍以内に並ぶ場合は1組のデータとする。
                    kindSameN2 = {}
                    for j, kind1 in enumerate(kind):
                        ln3 = []
                        ln = kindSameN[kind1]
                        if len(ln) == 1:
                            kindSameN2[kind1] = [[ln[0][0]]]
                        else:
                            ln2 = []
                            n0 = ln[0][0]
                            y0 = ln[0][1]
                            ln2.append(n0)
                            for k in range(1,len(ln)):
                                n1 = ln[k][0]
                                y1 = ln[k][1]
                                if abs(y0-y1) < ypitch * 2.0 :
                                    ln2.append(ln[k][0])
                                    n0 = ln[k][0]
                                    y0 = ln[k][1]
                                else:
                                    ln3.append(ln2)
                                    ln2 = []
                                    n0 = ln[k][0]
                                    y0 = ln[k][1]
                                    ln2.append(n0)
                                #end if
                            #next
                            if len(ln2)>0 :
                                ln3.append(ln2)
                            #end if
                            
                        #end if
                        if len(ln3)>0 :
                            kindSameN2[kind1] = ln3
                        #end if
                    #next
                    
                    # 主筋の数を1列にあるデータ数とする。
                    kindSameNMax = len(kindSameN2["主筋"])
                    # kindSameNMax = len(kindSameN2["断面寸法"])


                    # # 材料は主筋とフープ筋の2カ所に記載される場合があり、そのときは材料1と材料2に分ける。
                    # if len(材料)>0:
                    #     if len(kindSameN2["材料"]) == kindSameNMax*2:
                    #         d0 = kindSameN2["材料"]
                    #         d1 = []
                    #         d2 = []
                    #         for j, d in enumerate(d0):
                    #             if j % 2 == 0:
                    #                 d1.append(d)
                    #             else:
                    #                 d2.append(d)
                    #             #end if
                    #         #next
                    #         kindSameN2["材料1"] = d1
                    #         kindSameN2["材料2"] = d2
                    #     else:
                    #         kindSameN2["材料1"] = kindSameN2["材料"]
                    #     #end if
                    #     removed_value = kindSameN2.pop('材料')
                    # #end if :(if len(材料)>0:)

                    # キーの順番が乱れているので再度行の順番に並び替える。
                    keys = list(kindSameN2.keys())
                    L2 = []
                    for key in keys:
                        L2.append(kindSameN2[key][0][0])
                    #next
                    VArray = np.array(L2)      # リストをNumpyの配列に変換
                    index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                    keys1 = []
                    for j in range(len(index1)):
                        keys1.append(keys[index1[j]])
                    #next
                    keys = keys1
                    
                    # 同じ梁のデータを梁断面位置の順番でひとつにまとめる。
                    beam2 = []            
                    for bdata in Sec:
                        beam = []
                        for Beami in range(kindSameNMax):
                            dataDic1 = []
                            for key in keys:
                                nn = kindSameN2[key]
                                if len(nn) == 1:
                                    n2 = 0
                                    n1 = nn[0]
                                    for n in n1:
                                        n2 += 1
                                        data = bdata[n]
                                        if len(nn[0])>1 :
                                            if not("階" in key) and not("柱符号" in key):
                                                key2 = key + "-" + str(n2)
                                            else:
                                                key2 = key
                                            #end if
                                        else:
                                            key2 = key
                                        #end if
                                        dataDic1.append([key2,data["text"]])
                                    #nex
                                else:
                                    n2 = 0
                                    n1 = nn[Beami]
                                    for n in n1:
                                        n2 += 1
                                        data = bdata[n]
                                        if len(nn[Beami])>1 :
                                            if not("階" in key) and not("柱符号" in key):
                                                key2 = key + "-" + str(n2)
                                            else:
                                                key2 = key
                                            #end if
                                        else:
                                            key2 = key
                                        #end if
                                        dataDic1.append([key2,data["text"]])
                                    #next
                                #next
                                #end if
                            next
                        




                            # dataDic1 = []
                            # for key in keys:
                            #     nn = kindSameN2[key]
                            #     if len(nn[j]) == 1:
                            #         data = bdata[nn[0][0]]
                            #         key2 = key
                            #         dataDic1.append([key,data["text"]])
                            #     else:
                            #         n2 = 0
                            #         for n in nn[j]:
                            #             n2 += 1
                            #             data = bdata[n]
                            #             if len(nn[j])>1 :
                            #                 if not("階" in key) and not("柱符号" in key):
                            #                     key2 = key + "-" + str(n2)
                            #                 else:
                            #                     key2 = key
                            #                 #end if
                            #             else:
                            #                 key2 = key
                            #             #end if
                            #             dataDic1.append([key2,data["text"]])
                            #         #next
                            #     #end if
                            # #next
                        
                            # 表に階のデータが無い場合は梁符号から作成し、追加する。
                            # FG1 -> 1FL  4G1 -> 4FL
                            if not("階" in keys):
                                hname = bdata[kindSameN2["柱符号"][0][0]]["text"]
                                if hname[0] == "F":
                                    floorName = "1FL"
                                else:
                                    floorName = hname[0] + "FL"
                                #end if
                                dataDic1.append(["階",floorName])
                            #end if
                            beam.append(dataDic1)

                        #next :(for j in range(kindSameNMax):)
                            
                        beam2.append(beam)

                    #next :(for bdata in Sec:)
                        
                #next :(for bdata in Sec:)
                
                n = len(beam2[0])
                m = len(beam2)
                for i in range(n):
                    beam3= []
                    for j in range(m):
                        beam3.append(beam2[j][i])
                    #next
                    ColumnData.append(beam3)
                #next
            # #next
        #end if    

        #=====================================================================
        # 柱データを辞書形式に変換する処理
        #=====================================================================
        
        ColumnData2 = []
        for i,beam in enumerate(ColumnData):
            # 梁データ毎にkeyを取り出す。
            keys = []
            for j, data in enumerate(beam):
                for k in range(len(data)):
                    if not(data[k][0] in keys):
                        keys.append(data[k][0])
                    #end if
                #next
            #next
            # keyの先頭を"階"データにする。
            keys2 = []
            for key in keys:
                if key == "階":
                    keys2.append(key)
                    break
                #end if
            #next
            for key in keys:
                if key != "階":
                    keys2.append(key)
                #end if
            #next
            keys = keys2

            # 各keyのデータが何番目にあるかを抽出する。
            NumberOfKey = []
            for j, key in enumerate(keys):
                n1 = []
                for k in range(len(data)):
                    if key == data[k][0]:
                        n1.append(k)
                    #end if
                #next
                NumberOfKey.append(n1[0])
            #next

            beam2 = []
            for j, data in enumerate(beam):
                dic = {}
                for k in range(len(data)):
                    dic[keys[k]] = data[NumberOfKey[k]][1]
                    #end if
                #next
                beam2.append(dic)
            #next
            ColumnData2.append(beam2)
            
        #next
        ColumnData = ColumnData2

        return BeamData , ColumnData
    
    #end def

    def Save_Element_Data(self, filename, BeamData, ColumnData):

        ja_cvu_normalizer = JaCvuNormalizer()
    
        if len(BeamData)>0 or len(ColumnData)>0 and filename != "":

            # filename = os.path.splitext(pdfname)[0] + "_部材リスト" + ".csv"

            # 異字体の修正
            filename = ja_cvu_normalizer.normalize(filename) 

            with open(filename, 'w', encoding='shift_jis') as f:
                writer = csv.writer(f)
                title = "[ " + filename + " ]"
                writer.writerow([title])
                writer.writerow("")

                if len(BeamData)>0:
                    bn = len(BeamData)
                    writer.writerow(["[ 梁部材リスト ]"])
                    writer.writerow("")
                    n = 0
                    for beams in BeamData:
                        n += 1
                        num = ["n= "+str(n)+"/"+str(bn)]
                        keys = list(beams[0].keys()) 
                        keys2 = num + keys
                        writer.writerow(keys2)
                        for beam in beams:
                            data = []
                            data.append("")
                            for key in keys:
                                data.append(beam[key])
                            #next
                            writer.writerow(data)
                        #next
                        writer.writerow("")
                    #next
                #end if
                writer.writerow("")

                if len(ColumnData)>0:
                    cn = len(ColumnData)
                    writer.writerow(["[ 柱部材リスト ]"])
                    writer.writerow("")
                    n = 0
                    for Colums in ColumnData:
                        n += 1
                        num = ["n= "+str(n)+"/"+str(cn)]
                        keys = list(Colums[0].keys()) 
                        keys2 = num + keys
                        writer.writerow(keys2)
                        for Colum in Colums:
                            data = []
                            data.append("")
                            for key in keys:
                                data.append(Colum[key])
                            #next
                            writer.writerow(data)
                        #next
                        writer.writerow("")
                    #next
                #end if

            #end with
        #end if
    #end def

#end class

#======================================================================================
#
#   メインルーチン
#
#======================================================================================

if __name__ == '__main__':

    time_sta = time.time()  # 開始時刻の記録

    CR = ChartReader()

    Folder1 = "PDF"

    pdffname =[]

    # pdffname.append("構造図テストデータ.pdf")
    # pdffname.append("構造計算書テストデータ.pdf")

    # pdffname.append("(仮称)阿倍野区三明町2丁目マンション新築工事_構造図.pdf")
    # pdffname.append("(2)Ⅲ構造計算書(2)一貫計算編電算出力.pdf")
    # pdffname.append("(2)Ⅲ構造計算書(2)一貫計算編電算出力のコピー.pdf")
    
    pdffname.append("02構造図.pdf")
    pdffname.append("02一貫計算書（一部）.pdf")


    # pdfname = "構造図テストデータ.pdf"
    # pdfname = "構造計算書テストデータ.pdf"
    
    # pdfname = "(仮称)阿倍野区三明町2丁目マンション新築工事_構造図.pdf"
    # pdfname = "(2)Ⅲ構造計算書(2)一貫計算編電算出力.pdf"
    
    # pdfname = "構造計算書の部材表.pdf"
    # pdfname = "構造計算書の部材表（柱のみ）.pdf"
    # pdfname = "構造計算書の基礎梁のみ.pdf"
    
    # pdfname = "01(2)Ⅲ構造計算書(2)一貫計算編電算出力.pdf"
    # pdfname = "03sawarabi 京都六角 計算書 (事前用).pdf"
    # pdfname = "03構造計算書（部材リストのみ）.pdf"
    # pdfname = "構造計算書断面リスト1.pdf"
    
    # pdfname = "02一貫計算書（一部）.pdf"

    Folder2 = "CSV"
    for pdf in pdffname:
        BeamData , ColumnData = CR.Read_Elements_from_pdf(Folder1 + "/"+ pdf)
        
        if len(BeamData) > 0 or len(ColumnData) > 0:

            filename = os.path.splitext(pdf)[0] + "_部材リスト" + ".csv"
            filename = Folder2 + "/"+ filename

            CR.Save_Element_Data(filename, BeamData , ColumnData )

        #end if
    #next
    
    time_end = time.time()  # 終了時刻の記録
    print("処理時間 = {} sec".format(time_end - time_sta))
    
#end if
    
