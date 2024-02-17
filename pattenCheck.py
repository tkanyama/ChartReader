#********************************************************************
#
#   記号のパターンから部材の種類を決定するクラス
#
#   pm1 = PatternCheck()
#   print(d,"=",pm1.checkPattern("SD345"))
#   print(d,"=",pm1.checkPattern("2/4-D25"))
#
#   print結果       
#       SD345 = 材料
#       2/4-D25 = 主筋
#********************************************************************

import re


class PatternCheck:

    def __init__(self):

        # 記号パターン辞書の作成
        self.makePattern() 

    #end def
    
    #======================================
    #   記号パターン辞書を作成する関数
    #======================================"(\s*\S+\s*(×|x|ｘ)\s*)"
    def makePattern(self):
        self.patternDic = {}
        
        # self.patternDic["断面寸法2"]=[[
        #                             '(\s*\d{1,2}-D\d{2}\s*\+\s*)'
        #                         ], 25]
        # self.patternDic["断面寸法3"]=[[
        #                             '(\s*\w+\s*)'
        #                         ], 25]
        # self.patternDic["断面寸法4"]=[[
        #                             '(\s*\d+\s*(×|x|ｘ)\s*)|(\s*\d+,\d+\s*(×|x|ｘ)\s*)'
        #                         ], 25]
        self.patternDic["梁符号1"]=[[
                                    '(\s*G\d{1,2}\D*\s*)'   # G1 G20 G1A G20A
                                # '|'+'(\s*FG\d{1,2}\D*\s*)'          # FG1 FG10 FG1A FG10A
                                # '|'+'(\s*FCG\d{1,2}\D*\s*)'          # FCG1 FCG10 FCG1A FCG10A
                                ] , 8 ] # 文字数制限
        self.patternDic["小梁符号"]=[[
                                    '(\s*B\d{1,2}\D*\s*)' +         # B1 B20 B1A B20A
                                '|'+'(\s*(C|F)B\d{1,2}\D*\s*)'        # CB1 CB10 CB1A CB10A FB1 FB10 FB1A FB10A
                                        # CB1 CB10 CB1A CB10A FB1 FB10 FB1A FB10A
                                ] , 8 ] # 文字数制限
        self.patternDic["梁符号2"]=[[
                                    '(\s*\d{1,2}G\d{1,2}\D*\s*)'+   # 9G1 12G12 9G1A 12G12A
                                '|'+'(\s*RG\d{1,2}\D*\s*)' +       # RG1 RG10 RG1A RG10A
                                '|'+'(\s*FG\d{1,2}\D*\s*)' +        # FG1 FG10 FG1A FG10A
                                # '|'+'(\s*FCG\d{1,2}\D*\s*)' +        # FCG1 FCG10 FCG1A FCG10A
                                '|'+'(\s*\d{1,2}G\d{1,2}\D*\s*),(\s*\d{1,2}G\d{1,2}\D*\s*)' +
                                '|'+'(\s*\d{1,2}G\d{1,2}\D*\s*,\s*\d{1,2}G\d{1,2}\D*\s*,\s*\d{1,2}G\d{1,2}\D*\s*)'
                                ], 10]
        self.patternDic["片持梁符号"]=[[
                                    '(\s*CG\d{1,2}\D*\s*)' +         # CG1 CG20 CG1A CG20A
                                '|'+'(\s*FCG\d{1,2}\D*\s*)' +       # FCG1 FCG10 FCG1A 
                                '|'+'(\s*FCG\d{1,2}\D*\s*-\d*\s*)' +        # FCG-1
                                '|'+'(\s*CG\d{1,2}\D*\s*-\d*\s*)'         # CG1-1
                                ] , 8 ] # 文字数制限
        self.patternDic["壁"]=[[
                                    '(\s*W\d{1,2}\D*\s*)' +         # W15,W15a
                                '|'+'(\s*EW\d{1,3}\D*\s*)'         # EW165,EW18A
                                ] , 8 ] # 文字数制限
        self.patternDic["梁断面位置"]=[[
                                    '\s*全断\S{1}\s*|\s*端部\s*|\s*両端\s*|\s*中央\s*|\s*左端\s*|\s*右端\s*'+
                                    '|s*元端\s*|s*先端\s*'+
                                    '|\s*\d{1}通端\s*'+
                                    '|'+'\s*\d{1}通\s*,\s*\d{1}通端\s*' +
                                    '|'+'\s*\d{1}通\s*(・)\s*\d{1}通端\s*' +
                                    '|\s*\w+\d+\s*端\s*|\s*全断\s*'
                                ], 12]
        self.patternDic["項目名1"]=[[
                                    '符号名'+
                                    '|'+'コンクリート'+
                                    '|'+'\s*主\s*筋\s*'
                                    '|'+'かぶり'+
                                    '|'+'かぶり・あき'+
                                    '|'+'\s*上\s*端\s*筋\s*'+
                                    '|'+'あばら筋'+'|'+
                                    '|'+'\s*帯\s*筋\s*'+'|'+
                                    '|'+'\s*下\s*端\s*筋\s*'+
                                    '|'+'仕口部帯筋'+
                                    '|'+'フープ'+
                                    # '|'+'スターラップ'+
                                    '|'+'\s*腹\s*筋\s*'+
                                    '|'+'芯鉄筋'
                                ], 10]
        # self.patternDic["主筋項目名"]=[[スターラップ
        #                             '\s*上\s*端\s*筋\s*'+
        #                             '|'+'\s*下\s*端\s*筋\s*'+
        #                             '|'+'仕口部帯筋'+'|'+'\s*腹\s*筋\s*'+
        #                             '|'+'芯鉄筋'
        #                         ], 10]
        # self.patternDic["材料項目名"]=[[
        #                             '|'+'\s*主\s*筋\s*'  #+'|'+'主 筋'+
        #                             '|'+'あばら筋'+'|'+
        #                             '|'+'\s*帯\s*筋\s*'+
        #                             '|'+'芯鉄筋'
        #                         ], 10]
        self.patternDic["構造計算書"]=[[
                                    '構造計算書'
                                ], 10]
        self.patternDic["同上"]=[[
                                    '\s*同\s*上\s*'
                                ], 6]
        self.patternDic["階上項目"]=[[
                                    '\s*階\s*|\s*符\s*号\s*'
                                ], 6]
        self.patternDic["断面リスト"]=[[
                                    '断面リスト'
                                ], 10]
        self.patternDic["項目名2"]=[[
                                    '(\s*上端\s*)'+    # 上端
                                    '|'+'(\s*下端\s*)'+ # 下端
                                    '|'+'(\s*X)\s*'+ # X
                                    '|'+'(\s*Y\s*)' # Y
                                    # '|'+'(\s*材料\s*)' # 主筋
                                ] ,5]
        self.patternDic["柱符号"]=[[
                                    '(\s*C\d{1,2}\s*)'       # C1 C10
                                # '|'+'(\s*P\d{1,2}\s*)'        # P1 P10
                                ], 6]
        self.patternDic["柱符号2"]=[[
                                    '(\s*\S*\d{1,2}C\d{1,2}\s*)'+     # 10C1 10C10
                                '|'+'(\s*\S*\d{1,2}P\d{1,2}\s*)'      # 10P1 10P10
                                ],8]
        
        self.patternDic["断面寸法"]=[[
                                    '(\s*\d+\s*(×|x|ｘ)\s*\d+(\s*\(\S+\))*\s*)'+         # 500×500(Fc24) 500 × 500(Fc24) 500 × 500 (Fc24)
                                '|'+'(\s*\d+,\d+\s*(×|x|ｘ)\s*\d+(\s*\(\S+\))*\s*)'+     # 2,500×500(Fc24) 2,500 × 500(Fc24) 2,500 × 500 (Fc24)
                                '|'+'(\s*\d+\s*(×|x|ｘ)\s*\d+,\d+(\s*\(\S+\))*\s*)'+     # 500×2,500(Fc24) 500 × 2,500(Fc24) 500 × 2,500 (Fc24)
                                '|'+'(\s*\d+,\d+\s*(×|x|ｘ)\s*\d+,\d+(\s*\(\S+\))*\s*)'  # 2,500×2,500(Fc24) 2,500 × 2,500(Fc24) 2,500 × 2,500 (Fc24)
                                
                                    # \s*：スペース無または１個 
                                    # (×|x) ：x又は×
                                    # (\s*\(\S+\))* ：(Fc24)がある場合もない場合も含む
                                ], 25]
        self.patternDic["断面寸法2"]=[[
                                    '(\s*\S+\s*(×|x|ｘ)\s*\S+\s*)'       # B × D 
                                ], 10]

        self.patternDic["コンクリート強度"]=[[
                                '(\s*\(*(Fc|FC|fc)\d+\)*\s*)'+            # Fc30 FC30 fc30 (Fc30) (FC30) (fc30)
                                # '|'+'((Fc|FC|fc)\d+)'+
                                '|'+'(\s*\(*(Fc|FC|fc)\s*=\s*\d+\)*\s*)'  # Fc=30 Fc = 30 (Fc=30) (Fc = 30)
                                ], 8]
        
        self.patternDic["フープ筋"]=[[
                                '(\s*\d{1}-\w+\d{2}@\d+\s*)'+         # 2-D13@200 2-TA13@150
                                '|'+'(\s*-\w+\d{2}@\d+\s*)' +          # D13@200
                                '|'+'(\s*-\w+\d{2}\s*@\s*\d+\s*)' +     # D13@ 200
                                '|'+'(\s*\d{1}\s*-\w+\d{2}\s*@\d+\s*)' +   # 5 -D13@200
                                '|'+'(\s*\d{1}\s*-\w+\d{2}\s*@\s*\d+\s*)'    # 5 -D13@ 200
                                ], 12]
        
        self.patternDic["腹筋"]=[[
                                '(\s*\d{1,2}-D13\s*)'+                 # 2-D13
                                '|'+'(\s*\d{1,2}-D10\s*)'                    # 2-D10
                                ], 16]
        
        self.patternDic["主筋"]=[[
                                '(\s*\d{1,2}/\d{1,2}-D\d{2}\s*)'+                 # 2/4-D25 10/10-D25
                                '|'+'(\s*\d{1,2}-D\d{2}\s*)'+                     # 2-D25 10-D25
                                '|'+'(\s*\d{1,2}/\d{1,2}/\d{1,2}-D\d{2}\s*)'+     # 2/2/4-D25 10/10/10-D25
                                '|'+'(\s*\d{1,2}-D\d{2}\s*(,|\+)\s*\d{1,2}-D\d{2}\s*)'   # 2-D25,10-D25 2-D25+10-D25
                                ], 16]
        
        self.patternDic["材料"]=[[
                                    '(\s*SD\d+\w*\s*)'+       # SD295A,SD345
                                '|'+'(\s*SPR\d+\w*\s*)' +      # SPR685,SPR685A
                                '|'+'((\s*(X|Y):SD)\d+\w*\s*)' +      # X:SD390 Y:SD345
                                '|'+'(\s*X:SD\d+\D*\s{1}Y:SD\d+\D*\s*)'       # X:SD390 Y:SD345
                                ],10]
        
        self.patternDic["階"]=[[
                                '(\s*(\d+|R)FL(\s*\層)*\s*)'+     # 10FL 10FL 層 RFL RFL 層
                                '|'+'(\s*(\d+|R)F(\s*\階)*\s*)'+     # 10F 10F 階 RF RF 階
                                '|'+'(\s*\d{1}\s*)'+              # 1
                                '|'+'(\s*\d{2}\s*)'+              # 20
                                '|'+'(\s*R\s*)'                   # R
                                ], 8]
        self.patternDic["日付"]=[[
                                '(\s*\d{4}/\d{1,2}/\d{1,2}\s*)'  # 2024/01/31
                                ], 12]
        self.patternDic["かぶり"]=[[
                                '(\s*\d+(\d+.\d+)*\s*/\s*\d+(\d+.\d+)*\s*)'+      # 50/50 50/37.5 50.5/50 50.5/50.5
                                '|'+'(\s*\d+(\d+.\d+)*\s*)'+
                                '|'+'(\s*\d{3}\s*)'              # 20
                                ], 12]
        self.patternDic["X通"]=[['\s*X\d+\Z\s*'], 4]
        self.patternDic["Y通"]=[['\s*Y\d+\Z\s*'], 4]
        
        self.PatternKeys = list(self.patternDic.keys())
    #end def
        
    
    #======================================
    #   記号パターンから結果を返す関数
    #======================================
    def checkPattern(self,word):
        # print(word)
        for key in self.PatternKeys:
            [p1,n] = self.patternDic[key]
            if len(word) <= n:
                for p in p1:
                    # if re.match(p,word):
                    if re.fullmatch(p,word):
                        if key == "階" and word.isnumeric():
                            if int(word) >= 30 :
                                return "かぶり"
                            else:
                                if word[0] != "0":
                                    return key
                                else:
                                    return ""
                                #end if
                            #end if
                        elif key == "主筋" :
                            if "D13" in word or "D10" in word:
                                return "腹筋"
                            else:
                                return key
                            #end if
                        elif key == "かぶり" and word.isnumeric():
                            if int(word) <= 150 :
                                if word[0] != "0":
                                    return key
                                else:
                                    return ""
                                #end if
                                # return "かぶり"
                            else:
                                return ""
                            #end if
                        else:
                            return key
                        #end if
                    #end if
                #next
            #end if
        #next
        words = []
        if " " in word or "," in word:
            words = word.split(" ")
            if len(words) == 0:
                words = word.split(",")
            #end if
            if len(words) > 0:
                for word1 in words:
                    if word1 != "":
                        for key in self.PatternKeys:
                            [p1,n] = self.patternDic[key]
                            for p in p1:
                                # if re.match(p,word):
                                if re.fullmatch(p,word1):
                                    return key
                                #end if
                            #next
                        #next
                    #end if
                #next
            #end if
        #end if
        return ""
    #end def
    

    def isMember(self,key,word):
        if key in self.PatternKeys:
            [p1,n] = self.patternDic[key]
            flag = False
            for p in p1:
                if re.fullmatch(p,word) :
                    return True
                    break
                #end if
            #next
            return flag
        else:
            return None
        #end if

    @property
    def KeyNames(self):
        return self.PatternKeys
    #end def

if __name__ == '__main__':

    pm1 = PatternCheck()

    data1 = []

    # # 断面寸法2
    data1.append("2-D25 + ")
    data1.append("D")
    # data1.append("x500")
    # data1.append("x 1,500")
    # data1.append("800×")
    # data1.append("1,850x")

    data1.append("X:SD390 Y:SD345")
    data1.append("3G1,4G1A,5G1")
    
    data1.append("150")
    data1.append("300")
    # 梁符号1
    data1.append("G1")
    data1.append("G20")
    data1.append("G1A")
    data1.append("G20A")
    data1.append(" G1A")
    data1.append(" G20A ")
    data1.append("FG1")
    data1.append("FG1A")
    data1.append("FCG1")
    data1.append("FCG11A")
    # 小梁符号
    data1.append("B1")
    data1.append("B20")
    data1.append("B1A")
    data1.append("B20A")
    data1.append(" B1A")
    data1.append(" B20A ")
    data1.append("CB1")
    data1.append("CB1A")
    data1.append("FB1")
    data1.append("FB11A")
    data1.append("FCG1")
    data1.append("FCG11A")
    # 片持梁
    data1.append("CG1")
    data1.append("CG20")
    data1.append("FCG1A")
    data1.append("FCG20A")
    data1.append("FCG20-1")
    data1.append("FCG20A-1")
    # 壁
    data1.append("W15")
    data1.append("W15a")
    data1.append("EW165")
    data1.append("EW18A")
    # 梁符号2
    data1.append("RG1")
    data1.append("RG1A")
    data1.append("9G1")
    data1.append("9G1A")
    data1.append("12G10")
    data1.append("12G10A")
    data1.append("3G1,4G1")
    data1.append("3G1A,4G1A")
    data1.append("3G1,4G1A,5G1")
    # 梁断面位置
    data1.append("全断面")
    data1.append("中央")
    data1.append("端部")
    data1.append("左端")
    data1.append("右端")
    data1.append("1通端")
    data1.append("2通端")
    data1.append("1通,2通端")
    data1.append("1通 , 2通端")
    data1.append("元端")
    data1.append("先端")
    data1.append("1通・3通端")
    data1.append("Y1 端")
    data1.append("Y2 端")
    data1.append("全断")
    
    # 項目名1Y1 端,Y2 端,Y3 端
    data1.append("符号名")
    data1.append("コンクリート")
    data1.append("主筋")
    data1.append("主筋  Y")
    data1.append("かぶり")
    data1.append("かぶり・あき")
    data1.append("あばら筋")
    data1.append("帯筋")
    # 項目名2
    data1.append("上端")
    data1.append("下端")
    data1.append("上端 mm")
    data1.append("下端 mm")
    data1.append("上端mm")
    data1.append("X")
    data1.append("Y")
    data1.append("材料")
    # 主筋
    data1.append("4-D25")
    data1.append("4/1-D25")
    data1.append("4/2-D25")
    data1.append(" 4/1-D25 ")
    data1.append("  4/2-D25 ")
    data1.append("10/10/20-D25")
    data1.append("7-D29")
    data1.append("2-D29,4-D22")
    data1.append("2-D29+4-D22")
    data1.append("24-D35+ 8-D38")
    # 腹筋
    data1.append("4-D13")
    data1.append(" 4-D10 ")
    # フープ筋-TA13 @100
    data1.append("2-D13@200")
    data1.append("2-TA13@150")
    data1.append("-D13@150")
    data1.append("5 -K16@150")
    data1.append("-D13@ 150")
    data1.append("-TA13 @100")
    
    # 柱符号
    data1.append("C1")
    data1.append("C10")
    data1.append("P1")
    data1.append("P10")
    # 柱符号2
    data1.append("3C1")
    data1.append("10C10")
    data1.append("3P1")
    data1.append("10P10")
    # 断面寸法
    data1.append("800×800")
    data1.append("1600x500")
    data1.append("800×800(Fc30)")
    data1.append("850x700")
    data1.append("1600x500")
    data1.append("850x700(Fc30)")
    data1.append("1600x500")
    data1.append("850x1,700(Fc30)")
    data1.append("1,850x700(Fc30)")
    data1.append("1,850x1,700(Fc30)")
    data1.append("850 x 700")
    data1.append("1600 x 500")
    data1.append("850 x 1,700")
    data1.append("1,850 x 700")
    data1.append("1,850 x 1,700")
    data1.append("450 × 800 (Fc24)")
    data1.append("450×800 (Fc24)")
    data1.append("850x1,700 (Fc30)")
    data1.append("1,850x700 (Fc30)")
    data1.append("1,850x1,700 (Fc30)")
    data1.append("450 × 800 (Fc24)")
    data1.append("850 x 1,700 (Fc30)")
    data1.append("1,850 x 700 (Fc30)")
    data1.append("1,850 x 1,700 (Fc30)")
    data1.append("500 x 1,800")
    data1.append("950ｘ1,800")
    # コンクリート強度
    data1.append("(Fc30)")
    data1.append("Fc30")
    data1.append("(FC30)")
    data1.append("FC30")
    data1.append("Fc=30")
    data1.append("Fc = 30")
    data1.append("(FC30)")
    data1.append("(Fc=30)")
    data1.append("(Fc = 30)")
    # 材料
    data1.append("SD345")
    data1.append("SD295A")
    data1.append("SPR635")
    data1.append("X:SD390")
    data1.append("Y:SD390A")
    data1.append("X:SD390 Y:SD345")
    # 階
    data1.append("RFL")
    data1.append("10FL")
    data1.append("1FL")
    data1.append("4FL")
    data1.append("RFL 層")
    data1.append("10FL 層")
    data1.append("1FL 層")
    data1.append("RF 階")
    data1.append("10F 階")
    data1.append("1F 階")
    data1.append("R")
    data1.append("10")
    data1.append("1")
    data1.append("05")
    data1.append("CFL")
    # 日付
    data1.append("2024/01/31")
    data1.append("2024/1/1")
    # かぶり
    data1.append("37.5")
    data1.append("30")
    data1.append("50/50")
    data1.append("50/37.5")
    data1.append("37.5/50")
    data1.append("50.5/50.5")
    data1.append("50 / 50")
    data1.append("50 / 37.5")
    data1.append("37.5 / 50")
    data1.append("50.5 / 50.5")
    data1.append("200")
    

    for d in data1:
        print(d,"=",pm1.checkPattern(d))

    a = 0