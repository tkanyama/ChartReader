#********************************************************************
#
#   PDFの部材リストからデータを読み取るクラス
#
#********************************************************************

# pip install pdfplumber
import pdfplumber
from io import StringIO
import time
import copy
import pickle
from pypdf import PdfReader as PR2 # 名前が上とかぶるので別名を使用

# pip install numpy matplotlib scipy
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import re
import sys,csv,os
import logging

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

#**************************************************************************************************
#
#   構造図および構造計算書の部材表から部材データを読み取るクラス。
#
#**************************************************************************************************

class ChartReader:

    #============================================================================
    #　インスタンスの初期化関数
    #============================================================================
    def __init__(self):

        # self.a = "abc"
        # # b = locals()
        # # c = b["self"]
        # # keys = c."a"
        # # d = c.locals()["a"]
        # print(getattr(self, "a"))

        self.MemberPosition = {}    # 部材符号と諸元データの辞書locals()[Item])getattr(self, var)
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

        
    #============================================================================
    #　梁データまたは柱データを階数および記号の順で並び替える関数
    #============================================================================
    def Sort_Element(self, E_data, ItemName="梁符号", sc=-1):

        if len(E_data)>1:
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
                        if floor2[0].isnumeric():
                            L2.append(int(floor2[0]))
                        else:
                            L2.append(0)
                        #end if
                        
                    else:
                        if floor.isnumeric():
                            L2.append(int(floor))
                        else:
                            L2.append(0)
                        #end if
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
        else:
            return E_data
        #end if
    
    #end def

    #============================================================================
    #　PDFのページから単語を抽出する関数
    #============================================================================
    def Read_Word_From_Page(self, page):

        # 記号パターンから種類を特定するツールPatternCheckのインスタンスを作成
        pCheck = PatternCheck()


        # wordデータを高さy1の順に並び替え
        # ページの座標系はＸ方向は左から右方向が正、Ｙ方向は上から下方向が正

        page_word = []
        Lheight = []
        for obj in page.extract_words():
            text = obj['text']
            x0, y0, x1, y1 = obj['x0'], obj['top'], obj['x1'], obj['bottom']
            page_word.append({
                'text': text, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                'xm': (x0 +x1)/2 ,'h': (y1 - y0),'w': (x1 - x0),'pitch': (x1 - x0)/len(text)
                })
            Lheight.append(y1)
        #end if

        # ページ中の全ての単語を高さの順位並べ替える。
        VArray = np.array(Lheight)      # リストをNumpyの配列に変換
        index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        page_word2 = []    
        for j in range(len(index1)):
            page_word2.append(page_word[index1[j]])
        #next
        page_word = page_word2


        # 高さy1の差が0.1ポイント（0.035mm)未満のwordを同じ行のリストにまとめる
        row = 1
        line_word = []
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
        
        # さらに高さの差が1ポイント以内の行を同じ行にまとめる
        page_lines2 = []
        rowi = 0        
        ln = len(page_lines)
        i = 0
        AddFlag = []
        # print()
        # print(len(page_lines))
        flag0 = True
        while i < ln:
            line0 = page_lines[i]

            y0 = line0[0]["y0"]
            flag1 = True
            flag2 = False
            while flag1:
                i += 1
                if i > ln -1 :
                    flag0 = False
                    break
                #end if
                line1 = page_lines[i]
                y1 = line1[0]["y0"]
                if abs(y1 - y0)<1.0 :
                    line0 += line1
                    
                    flag2 = True
                    if i > ln -1 :
                        flag0 = False
                        page_lines2.append(line0)
                        break
                    #end if
                else:
                    page_lines2.append(line0)
                    if DbPrint:
                        t1 = ""
                        for D in line0:
                            t1 += D["text"]
                        print(t1)

                    if flag2:
                        AddFlag.append(1)
                    else:
                        AddFlag.append(0)
                    #end if
                    rowi += 1
                    flag1 = False
                #end if
            #end while
        #end while
        # print(len(page_lines2))
        page_lines = page_lines2


        # 合成した各行のwordをx0の順に並べ替える。
        page_lines2 = []
        for rowi, line in enumerate(page_lines):
            line2 = []
            xx = []
            for d1 in line:
                xx.append(d1["x0"])
            #next
            VArray = np.array(xx)      # リストをNumpyの配列に変換
            index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
            for j in range(len(index1)):
                line[index1[j]]["row"] = rowi   # 並び替えるついでに行位置rowも修正
                line2.append(line[index1[j]])
            #next
            page_lines2.append(line2)
        #next
        page_lines = page_lines2


        # 各行の近接するwordをひとつのワードに統合する。
        # 結合条件は 単語間の距離が文字ピッチのc(=1.5)倍以内であれば結合する。
        c = 1.5    

        page_lines3 = []

        """
        デバッグプリントするときはここでブレークポイント
        """
        for line in page_lines:
            if DbPrint:
                name = input("enter to Continue: ")
                
            # デバッグプリント============
            if DbPrint:
                t1 = ""
                for L1 in line:
                    t1 += "["+L1["text"]+"] "
                print(t1,len(line))
            #==========================

            if len(line)>1 :
                line2 = []
                # word0 = {}
                wn = len(line)
                wi = 0
                while wi < wn - 1:
                    word0 = line[wi]
                    pitch = word0["pitch"]
                    text0 = word0["text"]
                    x00 = word0["x0"]
                    x01 = word0["x1"]
                    y00 = word0["y0"]
                    
                    word1 = line[wi + 1]
                    text1 = word1["text"]
                    x10 = word1["x0"]
                    x11 = word1["x1"]
                    y10 = word1["y0"]

                    text = text0 + " " + text1

                    addflag = False

                    # 単語間の高さの差が1ポイント以内で、かつ、右端と左端の距離が文字幅の1.5倍以内であれば結合する。
                    if abs(y00 - y10)<1.0:
                        if (x10 - x01) <= pitch * c:
                            addflag = True

                    # 条件を満たした場合は単語を結合する。
                    if addflag :
                        word0["text"] =  text
                        word0["x1"] = x11
                        word0["xm"] = (x00 + x11)/2
                        word0["pitch"] = (x01 + x11) / len(text)
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
            if DbPrint:     # デバッグプリント
                t2 = ""
                for L1 in line2:
                    t2 += "["+L1["text"]+"] "
                print(t2,len(line2))

            # 距離が離れていて2つの単語を結合したものが登録部材名に合致する場合は結合する。
                
            if len(line2)>1 :
                line3 = []
                # word0 = {}
                wn = len(line2)
                wi = 0
                while wi < wn - 1:
                    word0 = line2[wi]
                    pitch = word0["pitch"]
                    text0 = word0["text"]
                    x00 = word0["x0"]
                    x01 = word0["x1"]
                    y00 = word0["y0"]
                    
                    word1 = line2[wi + 1]
                    text1 = word1["text"]
                    x10 = word1["x0"]
                    x11 = word1["x1"]
                    y10 = word1["y0"]

                    text = text0 + " " + text1

                    addflag = False

                    if abs(y00 - y10)<1.0:
                        if pCheck.isMember("断面寸法",text):        # [500 x 1,500]
                            addflag = True
                        elif pCheck.isMember("断面寸法2",text) :     # [b x D]
                            addflag = True
                        elif pCheck.isMember("梁断面位置",text) :   # [Y1 端]
                            addflag = True
                        elif pCheck.isMember("フープ筋",text):      # [-D13@ 100] [-D13 @100]
                            addflag = True
                        elif pCheck.isMember("主筋",text) :         # [10-D25 + 10-D15] [10-D25 , 10-D15]
                            addflag = True
                        #end if
                    #end if

                    # 条件を満たした場合は単語を結合する。
                    if addflag :
                        word0["text"] =  text
                        word0["x1"] = x11
                        word0["xm"] = (x00 + x11)/2
                        word0["pitch"] = (x00 + x11) / len(text)
                        line3.append(word0)
                        wi += 1
                    else:
                        line3.append(word0)
                    #end if
                    wi += 1
                #end while
                if wi < wn:
                    line3.append(line2[wi])
                #end if
            else:
                line3=line2
            #end if
            if DbPrint:
                t2 = ""
                for L1 in line3:
                    t2 += "["+L1["text"]+"] "
                print(t2,len(line3))
                print()

            if len(line3)>0:
                page_lines3.append(line3)
            #end if
        #next   for line in page_lines:

        page_lines = page_lines3

        return page_lines
    
    #end def
        
    #============================================================================
    #　複数ページのPDFファイルから梁データまたは柱データを抽出し、リストを返す関数
    #============================================================================
    def Read_Members_from_pdf(self, pdf_path,stpage1=1,edpage1=100):

        # CR = ChartReader()
        BeamData = []
        ColumnData = []

        # try:
        if stpage1>0:
            stpage = stpage1
        else:
            stpage = 1
        #end if
        if edpage1 > 0:
            edpage = edpage1
        else:
            edpage = 100
        #end if
            
        with pdfplumber.open(pdf_path) as pdf:

            BeamData = []
            ColumnData = []
            for pageN, page in enumerate(pdf.pages):
                if pageN >= stpage -1 and pageN <= edpage -1:

                
                    print("page = {}".format(pageN+1),end="")

                    # page_lines = self.Read_Word_From_Page(page)

                    BeamData1, ColumnData1 = self.ElementFinder(page)

                    print("  梁データ:{}個 , 柱データ:{}個".format(len(BeamData1), len(ColumnData1)))
                    if len(BeamData1) > 0:
                        BeamData += BeamData1
                    #end if
                    if len(ColumnData1) > 0:
                        ColumnData += ColumnData1
                    #end if
                #end if
                
            #next
            #end with
    
            # 階および符号名でデータの並び替え
                        
            BeamData = self.Sort_Element(BeamData, ItemName="梁符号", sc=-1)    # sc=-1:降順,sc=1:昇順

            ColumnData = self.Sort_Element(ColumnData, ItemName="柱符号",sc=-1)  # sc=-1:降順,sc=1:昇順
        # except:
        #     print('Exception!')
        #     flag = False
        # #end try
        return BeamData, ColumnData

    # #end def


    #============================================================================
    #　pdfファイルから梁データと柱データを抽出し、pickleファイルに書き出す関数
    #============================================================================
    def Read_and_Save_Members_To_Pickle(self, pdf_path, pickle_path,stpage1=1 ,edpage1=100):

        if pdf_path =="" or pickle_path == "":
            return False
        #end if
        
        flag = True
        try:
            if stpage1>0:
                stpage = stpage1
            else:
                stpage = 1
            #end if
            if edpage1 > 0:
                edpage = edpage1
            else:
                edpage = 100
            #end if
            
            with pdfplumber.open(pdf_path) as pdf:

                BeamData = []
                ColumnData = []
                for pageN, page in enumerate(pdf.pages):

                    if pageN >= stpage -1 and pageN <= edpage -1:
                        print("page = {}".format(pageN+1),end="")

                        # page_lines = self.Read_Word_From_Page(page)

                        BeamData1, ColumnData1 = self.ElementFinder(page)

                        print("  梁データ:{}個 , 柱データ:{}個".format(len(BeamData1), len(ColumnData1)))
                        if len(BeamData1) > 0:
                            BeamData += BeamData1
                        #end if
                        if len(ColumnData1) > 0:
                            ColumnData += ColumnData1
                        #end if
                    #end if
                #next
            #end with
            
            # 階および符号名でデータの並び替え
            if len(BeamData) > 0 or len(ColumnData) >0 :

                BeamData = self.Sort_Element(BeamData, ItemName="梁符号", sc=-1)    # sc=-1:降順,sc=1:昇順

                ColumnData = self.Sort_Element(ColumnData, ItemName="柱符号",sc=-1)  # sc=-1:降順,sc=1:昇順

                self.Save_MemberData_Picle(pickle_path, BeamData, ColumnData)

                flag = True
            else:
                flag = False
            #end if
        except:
            print('Exception!')
            flag = False
        #end try

        return flag

    # #end def



    #============================================================================
    #　PDFのページから単語データを抽出する関数
    #============================================================================
    def FindMember(self,PageWordData):

        # 文字列パターンを用いてデータの種類を判別するオブジェクトの作成
        pCheck = PatternCheck()
        # データの種類リスト（例：断面寸法）
        KeyNames = pCheck.KeyNames
        
        
        # 異体字正規化モジュール
        ja_cvu_normalizer = JaCvuNormalizer()
                        
        # words = []
        wordsByKind = {}
        for keyname in KeyNames:
            wordsByKind[keyname] = []
        #next

        # 各行のすべての単語のパターンチェックを行い、分類ごとの記号リストwordsByKindを作成する。
            
        self.ypitch = 0
        for i, LineWord in enumerate(PageWordData):
            # line = []
            for j, word in enumerate(LineWord):
                t1 = word["text"]
                # print(t1)
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
                    if abs(word["y0"]-word["y1"])>self.ypitch:
                        self.ypitch = abs(word["y0"]-word["y1"])
                    #end if
                #end if
            #next
            # if len(line)>0:
            #     wordsByKind[kind].append(line)
            # #end if
        #next

        # ページの最終行を抽出
        self.rowmax = len(PageWordData)

        # データリストwordsByKindから各記号のリストを抽出する。

        self.梁符号1 = wordsByKind["梁符号1"]
        self.梁符号2 = wordsByKind["梁符号2"]

        # 梁符号1がある場合は梁符号1を梁符号とする。
        self.梁符号 = []
        if len(self.梁符号1) > 0:
            self.梁符号 = self.梁符号1
        else:
            # 梁符号1が無く、梁符号2はある場合は梁符号2を梁符号とする。
            if len(self.梁符号2) > 0:
                flag = False
                for d in self.梁符号2:
                    if "FG" in d["text"]:
                        flag = True
                    #end if
                #next
                if flag:
                    self.梁符号 = self.梁符号2
                    self.梁符号2 = []
                #end if
            #end if
        #end if
        #記号の種類
        for i in range(len(self.梁符号)):
            self.梁符号[i]["kind"] = "梁符号"
        #next

        self.小梁符号 = wordsByKind["小梁符号"]
        self.片持梁符号 = wordsByKind["片持梁符号"]
        self.項目名1 = wordsByKind["項目名1"]
        self.項目名2 = wordsByKind["項目名2"]
        # 主筋項目名 = wordsByKind["主筋項目名"]
        # 材料項目名 = wordsByKind["材料項目名"]
        self.断面寸法 = wordsByKind["断面寸法"]
        self.コンクリート強度 = wordsByKind["コンクリート強度"]
        self.フープ筋 = wordsByKind["フープ筋"]
        self.主筋 = wordsByKind["主筋"]
        self.腹筋 = wordsByKind["腹筋"]
        self.材料 = wordsByKind["材料"]
        self.階 = wordsByKind["階"]
        self.壁 = wordsByKind["壁"]
        self.日付 = wordsByKind["日付"]
        self.かぶり = wordsByKind["かぶり"]
        self.柱符号 = wordsByKind["柱符号"]
        self.柱符号2 = wordsByKind["柱符号2"]
        self.構造計算書 = wordsByKind["構造計算書"]
        self.同上 = wordsByKind["同上"]
        self.断面リスト = wordsByKind["断面リスト"]
        self.階上項目 = wordsByKind["階上項目"]

        # 同じ行にある柱符号から表のコラム間隔self.ColumnPitchを抽出する。
        self.ColumnPitch = 0
        if len(self.柱符号)>0:
            itemXmin = 10000
            self.ColumnPitch = 0
            xm1 = self.柱符号[0]["xm"]
            x0 = self.柱符号[0]["x0"]
            if x0 < itemXmin:
                itemXmin = x0
            #end if
            row1 = self.柱符号[0]["row"]
            for i in range(1,len(self.柱符号)):
                xm2 = self.柱符号[i]["xm"]
                row2 = self.柱符号[i]["row"]
                
                if row2 == row1 :
                    self.ColumnPitch = abs(xm1 - xm2)
                    break
                #end if
            #next
        #end if
                
        # 同じ行にある梁符号から表のコラム間隔self.beamPitchを抽出する。
        self.beamPitch = 0
        if len(self.梁符号)>0:
            itemXmin = 10000
            self.beamPitch = 0
            xm1 = self.梁符号[0]["xm"]
            x0 = self.梁符号[0]["x0"]
            if x0 < itemXmin:
                itemXmin = x0
            #end if
            row1 = self.梁符号[0]["row"]
            for i in range(1,len(self.梁符号)):
                xm2 = self.梁符号[i]["xm"]
                row2 = self.梁符号[i]["row"]
                
                if row2 == row1 :
                    self.beamPitch = abs(xm1 - xm2)
                    break
                #end if
            #next
        #end if
                
        # self.beamPitchまたはself.ColumnPitchから表のコラム間隔self.itemPitchを決定する。
        self.itemPitch = 0
        if self.beamPitch>0:
            self.itemPitch = self.beamPitch
        else:
            if self.ColumnPitch>0:
                self.itemPitch = self.ColumnPitch
            #end if
        #end if
        if self.itemPitch == 0:
            self.itemPitch = 72
        #end if

        # すべての梁符号からx0およびy0の最小値を抽出する。
        itemXmin = 10000
        itemYmin = 10000
        if len(self.梁符号)>0:
            for d in self.梁符号:
                x0 = d["x0"]
                y0 = d["y0"]
                if x0 < itemXmin:
                    itemXmin = x0
                #end if
                if y0 < itemYmin:
                    itemYmin = y0
                #end if
            #next

            self.梁断面位置 = wordsByKind["梁断面位置"]
            if len(self.梁断面位置) > 1:
                # 梁断面位置のうち梁符号より上にあるものは削除する。
                self.梁断面位置2 = []
                for d in self.梁断面位置:
                    y1 = d["y1"]
                    if y1 > itemYmin:
                        self.梁断面位置2.append(d)
                    #end if
                #next
                self.梁断面位置 = self.梁断面位置2
                
                # 同じ行にある梁断面位置から表のコラム間隔self.beamPitchを抽出する。
                self.beamPitch = 0
                xm1 = self.梁断面位置[0]["xm"]
                x0 = self.梁断面位置[0]["x0"]
                if x0 < itemXmin:
                    itemXmin = x0
                #end if
                row1 = self.梁断面位置[0]["row"]
                for i in range(1,len(self.梁断面位置)):
                    xm2 = self.梁断面位置[i]["xm"]
                    row2 = self.梁断面位置[i]["row"]
                    
                    if row2 == row1 :
                        self.beamPitch = abs(xm1 - xm2)
                        break
                    #end if
                #next
            
            else:
                # 表データが1列の場合は表の横ピッチは72とする。
                self.beamPitch = 72
            #end if
        else:
            self.梁断面位置 = []
        #end if ja_cvu_normalizer.normalize(Line) 
            

        if len(self.梁断面位置):
            # 文字の異字体の変換を行う。（面）
            self.梁断面位置2 = []
            for data in self.梁断面位置:
                data["text"] = ja_cvu_normalizer.normalize(data["text"]) 
                self.梁断面位置2.append(data)
            #next
            self.梁断面位置 = self.梁断面位置2

            # 梁断面位置の下側に主筋もフープ筋ないものは削除する。
            self.梁断面位置2 = []
            for d in self.梁断面位置:
                # print(d["text"])
                row = d["row"]
                xm = d["xm"]
                flag = False
                if len(self.主筋)>0:
                    for d1 in self.主筋:
                        row1 = d1["row"]
                        xm1 = d1["xm"]
                        if row < row1 and abs(xm - xm1)<self.beamPitch * 2:
                            flag = True
                            break
                        #end if
                    #next
                #end if
                
                if flag == False:
                    if len(self.フープ筋)>0:
                        for d1 in self.フープ筋:
                            row1 = d1["row"]
                            xm1 = d1["xm"]
                            if row < row1 and abs(xm - xm1)<self.beamPitch * 2:
                                flag = True
                                break
                            #end if
                        #next
                    #end if
                #end if
                if flag :
                    self.梁断面位置2.append(d)
                #end if
            #next
            self.梁断面位置 = self.梁断面位置2

        # 梁データが無い場合は柱符号で項目名の境界[itemXmin]を決定する。
        if len(self.柱符号)>0 and itemXmin == 10000:
            for d in self.柱符号:
                x0 = d["x0"]
                if x0 < itemXmin:
                    itemXmin = x0
                #end if
            #next
        #end if
        


        if itemXmin == 10000:
            itemXmin = 72*2
        #end if                         getattr(self, "a")
        
        # self.登録外項目 = []
        # itemKey = []
        # for i, LineWord in enumerate(PageWordData):
        #     word = LineWord[0]
        #     text = word["text"]
        #     x1 = word["x1"]
        #     # if not(text.isnumeric()) and len(text)>= 2 and pCheck.isMember("項目名1",text) == False and x1<itemXmin:
        #     if not(text.isnumeric()) and len(text)>= 2 and pCheck.isMember("項目名1",text) == False and text != "断面":
        #         # if not(text in itemKey):
        #         self.登録外項目.append(word)
        #         # itemKey.append(text)
        #     #end if
        # #next

        # PDFが構造計算書の場合で「断面リスト」の単語がない場合はそのページの処理を中止する。
        if len(self.構造計算書)>0:
            if len(self.断面リスト)==0 :
                # BeamData = []
                # ColumnData = []
                return False
            #end if
        #end if

        # 主筋データが無い場合、又は、梁符号も柱符号も両方がない場合はそのページの処理を中止する。
        flag = False
        flag = flag or len(self.主筋) == 0
        flag = flag or len(self.断面寸法) == 0
        flag = flag or (len(self.梁符号) == 0 and len(self.柱符号) == 0)
        flag = flag or (len(self.梁符号) > 0 and len(self.梁断面位置) == 0)
        
        # if len(self.主筋) == 0 or ((len(self.梁符号) == 0 and len(self.断面位置)==0) and len(self.柱符号) == 0):
        if flag:
            # BeamData = []
            # ColumnData = []
            return False
        #end if

        #======================================
        # 中止条件がない場合は以下の処理に進む。
        #======================================

        # 各部材の副項目名Itemに""を追加
        ItemName = ["同上","梁符号","梁断面位置","梁符号2","主筋","階","断面寸法","かぶり",
                    "柱符号","柱符号2","腹筋","フープ筋","材料","片持梁符号"]
        for Item in ItemName:
            if len(getattr(self, Item))>0:
                for j in range(len(getattr(self, Item))):
                    getattr(self, Item)[j]["item"] = ""
                #next
            #end if
        #next
        
        # 最後列の断面寸法より下側にある階上項目（壁などの別の表に存在する場合など）は削除する
        if len(self.階上項目)>0:
            y0 = self.断面寸法[len(self.断面寸法)-1]["y0"]
            DAN = []
            for d in self.階上項目:
                if d["y0"]<y0:
                    DAN.append(d)
                #end if
            #next
            self.階上項目 = DAN
        #end if
            
        
        #=============================================================
        # 階データには無駄なデータが多数含まれるため、以下の処理でふるい落とす。
        
        if len(self.階) > 0:
        
            if len(self.階上項目)>0:
                # 階上項目（階、符号など）がある場合
                # 階のデータのうち、上端３行と下端３行およびxmが階上項目の直下にないデータは除外する
                階2 = []
                for d in self.階:
                    flag = False
                    xm = d["xm"]
                    if d["row"] > 3 and d["row"] < self.rowmax-3:
                        for d1 in self.階上項目:
                            x0 = d1["x0"]
                            x1 = d1["x1"]
                            if xm > x0 and xm < x1:
                                flag = True
                                break
                            #end if
                        #next
                    #next
                    if flag:
                        階2.append(d)
                    #end if
                #next
                self.階 = 階2 
            else:
                # 階上項目（階、符号など）がない場合
                # 項目名1（主筋など）の左端からコラムピッチ以内もののみ抽出
                階2 = []
                for d in self.階:
                    flag = False
                    xm = d["xm"]
                    if d["row"] > 3 and d["row"] < self.rowmax-3:
                        for d1 in self.項目名1:
                            x0 = d1["xm"] - self.itemPitch*1.0
                            x1 = d1["x1"] #+ self.itemPitch*0.5
                            if xm > x0 and xm < x1:
                                flag = True
                                break
                            #end if
                        #next
                    #next
                    if flag:
                        階2.append(d)
                    #end if
                #next
                self.階 = 階2 
                    
            #end if
                
            flag = [0] * len(self.階)

            # 階データのうち、上下２段（行の差が５行以内）で表記されているものは１つのデータにまとめる
            #  9FL
            #   〜      ->  9FL , 7FL
            #  7FL

            階2 = []

            for i in range(len(self.階)):
                if flag[i] == 0:
                    row0 = self.階[i]["row"]
                    xm0 = self.階[i]["xm"]
                    d0 = self.階[i]
                    text0 = self.階[i]["text"]
                    for j in range(len(self.階)):
                        if i != j and flag[j] == 0 :
                            row = self.階[j]["row"]
                            xm = self.階[j]["xm"]
                            y1 = self.階[j]["y1"]
                            text = self.階[j]["text"]
                            d1 = self.階[j]
                            if row - row0 < 6 and abs(xm - xm0) < 72:
                                text0 += " , " + text
                                d0["text"] = text0
                                d0["y1"] = y1
                                flag[j] = 1
                            #end if
                        #next
                    #next
                    階2.append(d0)
                    flag[i] = 1
                #end if
            #next
            self.階 = 階2 
        #end if

        # 登録外項目も多数抽出されるので、数字だけのもの、1文字のもの、項目名1または項目名2に該当するもの、"断面"を含むものは除外する。
        self.登録外項目 = []
        itemKey = []
        for i, LineWord in enumerate(PageWordData):
            for word in LineWord:
                text = word["text"]
                x1 = word["x1"]
                flag = True
                flag = flag and not(text.isnumeric()) 
                flag = flag and len(text)>= 2 
                flag = flag and (pCheck.isMember("項目名1",text) == False )
                flag = flag and (pCheck.isMember("項目名2",text) == False)
                flag = flag and not("断面" in text)
                
                # if not(text.isnumeric()) and len(text)>= 2 and pCheck.isMember("項目名1",text) == False and pCheck.isMember("項目名2",text) == False and text != "断面":
                if flag:
                    self.登録外項目.append(word)
                #end if
        #next
        
        # 登録外項目のうち階データからコラムピッチの2倍以上離れているものおよび数値を含むもの（FC-33等）を除外
        if len(self.登録外項目):
            d1 = []
            for d2 in self.登録外項目:
                flag = False
                xm0 = d2["xm"]
                for d3 in self.階:
                    xm1 = d3["xm"]
                    if abs(xm0 - xm1) < self.itemPitch*2 and not( bool(re.search(r'\d', d2["text"]))):
                        flag = True
                        break
                    #end if
                #next
                if flag :
                    d1.append(d2)
                #end if
            #nexr
            self.登録外項目 = d1
        #end if

        # フープ筋と材料については表の左側の副項目名を追加（あば筋、帯筋等）
        ItemName = ["フープ筋","材料"]
        for Item in ItemName:
            if len(getattr(self, Item))>0:
                # flag = [0]*len(locals()[Item])
                for j in range(len(getattr(self, Item))):
                    # print(getattr(self, Item)["text"])
                    # if flag[j] == 0:
                    dataDic1 = getattr(self, Item)[j].copy()
                    row = dataDic1["row"]
                    xm = dataDic1["xm"]
                    left0 = dataDic1["x0"]
                    right0 = dataDic1["x1"]
                    top0 = dataDic1["y0"]
                    bottom0 = dataDic1["y1"]
                    text = dataDic1["text"]
                    # print(text)
                    d2 = []
                    for d in self.項目名1:
                        row1 = d["row"]
                        left1 = d["x0"]
                        right1 = d["x1"]
                        xm1 = d["xm"]
                        top1 = d["y0"]
                        bottom1 = d["y1"]

                        # フープ筋より左側にあり、かつ、高さの差が行ピッチの2倍以内にあるものを抽出

                        if right1<left0 and top1-self.ypitch*2.0 < top0 and bottom1+self.ypitch*2.0 > bottom0 :

                            # かつ、以下の語を含むもののみ抽出
                            flag = False
                            if "筋" in d["text"]:   # 主筋、あばら筋、帯筋、上端筋 など
                                flag = True
                            elif "フープ" in d["text"]:
                                flag = True
                            # elif "HOOP" in d["text"]:
                            #     flag = True
                            # elif "スターラップ" in d["text"]:
                            #     flag = True
                            # end if
                            
                            if flag:
                                d2.append(d)
                            #end if
                        #end if
                    #next
                    
                    # さらに登録外項目を探す
                    if len(self.登録外項目)>0:
                        for d in self.登録外項目:
                            row1 = d["row"]
                            left1 = d["x0"]
                            right1 = d["x1"]
                            top1 = d["y0"]
                            bottom1 = d["y1"]

                            # フープ筋より左側にあり、かつ、高さの差が行ピッチの1倍以内にあるものを抽出

                            if right1<left0 and top1-self.ypitch*1.0 < top0 and bottom1+self.ypitch*1.0 > bottom0:
                            
                                d2.append(d)
                                #end if
                            #end if
                        #next
                    #end if
                            
                    # 項目名の決定
                    if len(d2) == 1:
                        # 近くにある項目名がひとつの場合はそれを選択する
                        
                        getattr(self, Item)[j]["item"] = d2[0]["text"]
                        
                    elif len(d2) > 1:
                        # 近くにある項目名が複数有るときは直線距離が最も小さいものを選択する
                        
                        im = -1
                        x00 = dataDic1["xm"]
                        y00 = dataDic1["y0"]
                        x10 = d2[0]["xm"]
                        y10 = d2[0]["y0"]
                        L1 = (x00-x10)**2 + (y00-y10)**2
                        # L1 = (y00-y10)
                        xi = 0
                        for k  in range(1,len(d2)):
                            x10 = d2[k]["xm"]
                            y10 = d2[k]["y0"]
                            L0 = (x00-x10)**2 + (y00-y10)**2
                            # L0 = (y00-y10)
                            if L0 < L1 :
                                xi = k
                            #next
                        #next
                        getattr(self, Item)[j]["item"] = d2[xi]["text"]
                        
                    #end if
                #next for j in range(len(getattr(self, Item))):
            #end if
        #next for Item in ItemName:
        
        # 主筋についても表の左側の副項目名があれば追加（帯筋等）
        ItemName = ["主筋"]
        for Item in ItemName:
            if len(getattr(self, Item))>0:
                # flag = [0]*len(getattr(self, Item))
                for j in range(len(getattr(self, Item))):
                    # if flag[j] == 0:
                    dataDic1 = getattr(self, Item)[j]
                    row = dataDic1["row"]
                    xm = dataDic1["xm"]
                    left0 = dataDic1["x0"]
                    right0 = dataDic1["x1"]
                    top0 = dataDic1["y0"]
                    bottom0 = dataDic1["y1"]
                    d2 = []
                    for d in self.項目名1:
                        row1 = d["row"]
                        left1 = d["x0"]
                        right1 = d["x1"]
                        top1 = d["y0"]
                        bottom1 = d["y1"]

                        # 主筋より左側にあり、かつ、高さの差が行ピッチの2倍以内にあるものを抽出

                        if right1<left0 and top1-self.ypitch*2.0 < top0 and bottom1+self.ypitch*2.0 > bottom0:
                            if "筋" in d["text"] :
                                d2.append(d)
                            #end if
                        #end if
                    #next
                            
                    # 項目名の決定
                    if len(d2) == 1:
                        if not("主" in d2[0]["text"] and "筋" in d2[0]["text"]):
                            #
                            getattr(self, Item)[j]["item"] = d2[0]["text"]
                        else:
                            # 副項目が"主筋"の場合は追加しない
                            getattr(self, Item)[j]["item"] = ""
                        #end if
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
                            if not("主" in d2[im]["text"] and "筋" in d2[im]["text"]) :
                            # if re.fullmatch("\s*主\s*\筋\s*\S*\s*",d2[im]["text"]) == None :
                                getattr(self, Item)[j]["item"] = d2[im]["text"]
                            else:
                                getattr(self, Item)[j]["item"] = ""
                            #end if
                            
                        #end if
                    #end if
                #next for j in range(len(getattr(self, Item))):
            #end if
        #next for Item in ItemName:
        

        # かぶりデータを行で並び替え
        L2 = []
        for i in range(len(self.かぶり)):
            L2.append(self.かぶり[i]["row"])
        #next
        VArray = np.array(L2)      # リストをNumpyの配列に変換
        index1 = np.argsort(VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        L22 = []
        for j in range(len(index1)):
            L22.append(self.かぶり[index1[j]])
        #next
        self.かぶり = L22

        return True
    
    #end def

    #============================================================================
    #　PDFのページから抽出された単語データから梁データを作成する関数
    #============================================================================
    def MakeBeamData(self):
        #===================================
        # 梁部材の抽出
        #===================================
        

        dn = len(self.梁断面位置)
        Section = []
        Section2 = []
        BeamData = []
        if dn > 0 and len(self.梁符号) > 0 and len(self.主筋) > 0 and len(self.断面寸法) > 0:
            flag = [0] * dn
            for i in range(dn):
                if flag[i] == 0 :
                    text0 = self.梁断面位置[i]["text"]
                    row0 = self.梁断面位置[i]["row"]  # 行位置を記憶
                    xm0 = self.梁断面位置[i]["xm"]    # 梁断面位置Ｘ座標を記憶
                    y00 = self.梁断面位置[i]["y0"]  # 行位置を記憶
                    
                    sn2 = []
                    if "全断" in text0 :
                        Section.append([self.梁断面位置[i]])
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        Section2.append(sn2)
                        # Section2.append([[梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]]])
                        flag[i] = 1
                    elif "端部" in text0 or "両端" in text0 :
                        sn = [self.梁断面位置[i]]
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]    # 梁断面位置Ｘ座標を記憶
                                if text1 == "中央" and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*1.2:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
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
                        sn = [self.梁断面位置[i]]
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]    # 梁断面位置Ｘ座標を記憶
                                if text1 == "中央" and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*1.2:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
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
                        sn = [self.梁断面位置[i]]
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if text1 == "先端" and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*1.2:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
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
                        sn = [self.梁断面位置[i]]
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if "中央" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*1.2:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if "右端" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*2.4:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
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
                        sn = [self.梁断面位置[i]]
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if "中央" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*1.2:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if "通端" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*2.4:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
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
                        sn = [self.梁断面位置[i]]
                        dic = {}
                        dic["kind"] = self.梁断面位置[i]["kind"]
                        dic["text"] = self.梁断面位置[i]["text"]
                        dic["number"] = i
                        dic["row"] = self.梁断面位置[i]["row"]
                        dic["xm"] = self.梁断面位置[i]["xm"]
                        dic["y0"] = self.梁断面位置[i]["y0"]
                        dic["item"] = self.梁断面位置[i]["item"]
                        sn2.append([dic])
                        # sn2.append([梁断面位置[i]["text"] , 梁断面位置[i]["kind"] , i , 梁断面位置[i]["row"]])
                        flag[i] = 1
                        # sn2 = []
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if "中央" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*1.2:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
                                    sn2.append([dic])
                                    # sn2.append([梁断面位置[j]["text"] , 梁断面位置[j]["kind"] , j , 梁断面位置[j]["row"]])
                                    flag[j] = 1
                                    break
                                #end if
                            #end if
                        #next
                        for j in range(dn):
                            if flag[j] == 0:
                                text1 = self.梁断面位置[j]["text"]
                                row1 = self.梁断面位置[j]["row"]  # 行位置を記憶
                                xm1 = self.梁断面位置[j]["xm"]    # 梁断面位置Ｘ座標を記憶
                                y10 = self.梁断面位置[j]["y0"]
                                if "端" in text1 and abs(y00-y10)<0.5 and abs(xm0-xm1) < self.beamPitch*2.4:
                                    sn.append(self.梁断面位置[j])
                                    dic = {}
                                    dic["kind"] = self.梁断面位置[j]["kind"]
                                    dic["text"] = self.梁断面位置[j]["text"]
                                    dic["number"] = j
                                    dic["row"] = self.梁断面位置[j]["row"]
                                    dic["xm"] = self.梁断面位置[j]["xm"]
                                    dic["y0"] = self.梁断面位置[j]["y0"]
                                    dic["item"] = self.梁断面位置[j]["item"]
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
                        for j in range(len(getattr(self, Item))):
                            dataDic1 = getattr(self, Item)[j]
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
                        Section[i][j]["rmax"] = self.rowmax 
                    #next
                #end if
            #next

            for i in range(len(Section)):
                bn = len(Section[i])
                if bn == 1:
                    xm0 = Section[i][0]["xm"]
                    row0 = Section[i][0]["row"]
                    xmin = Section[i][0]["xm"]-xpitch/2
                    xmax = Section[i][0]["xm"]+xpitch/2
                    y00 = Section[i][0]["y0"]
                else:
                    xm0 = (Section[i][0]["xm"] + Section[i][bn - 1]["xm"])/2
                    row0 = Section[i][0]["row"]
                    xmin = Section[i][0]["x0"]  #-20
                    xmax = Section[i][bn-1]["x1"]   #+20
                    y00 = Section[i][0]["y0"]
                #end if
                
                for j in range(len(Section[i])):
                    Section[i][j]["xm0"] = xm0
                #nextj , d2 in enumerate(梁符号1)
                
                row1 = Section[i][0]["row"]
                rmax = Section[i][0]["rmax"]
                
                data = []

                flag1 = True
                dd = []
                for k,d1 in enumerate(self.梁符号):   # ローカル変数を名前で指定する関数
                    xm = d1["xm"]
                    row = d1["row"]
                    if row1 > row  and xm >= xmin and xm <= xmax:
                        dd.append(d1)
                    #end if
                #next
                for k,d1 in enumerate(self.片持梁符号):   # ローカル変数を名前で指定する関数
                    xm = d1["xm"]
                    row = d1["row"]
                    if row1 > row  and xm >= xmin and xm <= xmax:
                        dd.append(d1)
                    #end if
                #next
                
                if len(dd) > 0:
                    if len(dd) == 1:
                        dic = {}
                        dic["kind"] = dd[0]["kind"]
                        dic["text"] = dd[0]["text"]
                        dic["number"] = k
                        dic["row"] = dd[0]["row"]
                        dic["xm"] = dd[0]["xm"]
                        dic["y0"] = dd[0]["y0"]
                        dic["item"] = dd[0]["item"]
                        data.append(dic)
                        flag1 = False   # 梁符号1が見つかった場合はFlag1をFalseにする。
                    
                    else:
                        LL = 2000*2000
                        kk = 0
                        for k, d2 in enumerate(dd):
                            xm = d2["xm"]
                            y10 = d2["y0"]
                            L1 = (xm - xm0)**2 + (y10 - y00)**2
                            if L1 < LL:
                                kk = k
                                LL = L1
                            #end if
                        #next
                        dic = {}
                        dic["kind"] = dd[kk]["kind"]
                        dic["text"] = dd[kk]["text"]
                        dic["number"] = k
                        dic["row"] = dd[kk]["row"]
                        dic["xm"] = dd[kk]["xm"]
                        dic["y0"] = dd[kk]["y0"]
                        dic["item"] = dd[kk]["item"]
                        data.append(dic)
                        flag1 = False   # 梁符号1が見つかった場合はFlag1をFalseにする。
                    #end if
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
                
                
                #======================================================================
                #   梁断面位置に各部材を追加する
                #
                ItemName = ["梁符号2","断面寸法","主筋","フープ筋","かぶり","材料","腹筋"]
                
                for Item in ItemName:
                    data = []
                    s2 = []
                    for k, d1 in enumerate(getattr(self, Item)):   # ローカル変数を名前で指定する関数
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
                        # 該当するデータが一つしかない場合は、端部と中央で同じデータを追加する。
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
                                
                        # 該当するデータ複数ある場合は、端部と中央でそれぞれのデータを追加する。
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
                
                #======================================================================
                #   階に各部材を追加する
                #
                if len(self.階)>0:
                    ItemName2 = ["階"]
                    
                    for j in range(len(Section[i])):
                        row1 = Section[i][j]["row"]
                        rmax = Section[i][j]["rmax"]
                        xm1 = Section[i][0]["xm"]
                        for Item in ItemName2:
                            # data = []
                            for k, d1 in enumerate(getattr(self, Item)):   # ローカル変数を名前で指定する関数
                                xm = d1["xm"]
                                row = d1["row"]
                                if row >= row1 and row <= rmax and xm < xm1:
                                    # data.append(d1)
                                    dic = {}
                                    dic["kind"] = d1["kind"]
                                    floor = d1["text"]

                                    # 階はＲ以外は数値のみを追加する。　階の字やFLは削除
                                    if floor[0] == "R":
                                        floor = "R"
                                    else:
                                        #  階が一カ所に複数記載されている場合はカンマ区切りで追加する
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
                                    dic["text"] = floor # 階はＲ以外は数値のみを追加する。　階の字やFLは削除
                                    dic["number"] = k
                                    dic["row"] = d1["row"]
                                    dic["xm"] = d1["xm"]
                                    dic["y0"] = d1["y0"]
                                    dic["item"] = d1["item"]
                                    Section2[i][j].append(dic)
                                #end if
                            #next
                            
                        #next
                    #next
                
                #end if

            #next :(for i in range(len(Section)):)


            # データに梁符号が含まれているものだけを抽出する。        
            Section22 = []
            bn = len(Section2)
            for i in range(bn):
                data = Section2[i][0]
                flag = False
                for d in data:
                    if d["kind"]=="梁符号":
                        flag = True
                        break
                    #end if
                #next
                if flag :
                    Section22.append( Section2[i])
                #end if
            #next
            Section2 = Section22

            """
            ここでブレークポイント
            """
            # Section2を行の順番に並び替える
            Section22 = []
            for Sec in Section2:
                Sec2 = Sec[0]
                L2 = []
                for dic in Sec2:
                    L2.append(dic["row"])
                #next
                VArray = np.array(L2)      
                index1 = np.argsort(VArray) 
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
                                if abs(y0-y1) < self.ypitch*3 :
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
                        
                    for k in kind:
                        if "主筋" in k:
                            mainKey = k
                            break
                        #end if
                    #next

                    # 主筋の数を1列にあるデータ数とする。
                    kindSameNMax = len(kindSameN2[mainKey])

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
            if len(self.梁符号2)>0:
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

        return BeamData
    #end


    #============================================================================
    #　PDFのページから抽出された単語データから柱データを作成する関数
    #============================================================================
    def MakeColumnData(self):
        """
        ここからは柱の処理

        """

        #===================================
        # 柱部材の抽出
        #===================================

        # 柱には梁のような複数の断面はないので柱符号の数の断面データを作成する。

        Section = []
        Section2 = []
        ColumnData = []
        dn = len(self.柱符号)
        if dn > 0 and len(self.主筋) > 0 and len(self.断面寸法) > 0  :
            flag = [0] * dn
            for i in range(dn):
                if flag[i] == 0 :
                    text0 = self.柱符号[i]["text"]
                    row0 = self.柱符号[i]["row"]  # 行位置を記憶
                    xm0 = self.柱符号[i]["xm"]    # 梁断面位置Ｘ座標を記憶
                    sn2 = []
                    Section.append([self.柱符号[i]])
                    dic = {}
                    dic["kind"] = self.柱符号[i]["kind"]
                    dic["text"] = self.柱符号[i]["text"]
                    dic["number"] = i
                    dic["row"] = self.柱符号[i]["row"]
                    dic["xm"] = self.柱符号[i]["xm"]
                    dic["y0"] = self.柱符号[i]["y0"]
                    dic["y1"] = self.柱符号[i]["y1"]
                    dic["x0"] = self.柱符号[i]["x0"]
                    dic["x1"] = self.柱符号[i]["x1"]
                    dic["item"] = self.柱符号[i]["item"]
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
                
                # 表の終端を決める処理
                    
                # 梁断面位置の代わりに梁断面位置または小梁符号または片持梁符号があった場合も別の梁部材表であると判断し、データの終端行位置をその行−1とする。
                ItemName = ["柱符号","梁符号","梁断面位置","小梁符号","片持梁符号","壁"]
                for Item in ItemName:
                    if Section[i][0]["rmax"] == -1:
                        for j in range(len(getattr(self, Item))):
                            dataDic1 = getattr(self, Item)[j]
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
                        Section[i][j]["rmax"] = self.rowmax
                    #next
                #end if
            #next        

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
                y01 = Section[i][0]["y0"]
                
                ItemName = ["同上","柱符号2","断面寸法","主筋","フープ筋","かぶり","材料"]
                
                for Item in ItemName:
                    if len(getattr(self, Item)) > 0:
                        data = []
                        s2 = []
                            
                        for k, d1 in enumerate(getattr(self, Item)):   # ローカル変数を名前で指定する関数
                            xm = d1["xm"]
                            row = d1["row"]
                            y00 = d1["y0"]
                            if y00 > y01-self.ypitch*2 and row >= row1-1 and row <= rmax and xm >= xmin and xm <= xmax:
                                # data.append(d1)
                                dic = {}
                                dic["kind"] = d1["kind"]
                                dic["text"] = d1["text"]
                                dic["number"] = k
                                dic["row"] = d1["row"]
                                dic["xm"] = d1["xm"]
                                dic["y0"] = d1["y0"]
                                dic["y1"] = d1["y1"]
                                dic["x0"] = d1["x0"]
                                dic["x1"] = d1["x1"]
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
                                dic["y1"] = d1["y1"]
                                dic["x0"] = d1["x0"]
                                dic["x1"] = d1["x1"]
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
                                        
                    #end if :(if len(getattr(self, Item)) > 0:)
                    
                #next :(for Item in ItemName:)
                                            
                
                                
                if len(self.階)>0:
                    ItemName2 = ["階"]
                    
                    for j in range(len(Section[i])):
                        row1 = Section[i][j]["row"]
                        rmax = Section[i][j]["rmax"]
                        xm1 = Section[i][0]["xm"]
                        for Item in ItemName2:
                            # data = []
                            dic2 = []
                            for k, d1 in enumerate(getattr(self, Item)):   # ローカル変数を名前で指定する関数
                                xm = d1["xm"]
                                row = d1["row"]
                                # if row >= row1 and row <= rmax and xm < xm1 and abs(xm1-xm)<self.ColumnPitch*3.0:
                                if row >= row1 and row <= rmax and xm < xm1 :
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
                                    dic["y1"] = d1["y1"]
                                    dic["x0"] = d1["x0"]
                                    dic["x1"] = d1["x1"]
                                    dic["item"] = d1["item"]

                                    dic2.append(dic)
                                    if Item == "階":
                                        if abs(dic["xm"] - xm1) < self.ColumnPitch * 9:
                                            Section2[i][j].append(dic)
                                        #end if
                                    else:
                                        Section2[i][j].append(dic)
                                    #end if
                                #end if
                            #next
                                    
                            # # 階データが複数ある場合は最も近いものを選択する。
                            # if len(dic2)>1 :
                            #     xL0 = abs(dic2[0]["xm"] - xm1)
                            #     xn = 0
                            #     for k in range(1,len(dic2)):
                            #         xL1 = abs(dic2[k]["xm"] - xm1)
                            #         if xL1 < xL0:
                            #             xn = k
                            #         #end if
                            #     #next
                            #     Section2[i][j].append(dic2[xn])
                            # else:
                            #     Section2[i][j].append(dic2[0])
                            # #end if
                            
                            
                            
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
            

            #==========================================================
            # 表に空欄がある場合にそこに「no data」を追加する処理（柱のみの処理）
            #==========================================================

            # 表が縦に複数ある場合は分ける。
            Section3 = []
            Section22 = []
            row0 = Section2[0][0][0]["row"]
            for j, Sec in enumerate(Section2):
                row1 = Sec[0][0]["row"]
                if row0 == row1 :
                    Section22.append(Sec)
                else:
                    Section3.append(Section22)
                    Section22 = []
                    Section22.append(Sec)
                    row0 = Sec[0][0]["row"]
                #end if
            #next
            Section3.append(Section22)


            # 表が横または縦に複数ある場合は分ける。
            Section3 = []
            Section22 = []
            row0 = Section2[0][0][0]["row"]
            xm0 = Section2[0][0][0]["xm"]
            x00 = Section2[0][0][0]["x0"]
            x01 = Section2[0][0][0]["x1"]
            for j, Sec in enumerate(Section2):
                row1 = Sec[0][0]["row"]
                xm1 = Sec[0][0]["xm"]
                if row0 == row1 and abs(xm1 - xm0) < self.ColumnPitch * 1.5:
                    Section22.append(Sec)
                else:
                    Section3.append(Section22)
                    Section22 = []
                    Section22.append(Sec)
                    xm0 = Sec[0][0]["xm"]
                    row0 = Sec[0][0]["row"]
                    x00 = Sec[0][0]["x0"]
                    x01 = Sec[0][0]["x1"]
                #end if
                a=0
                # Section3.append(Section22)
            #next
            Section3.append(Section22)


            # 表毎に空欄がある場合はno dataを追加する        
            Section33 = []
            for Section2 in Section3:
                SecKeys = []
                KeyN = []
                KeyNmax = 0
                KeyPos = -1
                for i, Sec in enumerate(Section2):
                    SecKey = []
                    for D in Sec[0]:
                        SecKey.append(D["kind"])
                    #next
                    SecKeys.append(SecKey)
                    n = len(SecKey)
                    KeyN.append(len(SecKey))
                    if n > KeyNmax:
                        KeyNmax = n
                        KeyPos = i
                    #end if
                #next
                StandardKeys = SecKeys[KeyPos]
                StandardData = Section2[KeyPos][0]
                Section22 = []
                for i, Sec in enumerate(Section2):
                    Sec2 = []
                    Sn = len(Sec)
                    for j in range(Sn):
                        k = 0
                        data = []
                        for m, key0 in enumerate(StandardKeys):
                            key1 = Sec[j][k]["kind"]
                            xm = Sec[j][k]["xm"]
                            if key0 == key1 :
                                data.append(Sec[j][k])
                                k += 1
                            else:
                                D = StandardData[m]
                                D["xm"] = xm
                                D["text"] = "no data"
                                data.append(D)
                            #end if
                        #next
                        Sec2.append(data) 
                    #next
                    Section22.append(Sec2)
                #next
                Section33 += Section22
            #next
            Section2 = Section33

            # 部材表は複数の部材が縦に並んでいるので部材毎に分割する処理
            for Sec in Section2:
                for bdata in Sec:
                    dflag = False
                    for bd in bdata:
                        if bd["kind"] == "同上":
                            dflag = True
                            break
                        #end if
                    #next
                        
                    if dflag :
                        bdata2 = []
                        bdata2.append(bdata[0].copy())
                        DDD = []
                        flag1 = True
                        flag2 = False
                        flag3 = True
                        bi = 1
                        while flag1:
                            if bdata[bi]["kind"] == "階":
                                bdata2.append(bdata[bi].copy())
                                row0 = bdata[bi]["row"]
                                # if flag3 == False:
                                #     flag3 = True
                                #end if
                            elif bdata[bi]["kind"] != "同上":
                                bdata2.append(bdata[bi].copy())
                                row0 = bdata[bi]["row"]
                                if flag3:
                                    DDD = []
                                    flag3 = False
                                #end if
                                DDD.append(bdata[bi].copy())
                                
                            elif bdata[bi]["kind"] == "同上":
                                row0 = bdata[bi]["row"]
                                y0 = bdata[bi]["y0"]
                                y1 = bdata[bi]["y1"]
                                for II, DD in enumerate(DDD):
                                    DD["row"] = row0 + II + 1
                                    DD["y0"] = y0 + (II + 1)*self.ypitch + self.ypitch*3
                                    DD["y1"] = y1 + (II + 1)*self.ypitch + self.ypitch*3
                                    DD["text"] = "同上"
                                    bdata2.append(DD.copy())
                                #next
                                flag3 = True
                            #end if
                            bi += 1
                            if bi >= len(bdata):
                                flag1= False
                            #end if
                        #end while
                        bdata = bdata2
                    #end if
                    

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
                                kindSameN[kind1].append([j,bd["y0"],bd["xm"]])
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
                            xm0 = ln[0][2]
                            ln2.append(n0)
                            for k in range(1,len(ln)):
                                n1 = ln[k][0]
                                y1 = ln[k][1]
                                xm1 = ln[k][2]
                                if abs(y0-y1) < self.ypitch * 1.5 and abs(xm0 - xm1)<self.ColumnPitch/4 :
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
                    

                    # キーの順番が乱れているので再度行の順番に並び替える。
                    keys = list(kindSameN2.keys())
                    L2 = []
                    for key in keys:
                        L2.append(kindSameN2[key][0][0])
                    #next
                    VArray = np.array(L2) 
                    index1 = np.argsort(VArray)
                    keys1 = []
                    for j in range(len(index1)):
                        keys1.append(keys[index1[j]])
                    #next
                    keys = keys1
                    
                    # 同じ柱のデータを柱符号の順番でひとつにまとめる。
                    beam2 = []            
                    # for bdata in Sec:
                    beam = []
                    # n0 = 0
                    for Beami in range(kindSameNMax):
                        dataDic1 = []
                        n0 = kindSameN2[keys[1]][Beami][0]
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
                                    if key == "柱符号":
                                        dataDic1.append([key2,data["text"]])
                                    else:
                                        if abs(n - n0) < 4:
                                            dataDic1.append([key2,data["text"]])
                                            n0 = n
                                        #end if
                                    #end if
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
                                    if key == "柱符号":
                                        dataDic1.append([key2,data["text"]])
                                    else:
                                        if abs(n - n0) < 4:
                                            dataDic1.append([key2,data["text"]])
                                            n0 = n
                                        #end if
                                    #end if
                                    # if abs(n - n0) < 4:
                                    #     dataDic1.append([key2,data["text"]])
                                    #     n0 = n
                                    # #end if
                                    # # dataDic1.append([key2,data["text"]])
                                #next
                            #next
                            #end if
                        next
                    
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
                
                n = len(beam2[0])
                m = len(beam2)
                for i in range(n):
                    beam3= []
                    for j in range(m):
                        beam3.append(beam2[j][i])
                    #next
                    ColumnData.append(beam3)
                #next
            # #next for Sec in Section2:
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
        
        return ColumnData
    
    #end def

    #============================================================================
    #　PDFのページから抽出された単語データから梁データまたは柱データを抽出する関数
    #============================================================================
    def ElementFinder(self,page):
        """
        
        """
        PageWordData = self.Read_Word_From_Page(page)

        BeamData = []
        ColumnData = []

        if self.FindMember(PageWordData):
            BeamData= self.MakeBeamData()
            ColumnData = self.MakeColumnData()
        #end if
        # print(len(BeamData),len(ColumnData))
        return BeamData , ColumnData
    
    #end def

    #============================================================================
    #　梁データまたは柱データをCSVファイルに書き出す関数
    #============================================================================
    def Save_MemberData_Csv(self, filename, BeamData, ColumnData):

        ja_cvu_normalizer = JaCvuNormalizer()
    
        if len(BeamData)>0 or len(ColumnData)>0 and filename != "":

            # filename = os.path.splitext(pdfname)[0] + "_部材リスト" + ".csv"

            # 異字体の修正
            # filename = ja_cvu_normalizer.normalize(filename) utf-8

            with open(filename, 'w', encoding='shift_jis') as f:
            # with open(filename, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                # title = "[ " + filename + " ]"
                # # title = ja_cvu_normalizer.normalize(title) 
                # writer.writerow([title])
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

    #============================================================================
    #　梁データまたは柱データをpickleファイルに書き出す関数
    #============================================================================
    def Save_MemberData_Picle(self, filename, BeamData, ColumnData):
        if (len(BeamData) >0 or len(ColumnData)>0) and filename != "":
            dlist = [BeamData,ColumnData]
            
            with open(filename, mode="wb") as f:
                pickle.dump(dlist, f)
            #end with
        #end if
    #end if
    
    #============================================================================
    #　梁データまたは柱データをpickleファイルから呼び込む関数
    #============================================================================
    def Load_MemberData_Picle(self, filename):
        BeamData = []
        ColumnData = []
        if filename != "":
            dlist = []
            
            with open(filename, mode="rb") as f:
                dlist = pickle.load(f)
            #end with
            BeamData = dlist[0]
            ColumnData = dlist[1]
        #end if
        return BeamData,ColumnData
    #end if

    #============================================================================
    # 複数のpickleファイルから梁データおよび柱データを呼び込みそれらを比較する関数
    #============================================================================
    def Compare_Data(self, picklefilenames):

        fn = len(picklefilenames)
        if fn >= 2 : # ファイルが2つ以上ある場合のみ処理を行う。
            BeamFoors = []
            BeamDics = []
            ColumnFoors = []
            ColumnDics = []
            for fi, filename in enumerate(picklefilenames):
                BeamData, ColumnData = self.Load_MemberData_Picle(filename)
                Bfoor, Bdic = self.Classify_Data(BeamData)
                BeamFoors.append(Bfoor)
                BeamDics.append(Bdic)

                Cfoor, Cdic = self.Classify_Data(ColumnData)
                ColumnFoors.append(Cfoor)
                ColumnDics.append(Cdic)
            #next



    #============================================================================
    # 梁データまたは柱データからデータの辞書を作成する関数
    #============================================================================
    def Classify_Data(self, Data):
        #=================================================================================
        # 入力： BeamData または ColumnData
        #
        # 出力： FloorNames  :データに含まれる階のリスト [ "R","10","9"・・・・]
        #       FloorDic    :階がキーの辞書（符号リストと符号リストがキーのデータの辞書を含む）
        #           MemberNames :符号リスト ["G1","G2"・・・・]
        #           MemberDic   :符号リストがキーのデータの辞書
        #
        #                       (データの例)
        #                       '階':'R'
        #                       '梁符号':'G1'
        #                       '梁断面位置':'1通端'
        #                       '断面寸法':'450x800'
        #                       '上端筋:主筋':'5-D25'
        #                       '下端筋:主筋':'4-D25'
        #                       'あばら筋:フープ筋':'-D13@200'
        #                       '腹筋':'2-D10'
        #
        #==================================================================================
        
        FloorDic = {}
        FloorNames = []
        if len(Data)>0:

            Data1 = Data.copy()
            # dic0 = Data1[0][0]
            # keys = list(dic0.keys())
            # MemberKey = keys[1]         # "梁符号" or "柱符号" 自動判別

            # 複数の階が記載されている場合の処理
            # [3,4]の場合はデータを1個追加する。[3,5]の場合はデータを2個追加する
            Data2 = []
            for i, D in enumerate(Data1):
                D1 = D.copy()
                floor = D[0]["階"]
                if "," in floor:
                    D2 = D1.copy()
                    f0 = floor.split(",")
                    
                    f0.sort()
                    f1 = []
                    for ff in f0:
                        f1.append(int(ff))
                    #next
                    f2 = f1[0]
                    f3 = f1[1]
                    for j in range(f2,f3+1):
                        D3 = D2.copy()
                        for D4 in D3:
                            D4["階"] = str(j)
                        #next
                        Data2.append(copy.deepcopy(D3))
                    #next
                else:
                    Data2.append(copy.deepcopy(D1))
                #end if
            #next
            Data1 = copy.deepcopy(Data2)

            # 階が修正されたデータで分類を行う。
            dic0 = Data1[0][0]
            keys = list(dic0.keys())
            MemberKey = keys[1]         # "梁符号" or "柱符号" 自動判別

            # Data中の階データの種類のリストを取得
            # FloorNames = []
            for D in Data1:
                if not(D[0]["階"] in FloorNames):
                    FloorNames.append(D[0]["階"])
                #end if
            #next
            
            L2 = []
            for d in FloorNames:
                if "R" in d:
                    L2.append(1000)
                else:
                    L2.append(int(d))
                #end if
            #next
            VArray = np.array(L2)
            index1 = np.argsort(-VArray)    # 降順にソートするインデックスを取得
            FloorNames2 = []
            for i in range(len(index1)):
                FloorNames2.append(FloorNames[index1[i]])
            #next
            FloorNames = FloorNames2
            # FloorNames.sort(reverse=True)   # リストを降順で並び替え

            # 同じ階のデータを抽出する。
            # FloorDic = {}
            for FloorName in FloorNames:
                FloorDatas = []
                for D in Data1:
                    if D[0]["階"] == FloorName :
                        FloorDatas.append(D)
                    #end if
                #next
                
                # 抽出したデータの符号名のリストを取得
                MemberNames = []
                for D in FloorDatas:
                    if not(D[0][MemberKey] in MemberNames):
                        MemberNames.append(D[0][MemberKey])
                    #end if
                #next
                        
                # MemberNames.sort(reverse=False)   # リストを昇順で並び替え
                
                # 同じ符号名のデータを抽出する。同じ階に同じ符号はないことが前提条件
                MemberDic = {}
                for MemberName in MemberNames:
                    MemberDatas = []
                    for D in FloorDatas:
                        if D[0][MemberKey] == MemberName :
                            MemberDatas.append(D)
                        #end if
                    #next
                    # 符号名による辞書を作成
                    MemberDic[MemberName] = MemberDatas
                #next
                FloorDic[FloorName] = [MemberNames, MemberDic]
            #next
        #end if
        
        return FloorNames,FloorDic
    
    #end def
                


    #============================================================================
    #  表紙以外のページのチェック（外部から読み出す関数名）
    #============================================================================

    def PageCheck(self,filename, outdir, psn, PageNumber,ProcessN):
        global flag1, fname, dir1, dir2, dir3, dir4, dir5, folderName, paraFileName
        global ErrorFlag, ErrorMessage
        
        if filename =="" :
            return False
        #end if
        print(filename)
        pdf_file = filename

        # PyPDF2のツールを使用してPDFのページ情報を読み取る。
        # PDFのページ数と各ページの用紙サイズを取得
        PaperSize = []
        self.PaperRotate = []                
        try:
            with open(pdf_file, "rb") as input:
                reader = PR2(input)
                PageMax = len(reader.pages)     # PDFのページ数
                # PaperSize = []
                # PaperRotate = []
                for page in reader.pages:       # 各ページの用紙サイズの読取り
                    p_size = page.mediabox
                    rotate = page.get('/Rotate', 0)
                    self.PaperRotate.append(rotate)
                    page_xmin = float(page.mediabox.lower_left[0])
                    page_ymin = float(page.mediabox.lower_left[1])
                    page_xmax = float(page.mediabox.upper_right[0])
                    page_ymax = float(page.mediabox.upper_right[1])
                    PaperSize.append([page_xmax - page_xmin , page_ymax - page_ymin])
            #end with
        except OSError as e:
            print(e)
            logging.exception(sys.exc_info())#エラーをlog.txtに書き込む
            return False
        except:
            logging.exception(sys.exc_info())#エラーをlog.txtに書き込む
            return False
        #end try
        
        #=============================================================
        # startpage = 1
        # endpage = PageMax
        
        # # PDFMinerのツールの準備
        # resourceManager = PDFResourceManager()
        # # PDFから単語を取得するためのデバイス
        # device = PDFPageAggregator(resourceManager, laparams=LAParams())
        # # PDFから１文字ずつを取得するためのデバイス
        # device2 = PDFPageAggregator(resourceManager)

        pageResultData = []
        pageNo = []
        BeamData = []
        ColumnData = []
        try:
            
            with pdfplumber.open(pdf_file) as pdf:
                # interpreter = PDFPageInterpreter(resourceManager, device)
                # interpreter2 = PDFPageInterpreter(resourceManager, device2)

                PageData = []
                for page in pdf.pages:
                # for page in PDFPage.get_pages(PDF):
                    PageData.append(page)
                #next
                pageI = 0
                # pageI2 = 0
                # PageN2 = len(PageNumber)
                flagPage = True

                while flagPage:
                    for i,p in enumerate(PageNumber):
                        flagPage = False
                        if p > 0:
                            pageI = i + 1
                            PageNumber[i] = 0
                            flagPage = True
                            page = PageData[i]
                            ProcessN[psn] += 1
                            break
                        #end if
                    #next
                    if flagPage == False:
                        break
                    #end if

                    # outfile = outdir + "/" + "outfile{:0=4}.pdf".format(pageI)
                    ResultData = []
                    print("ps={}:page={}:".format(psn,pageI), end="")

                    BeamData1, ColumnData1 = self.ElementFinder(page)

                    # print(len(BeamData1),len(ColumnData1))

                    if len(BeamData1) > 0:
                            BeamData += BeamData1
                    #end if
                    if len(ColumnData1) > 0:
                        ColumnData += ColumnData1
                    #end if

                #next

                # fp.close()
                folderName = ""
                # os.remove("./kind.txt")
            # end with
            
            if len(BeamData)>0 or len(ColumnData)>0:
                filename2 = os.path.splitext(pdf_file)[0] + ".pickle"
                filename2 = filename2.replace("/in/","/out/")
                self.Save_MemberData_Picle(filename2 ,BeamData ,ColumnData)
            #end if

        except OSError as e:
            print(e)
            logging.exception(sys.exc_info())#エラーをlog.txtに書き込む
            # print("******1")
            return False
        except:
            logging.exception(sys.exc_info())#エラーをlog.txtに書き込む
            # print("***********2")
            return False
        # end try

        # すべての処理がエラーなく終了したのでTrueを返す。
        return True

    # #end def   
    
    #*********************************************************************************


#end class
    
#======================================================================================


#======================================================================================
#
#   メインルーチン
#
#======================================================================================

if __name__ == '__main__':

    time_sta = time.time()  # 開始時刻の記録(\\s*G\\d{1,2}\\D*\\s*)|\\s*G\\d{1,2}\\D*\\s*\\,\\s*G\\d{1,2}\\D*\\s*

    CR = ChartReader()

    flag = 2

    if flag == 1:
        
        pdffname2 =[]
        # pdffname2.append("PICKLE/01(2)Ⅲ構造計算書(2)一貫計算編電算出力（抜粋）_部材リスト.pickle")
        # pdffname2.append("PICKLE/01(仮称)阿倍野区三明町2丁目マンション新築工事_構造図（抜粋）_部材リスト.pickle")

        pdffname2.append("PICKLE/02一貫計算書（一部）（抜粋）_部材リスト.pickle")
        pdffname2.append("PICKLE/02構造図（抜粋）_部材リスト.pickle")
        
        CR.Compare_Data(pdffname2)

    elif flag == 2:

        pdffname =[]

        # pdffname.append("ミックスデータ.pdf")
        # pdffname.append("構造図テストデータ2.pdf")
        
        # pdffname.append("構造図テストデータ.pdf")
        # pdffname.append("構造計算書テストデータ.pdf")

        # pdffname.append("01(仮称)阿倍野区三明町2丁目マンション新築工事_構造図（抜粋）.pdf")
        # pdffname.append("01(2)Ⅲ構造計算書(2)一貫計算編電算出力（抜粋）.pdf")
        
        pdffname.append("02構造図（抜粋）.pdf")
        pdffname.append("02一貫計算書（一部）（抜粋）.pdf")

        # pdffname.append("03sawarabi 京都六角 計算書 (事前用)（抜粋）.pdf")
        # pdffname.append("03sawarabi 京都六角 構造図(事前用)（抜粋）.pdf")

        # pdffname.append("01(仮称)阿倍野区三明町2丁目マンション新築工事_構造図.pdf")
        # pdffname.append("01(2)Ⅲ構造計算書(2)一貫計算編電算出力.pdf")
        
        # pdffname.append("02構造図.pdf")
        # pdffname.append("02一貫計算書（一部）.pdf")

        # pdffname.append("03sawarabi 京都六角 計算書 (事前用).pdf")
        # pdffname.append("03sawarabi 京都六角 構造図(事前用).pdf")


        Folder1 = "PDF"
        Folder2 = "CSV"
        Folder3 = "PICKLE"
        for pdf in pdffname:
            print("ファイ名={}".format(pdf))
            BeamData , ColumnData = CR.Read_Members_from_pdf(Folder1 + "/"+ pdf)
            
            if len(BeamData) > 0 or len(ColumnData) > 0:

                # FloorNames1,FloorDic1 = CR.Classify_Data(BeamData)
                # FloorNames2,FloorDic2 = CR.Classify_Data(ColumnData)


                filename2 = os.path.splitext(pdf)[0] + "_部材リスト" + ".pickle"
                filename2 = Folder3 + "/"+ filename2
                CR.Save_MemberData_Picle(filename2,BeamData,ColumnData)

                filename = os.path.splitext(pdf)[0] + "_部材リスト" + ".csv"
                filename = Folder2 + "/"+ filename

                CR.Save_MemberData_Csv(filename, BeamData , ColumnData )



    #     # filename = Folder1 + "/"+ pdf

    #     # filename2 = os.path.splitext(pdf)[0] + "_部材リスト" + ".picle"
    #     # filename2 = Folder3 + "/"+ filename2

    #     # CR.Read_and_Save_Members_To_Pickle(filename,filename2)

    # #next
    
    time_end = time.time()  # 終了時刻の記録
    print("処理時間 = {} sec".format(time_end - time_sta))



    

#end if
    
