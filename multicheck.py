

#==========================================================================================
#   構造計算書の数値検査プログラムのサブルーチン（ver.2.00）
#
#           一般財団法人日本建築総合試験所
#
#               coded by T.Kanyama  2023/05
#
#==========================================================================================
"""
このプログラムは、構造判定センターに提出される構造計算書（PDF）の検定比（許容応力度に対する部材応力度の比）を精査し、
設定した閾値（デフォルトは0.95）を超える部材を検出するプログラムのツールである。

"""
#
from pypdf import PdfReader as PR2 # 名前が上とかぶるので別名を使用
import pypdf

# その他のimport
import os,time
import sys
import logging
import glob
from multiprocessing import Process,Array
import shutil
from ChartReader import ChartReader

kind = ""
version = ""

#============================================================================
#  並列処理による数値チェックのクラス
#============================================================================

class multicheck:

    #============================================================================
    #  クラスの初期化関数
    #       fiename     : 計算書のファウル名
    #       limit       : 閾値
    #       stpage      : 処理開始ページ
    #       edpage      : 処理終了ページ
    #       bunkatu     : 並列処理の分割数
    #============================================================================
    def __init__(self,filename1, inputfolder1="PDF", outputfolder1="CSV", stpage=0, edpage=0, bunkatu=4):
        self.filename = filename1
        self.inputfolder = inputfolder1
        self.outputfolder = outputfolder1
        self.bunkatu = bunkatu
        self.kinf =""
        self.version = ""
        self.rotate = []

        # 検出結果のファイル名
        # self.pdf_out_file = os.path.splitext(self.filename)[0] + '[検出結果(閾値={:.2f}'.format(limit)+')].pdf'

        # PyPDF2のツールを使用してPDFのページ情報を読み取る。
        # PDFのページ数と各ページの用紙サイズを取得
        try:
            with open(self.inputfolder + "/"+ self.filename, "rb") as input:
                reader = PR2(input)
                self.PageMax = len(reader.pages)     # PDFのページ数
            
            #end with
        except OSError as e:
            print(e)
            logging.exception(sys.exc_info())#エラーをlog.txtに書き込む
            self.flag = False
        except:
            logging.exception(sys.exc_info())#エラーをlog.txtに書き込む
            self.flag = False
        #end try
        
        #=============================================================
        if stpage <= 1 :      # 検索を開始する最初のページ
            self.startpage = 1
        elif stpage > self.PageMax:
            self.startpage = self.PageMax-1
        else:
            self.startpage = stpage
        #end if

        if edpage <= 0 :  # 検索を終了する最後のページ
            self.endpage = self.PageMax 
        elif edpage > self.PageMax:
            self.endpage = self.PageMax
        else:
            self.endpage = edpage
        #end if
        self.flag = True
    #end def

    #============================================================================
    #  計算書ファイルを分割する関数
    #============================================================================
    def makepdf(self):

        # プログラムのあるディレクトリー
        fld = os.getcwd()

        # 分割ファイルを一時保存するディレクトリー（無ければ作成）
        self.dir1 = fld + "/in"
        if not os.path.isdir(self.dir1):
            os.mkdir(self.dir1)
        #end if

        # pdfフォルダー内にあるPDFファイルをすべて削除
        files = glob.glob(os.path.join(self.dir1, "*.pdf"))
        if len(files)>0:
            for file in files:
                os.remove(file)
            #next
        #end if

        # 結果ファイルを一時保存するディレクトリー（無ければ作成）
        self.dir2 = fld + "/out"
        if not os.path.isdir(self.dir2):
            os.mkdir(self.dir2)
        #end if

        p_file = fld + "/in/inputfile.pdf"
        # PDFファイルを回転して保存
        # def pdf_roll(p_file, p_angle):
        file = pypdf.PdfReader(open(self.inputfolder + "/" + self.filename , 'rb'))
        file_output = pypdf.PdfWriter()
        for page in file.pages: 

        # # for page_num in range(file.numPages):
        #     # page = file.getPage(page_num)
        #     rotate = page.get('/Rotate', 0)
        #     self.rotate.append(rotate)
        #     if rotate != 0:
        #         page.rotate(-rotate)
            
            file_output.add_page(page)
        with open(p_file, 'wb') as f:
            file_output.write(f)

        pagen = self.endpage - self.startpage + 1

        self.fnames = []
        rg = "0:1"
        fname = self.dir1 + "/" + "file{:0=2}.pdf".format(0)
        self.fnames.append(fname)
        merger = pypdf.PdfMerger()
        # merger.append(self.filename, pages=pypdf.PageRange(rg))
        merger.append(p_file, pages=pypdf.PageRange(rg))
        merger.write(fname)
        merger.close()

        for i in range(self.bunkatu):  
            fname = self.dir1 + "/" + "file{:0=2}.pdf".format(i+1)
            self.fnames.append(fname)
            # shutil.copyfile(self.filename, fname)
            shutil.copyfile(p_file, fname)
        #next
        os.remove(p_file)
    #end def

    
    #============================================================================
    #  表紙から計算プログラムの種類を検出する関数
    #============================================================================
    # def TopPageCheck(self):
    #     global kind, version
    #     CT = CheckTool()
    #     self.kind, self.verison = CT.TopPageCheckTool(self.fnames[0],self.dir2,self.limit)
    #     kind = self.kind
    #     version = self.version
    
    #============================================================================
    #  複製された計算書から数値検出する関数
    #============================================================================

    def PageCheck(self,fname,outdir,psn,PageNumber,ProcessN):
        CT = ChartReader()
        # CT.Read_and_Save_Members_To_Pickle(fname,outdir)
        CT.PageCheck(fname,outdir,psn,PageNumber,ProcessN)



    #============================================================================
    #  処理のメインルーチン関数
    #       計算書の分割
    #       表示の読取り
    #       分割された計算書の並列処理
    #============================================================================
    def doCheck(self):
        global kind, version

        
#       計算書の分割        
        self.makepdf()

# #       表示の読取り
#         self.TopPageCheck()

#       分割された計算書の並列処理
        n = len(self.fnames)    
        # 並列処理（マルチプロセスのオブジェクトを作成）    
        Plist = list()

        # if 並列化:
        ProcessN = Array('i', range(self.bunkatu))
        for i in range(self.bunkatu):
            ProcessN[i] = 0
        #next
        PageNumber = Array('i', range(self.PageMax))
        for i in range(self.PageMax):
            PageNumber[i] += 1
        #next
        
        for i, p in enumerate(PageNumber):
            if p < self.startpage or p > self.endpage:
                PageNumber[i] = 0
            #end if
        #next

        # for i, p in enumerate(PageNumber):
        #     print(i,p)
        # #next

        for i in range(n-1):
            fname = self.fnames[i+1]
            P = Process(target=self.PageCheck, args=([fname, self.dir2 , i, PageNumber, ProcessN]))
            Plist.append(P)
        #next

        # 各オブジェクトをスタート
        for P in Plist:
            P.start()
        #next

        # 各オブジェクトをジョイン（同期）
        for P in Plist:
            P.join()
        #next
        
        # else:
        #     for i in range(n-1):
        #         fname = self.fnames[i+1]
        #         self.PageCheck(fname, self.dir2 , i, self.bunkatu)
        #     #next
        # #end if

        for i,p in enumerate(ProcessN):
            print("Process No={} : N={}".format(i,ProcessN[i]))
        #next

        CR = ChartReader()

        # 結果フォルダーにあるファイル名の読取り
        files = glob.glob(os.path.join(self.dir2, "*.pickle"))
        # ファイルのソート
        files.sort()

        # 結果ファイルを順番に結合し、１つの結果ファイルを保存
        BeamData = []
        ColumnData = []
        for file in files:
            BeamData1, ColumnData1 = CR.Load_MemberData_Picle(file)
            if len(BeamData1) > 0:
                    BeamData += BeamData1
            #end if
            if len(ColumnData1) > 0:
                ColumnData += ColumnData1
            #end if
        #next
                
        BeamData = CR.Sort_Element(BeamData, ItemName="梁符号", sc=-1)    # sc=-1:降順,sc=1:昇順

        ColumnData = CR.Sort_Element(ColumnData, ItemName="柱符号",sc=-1)  # sc=-1:降順,sc=1:昇順

        filename2 = os.path.splitext(self.filename)[0] + "_部材リスト" + ".csv"
        # filename2 = filename2.replace("PDF/" , "CSV/")
        CR.Save_MemberData_Csv(self.outputfolder + "/" + filename2, BeamData,ColumnData)

        # 結果ファイルを消去
        for file in files:
            os.remove(file)

        # 分割したPDFファイルを消去
        for file in self.fnames:
            os.remove(file)

        # if os.path.exists(file1):
        #     os.remove(file1)

        return True

    #end def


#==================================================================================
#   このクラスを単独でテストする場合のメインルーチン（マルチプロセス）
#==================================================================================

if __name__ == '__main__':

    time_sta = time.time()  # 開始時刻の記録

    CR = ChartReader()

    Folder1 = "PDF"

    pdffname =[]

    # pdffname.append("ミックスデータ.pdf")
    
    pdffname.append("構造図テストデータ.pdf")
    pdffname.append("構造計算書テストデータ.pdf")

    # pdffname.append("(仮称)阿倍野区三明町2丁目マンション新築工事_構造図.pdf")
    # pdffname.append("(2)Ⅲ構造計算書(2)一貫計算編電算出力.pdf")
    
    # pdffname.append("02構造図.pdf")
    # pdffname.append("02一貫計算書（一部）.pdf")


    Folder1 = "PDF"
    Folder2 = "CSV2"
    Folder3 = "PICKLE"
    for pdf in pdffname:
        
        MCT = multicheck(pdf,inputfolder1=Folder1,outputfolder1=Folder2,stpage=1,edpage=100,bunkatu=4)
        MCT.doCheck()


    #next
    
    time_end = time.time()  # 終了時刻の記録
    print("処理時間 = {} sec".format(time_end - time_sta))
    
    

#*********************************************************************************
