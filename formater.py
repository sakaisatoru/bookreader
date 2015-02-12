#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright 2014 sakaisatoru <endeavor2wako@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

""" フォーマッタ

    準拠及び参考資料

        青空文庫より
            青空文庫収録ファイルへの記載事項
                http://www.aozora.gr.jp/guide/kisai.html
            【テキスト中に現れる記号について】
                http://www.aozora.gr.jp/KOSAKU/txt_chu_kigo.html
            注記一覧
                http://www.aozora.gr.jp/annotation/
"""


import jis3
from readersub import ReaderSetting, AozoraDialog
from aozoracard import AuthorList
import aozoraaccent

import sys
import codecs
import re
import os.path
import datetime
import unicodedata
import logging
import xml.sax.saxutils
import tempfile
import math
import copy
from contextlib import contextmanager
from HTMLParser import HTMLParser

import gtk
import cairo
import pango
import pangocairo
import gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)



class AozoraTag():
    """ 青空タグの検出　ネスティング対応版
    """
    def __init__(self, regex=ur'［＃.*?］'):
        self.reTmp = re.compile(regex)

    def sub_1(self, s, pos=0):
        """ s[pos]から終わり迄、［＃ を探してインデックスを返す。
            見つからない場合は -1 を返す。
        """
        try:
            while 1:
                if s[pos:pos+2] == u'［＃':
                    index = self.sub_1(s, pos+2)
                    if index != -1:
                        if s[index] == u'］':
                            """ 例えば[# [# ] の場合、最初の[# のペアとして
                                2番目の [# がindexとして戻るため、ここでチェ
                                ックする。
                            """
                            index = pos
                    break
                elif s[pos] == u'］':
                    index = pos
                    break
                else:
                    pos += 1
        except IndexError:
            index = -1
        return index

    def search(self, s, pos=0):
        """ re.search の代替
        """
        index = self.sub_1(s,pos)
        return None if index == -1 else self.reTmp.search(s,index)

class AozoraScale():
    """ 描画時のピクセル長の計算等
    """
    # Serif(TakaoEx明朝)における、対全角文字比
    charwidth_serif = {
            u' ':0.312500,  u'!':0.312500,  u'"':0.375000,  u'#':0.625000,
            u'$':0.625000,  u'&':0.750000,  u'%':0.812500,  u"'":0.200000,
            u'(':0.375000,  u')':0.375000,  u'*':0.250000,  u'+':0.687500,
            u',':0.250000,  u'-':0.315000,  u'.':0.250000,  u'/':0.500000,
            u'0':0.500000,  u'1':0.500000,  u'2':0.500000,  u'3':0.500000,
            u'4':0.500000,  u'5':0.500000,  u'6':0.500000,  u'7':0.500000,
            u'8':0.500000,  u'9':0.500000,  u':':0.250000,  u';':0.250000,
            u'<':0.687500,  u'=':0.687500,  u'>':0.687500,  u'?':0.500000,
            u'@':0.875000,  u'A':0.733333,  u'B':0.733333,  u'C':0.733333,
            u'D':0.800000,  u'E':0.666667,  u'F':0.666667,  u'G':0.800000,
            u'H':0.800000,  u'I':0.400000,  u'J':0.466667,  u'K':0.733333,
            u'L':0.600000,  u'M':0.933333,  u'N':0.800000,  u'O':0.800000,
            u'P':0.666667,  u'Q':0.800000,  u'R':0.666667,  u'S':0.600000,
            u'T':0.600000,  u'U':0.800000,  u'V':0.733333,  u'W':0.933333,
            u'X':0.733333,  u'Y':0.666667,  u'Z':0.600000,  u'[':0.312500,
            u'\\':0.500000, u']':0.312500,  u'^':0.500000,  u'_':0.500000,
            u'`':0.500000,  u'a':0.562500,  u'b':0.625000,  u'c':0.562500,
            u'd':0.625000,  u'e':0.562500,  u'f':0.312500,  u'g':0.562500,
            u'h':0.625000,  u'i':0.312500,  u'j':0.312500,  u'k':0.562500,
            u'l':0.312500,  u'm':0.875000,  u'n':0.625000,  u'o':0.562500,
            u'p':0.625000,  u'q':0.625000,  u'r':0.375000,  u's':0.500000,
            u't':0.312500,  u'u':0.625000,  u'v':0.562500,  u'w':0.750000,
            u'x':0.562500,  u'y':0.562500,  u'z':0.437500,  u'{':0.312500,
            u'|':0.187500,  u'}':0.312500,  u'~':0.500000   }

    # 文字サイズ変更への暫定対応(公比1.2、端数切り上げ、一部調整)
    fontsizefactor = {
            u'normal':1.0,
            #u'size="smaller"':0.8333333333333334,   u'size="larger"':1.2000,
            u'size="smaller"':0.82,   u'size="larger"':1.2000,
            #u'size="small"':0.8333333333333334,     u'size="large"':1.2000,
            u'size="small"':0.82,     u'size="large"':1.2000,
            u'size="x-small"':0.6944444444444445,   u'size="x-large"':1.4400,
            u'size="xx-small"':0.578703703703703,   u'size="xx-large"':1.7280,
            u'<sup>':0.82,          u'<sub>':0.82 }
            #u'<sup>':0.8333333333333334,          u'<sub>':0.8333333333333334 }

    reFontsizefactor = re.compile( ur'(?P<name>size=".+?")' )

    def __init__(self):
        pass

    def linelengthcount(self, sline):
        """ 文字列の長さを数える
            文字の大きさ変更等に対応
            <tag></tag> はカウントしない。
        """
        l = 0.0
        inTag = False
        tagname = u''
        tagstack = []
        fontsizename = u'normal'

        for s in sline:
            if s == u'>':
                # tagスタックの操作
                tagname += s
                if tagname[:2] == u'</':
                    # </tag>の出現とみなしてスタックから取り除く
                    # ペアマッチの処理は行わない
                    tmp = self.reFontsizefactor.search(self.tagstack.pop())
                    if tmp:
                        if tmp.group('name') in self.fontsizefactor:
                            fontsizename = u'normal' # 文字サイズの復旧
                else:
                    tmp = self.reFontsizefactor.search(tagname)
                    if tmp:
                        if tmp.group('name') in self.fontsizefactor:
                            fontsizename = tmp.group('name') # 文字サイズ変更
                    self.tagstack.append(tagname)
                    tagname = u''
                inTag = False
            elif s == u'<':
                inTag = True
                tagname = s
            elif inTag:
                tagname += s
            else:
                # 画面上における全長を計算
                l += self.charwidth(s) * self.fontsizefactor[fontsizename]
        return int(math.ceil(l))
        #return int(math.floor(l))
        #return int(round(l))

    def charwidth(self, lsc):
        """ 文字の幅を返す
            全角 を１とする
        """
        if lsc in self.charwidth_serif:
            lcc = self.charwidth_serif[lsc]
        elif unicodedata.east_asian_width(lsc) == 'Na':
            # 非全角文字
            lcc = 0.5
        else:
            # 全角文字
            lcc = 1.0
        return lcc

    def fontmagnification(self, s):
        """ 文字倍率を返す
        """
        reTmp = self.reFontsizefactor.search(s)
        if reTmp:
            s = reTmp.group(u'name')
            if s in self.fontsizefactor:
                n = self.fontsizefactor[s]
        elif s in self.fontsizefactor:
            n = self.fontsizefactor[s]
        else:
            n = 1
        return n

    def zentoi(self, s):
        """ 全角文字列を整数に変換する
        """
        n = 0
        for s2 in s:
            j = u'０１２３４５６７８９'.find(s2)
            if j != -1:
                n *= 10
                n += j
            else:
                break
        return n



class Aozora(ReaderSetting, AozoraScale):
    """
    """
    # ヘッダ・フッタ境界
    sHeader = u'-------------------------------------------------------'
    reFooter = re.compile(ur'(?P<type>(^(翻訳の)?底本：)|(［＃本文終わり］))')
    # 外字置換
    reGaiji3 = re.compile(ur'(［＃.*?、.*?(?P<number>\d+\-\d+\-\d+\d*)］)')
    reGaiji4 = re.compile(ur'(［＃.+?、U\+(?P<number>[0-9A-F]+?)、.+?］)')
    reGaiji5 = re.compile(ur'(［＃(?P<name>「.+?」)、.+?］)' )
    # 役物置換
    reKunoji = re.compile(ur'(／＼)')
    reGunoji = re.compile(ur'(／″＼)')
    reNonokagi = re.compile(ur'(“(?P<name>.+?)”)')
    # 青空文庫タグ抽出
    reCTRL = re.compile(ur'(?P<aozoratag>［＃.*?］)')
    reCTRL2 = AozoraTag(ur'(?P<aozoratag>［＃.*?］)') # ネスティング対応
    reCTRL3 = re.compile(ur'(［＃(?P<name>.*?)］)')
    # 傍線・傍点
    reBouten = re.compile(ur'(［＃「(?P<name>.+?)」に(?P<type>.*?)' + \
                        ur'(?P<type2>(傍点)|(傍線)|(波線)|(破線)|(鎖線))］)')
    reBouten2 = re.compile(ur'［＃(?P<type>.*?)' + \
                        ur'(?P<type2>(傍点)|(傍線)|(波線)|(破線)|(鎖線))］')
    reBouten2owari = re.compile(ur'［＃(?P<type>.*?)' + \
                        ur'(?P<type2>(傍点)|(傍線)|(波線)|(破線)|(鎖線))' + \
                        ur'終わり］' )

    reGyomigikogaki = re.compile(ur'(［＃「(?P<name>.+?)」は' +
                        ur'(?P<type>(行右小書き)|(上付き小文字)|' +
                        ur'(行左小書き)|(下付き小文字))］)')

    reMama = re.compile(ur'(［＃「(?P<name>.+?)」に「(?P<mama>.??ママ.??)」の注記］)')
    reMama2 = re.compile(ur'(［＃「(?P<name>.+?)」は(?P<mama>.??ママ.??)］)')
    reKogakiKatakana = re.compile(ur'(［＃小書(き)?片仮名(?P<name>.+?)、.+?］)')

    reRubi = re.compile(ur'《.*?》')
    reRubiclr = re.compile(ur'＃')
    reRubimama = re.compile(ur'(［＃ルビの「(?P<name>.+?)」はママ］)')

    reLeftBousen = re.compile(ur'［＃「(?P<name>.+?)」の左に(?P<type>二重)?傍線］')

    reFutoji = re.compile(ur'［＃「(?P<name>.+?)」は太字］')
    reSyatai = re.compile(ur'［＃「(?P<name>.+?)」は斜体］')

    # 左注記
    reLeftrubi = re.compile(ur'［＃「(?P<name>.+?)」の左に「(?P<rubi>.+?)」の注記］')

    # キャプション
    reCaption = re.compile(ur'(［＃「(?P<name>.*?)」はキャプション］)')
    # 文字サイズ
    reMojisize = re.compile(ur'(［＃「(?P<name2>.+?)」は(?P<size>.+?)段階(?P<name>.+?)な文字］)')
    reMojisize2 = re.compile(ur'(［＃(ここから)?(?P<size>.+?)段階(?P<name>.+?)な文字］)')

    # 処理共通タグ ( </span>生成 )
    reOwari = re.compile(
                ur'(［＃(ここで)?((大き)|(小さ))+な文字終わり］)|' +
                ur'(［＃(ここで)?斜体終わり］)|' +
                ur'(［＃(ここで)?太字終わり］)')

    # 縦中横
    reTatenakayoko = re.compile(ur'(［＃「(?P<name>.+?)」は縦中横］)')

    # 未実装タグ
    reOmit = re.compile(
                ur'(［＃(ここから)??横組み］)|'+
                ur'(［＃(ここで)??横組み終わり］)|' +
                ur'(［＃割り注.*?］)|' +
                ur'(［＃「.+?」は底本では「.+?」］)|' +
                ur'(［＃ルビの「.+?」は底本では「.+?」］)')

    """ ソースに直書きしているタグ
        u'［＃ページの左右中央］'
    """

    # 字下げ、字詰、地付き、地寄せ（地上げ）
    reIndent = re.compile(ur'［＃(天から)??(?P<number>[０-９]+?)字下げ］')
    reIndentStart = re.compile(ur'［＃ここから(?P<number>[０-９]+?)字下げ］')
    reKaigyoTentsuki = re.compile(ur'［＃ここから改行天付き、折り返して(?P<number>[０-９]+?)字下げ］')
    reKokokaraSage = re.compile(ur'［＃ここから(?P<number>[０-９]+?)字下げ、折り返して(?P<number2>[０-９]+?)字下げ］')
    reIndentEnd = re.compile(ur'［＃(ここで)?字下げ終わり］|［＃(ここで)?字下げおわり］')

    reJiage = re.compile(ur'((?P<name2>.+?)??(?P<tag>(［＃地付き］)|(［＃地から(?P<number>[０-９]+?)字上げ］))(?P<name>.+?)??$)')
    reKokokaraJiage = re.compile(ur'［＃ここから地から(?P<number>[０-９]+?)字上げ］')
    reJiageowari = re.compile(ur'［＃ここで字上げ終わり］')

    reKokokaraJitsuki = re.compile(ur'［＃ここから地付き］')
    reJitsukiowari = re.compile(ur'［＃ここで地付き終わり］')

    reJizume = re.compile(ur'［＃ここから(?P<number>[０-９]+?)字詰め］')
    reJizumeowari = re.compile(ur'［＃ここで字詰め終わり］')

    # 罫囲み
    reKeikakomi = re.compile(ur'［＃ここから罫囲み］')
    reKeikakomiowari = re.compile(ur'［＃ここで罫囲み終わり］')

    # 見出し
    reMidashi = re.compile(ur'［＃「(?P<midashi>.+?)」は(同行)??(?P<midashisize>大|中|小)見出し］')
    reMidashi2name = re.compile(ur'((<.+?)??(?P<name>.+?)[<［\n]+?)')
    reMidashi2 = re.compile(ur'(［＃(ここから)?(?P<midashisize>大|中|小)見出し］)')
    reMidashi2owari = re.compile(ur'(［＃(ここで)??(?P<midashisize>大|中|小)見出し終わり］)')

    # 改ページ・改丁・ページの左右中央
    reKaipage = re.compile(ur'［＃改ページ］|［＃改丁］|［＃改段］|［＃改見開き］')

    # 挿図
    #reFig = re.compile(ur'(［＃(?P<name>.+?)）入る］)' )
    reFig = re.compile(
        ur'(［＃(.+?)?（(?P<filename>[\w\-]+?\.png)(、横\d+?×縦\d+?)??）入る］)')
    reFig2 = re.compile(
        ur'(［＃「(?P<caption>.+?)」のキャプション付きの(.+?)（(?P<filename>[\w\-]+?\.png)(、横\d+?×縦\d+?)??）入る］)')

    # 訓点・返り点
    reKuntenOkuri = re.compile(ur'(［＃（(?P<name>.+?)）］)')
    reKaeriten = re.compile(
                    ur'(［＃(?P<name>[レ一二三四五六七八九'+
                    ur'上中下' + ur'甲乙丙丁戊己庚辛壬癸' + ur'天地人' +
                    ur'元亨利貞' + ur'春夏秋冬'+ ur'木火土金水'+ ur']+?)］)')

    # フッターにおける年月日刷を漢数字に変換
    reNenGetsuNichi = re.compile(
        ur'((?P<year>\d+?)(（((明治)|(大正)|(昭和)|(平成))??(?P<gengo>\d+?)）)??年)|'+
        ur'((?P<month>\d+?)月)|'+
        ur'((?P<day>\d+?)日)|' +
        ur'((?P<ban>\d+?)版)|' +
        ur'((?P<suri>\d+?)刷)')

    # 禁則
    kinsoku = u'\r,)]｝、）］｝〕〉》」』】〙〗〟’”｠»ヽヾーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻‐゠–〜?!‼⁇⁈⁉・:;。、！？'
    kinsoku2 = u'([{（［｛〔〈《「『【〘〖〝‘“｟«〳〴'
    kinsoku4 = u'\r,)]｝、）］｝〕〉》」』】〙〗〟’”｠»。、'

    # Pangoタグへの単純な置換
    dicAozoraTag = {
        u'［＃行右小書き］':u'<sup>',   u'［＃行右小書き終わり］':u'</sup>',
        u'［＃行左小書き］':u'<sub>',   u'［＃行左小書き終わり］':u'</sub>',
        u'［＃上付き小文字］':u'<sup>', u'［＃上付き小文字終わり］':u'</sup>',
        u'［＃下付き小文字］':u'<sub>', u'［＃下付き小文字終わり］':u'</sub>',
        u'［＃ここからキャプション］':u'<span size="smaller">',
            u'［＃ここでキャプション終わり］':u'</span>',
        u'［＃左に傍線］':u'<span underline="single">',
            u'［＃左に傍線終わり］':u'</span>',
        u'［＃左に二重傍線］':u'<span underline="double">',
            u'［＃左に二重傍線終わり］':u'</span>',
        u'［＃太字］':u'<span font_desc="Sans">',
        u'［＃ここから太字］':u'<span font_desc="Sans">',
        u'［＃斜体］':u'<span style="italic">',
        u'［＃ここから斜体］':u'<span style="italic">' }

    # 文字の大きさ
    dicMojisize = {
        u'大き１':u'large',    u'大き２':u'x-large',
        u'小さ１':u'small',    u'小さ２':u'x-small' }

    # Pangoタグを除去する
    reTagRemove = re.compile(ur'<[^>]*?>')


    def __init__( self, chars=40, lines=25 ):
        ReaderSetting.__init__(self)
        AozoraScale.__init__(self)
        self.destfile = os.path.join(self.get_value(u'workingdir'), u'view.txt')
        self.mokujifile = os.path.join(self.get_value(u'workingdir'),u'mokuji.txt')
        self.readcodecs = u'shift_jis'
        self.pagelines = int(self.get_value(u'lines'))  # 1頁の行数
        self.chars = int(self.get_value(u'column'))     # 1行の最大文字数
        self.linewidth = int(self.get_value(u'linewidth')) # 1行の幅
        self.charsmax = self.chars - 1          # 最後の1文字は禁則処理用に確保
        self.pagecounter = 0
        self.set_source( None )
        self.BookTitle = u''
        self.BookAuthor = u''
        self.BookTranslator = u''

    def set_source( self, s ):
        """ 青空文庫ファイルをセット
        """
        self.sourcefile = s if s else u''
        self.set_aozorabunkocurrent( self.sourcefile )

    def get_form( self ):
        """ ページ設定を返す。
        """
        return (self.chars, self.pagelines)

    def get_outputname(self):
        """ フォーマット済みのファイル名を返す。現在は単純に中間ファイル名を返す
        """
        return self.destfile            # フォーマット済ファイル出力先

    def get_booktitle(self):
        """ 処理したファイルの書名、著者名を返す。
        """
        return (self.BookTitle, self.BookAuthor)

    def get_source(self):
        """ 処理したファイル名を返す。
        """
        return self.sourcefile

    def mokuji_itre(self):
        """ 作成した目次のイテレータ。UI向け。
        """
        with file(self.mokujifile,'r') as f0:
            for s in f0:
                yield s.strip('\n')

    def get_booktitle_sub( self, sourcefile=u'' ):
        """ 書名・著者名を取得する。

            青空文庫収録ファイルへの記載事項
            http://www.aozora.gr.jp/guide/kisai.html
                *作品の表題
                 原作の表題（翻訳作品で、底本に記載のある場合）
                 副題（副題がある場合）
                 原作の副題（副題がある翻訳作品で、底本に記載のある場合）
                *著者名
                 翻訳者名（翻訳の場合）
        """
        sBookTitle = u''
        sOriginalTitle = u''
        sSubTitle = u''
        sOriginalsubTitle = u''
        sBookAuthor = u''
        sBookTranslator = u''
        sBuff = []

        if not sourcefile:
            sourcefile = self.sourcefile

        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            sBookTitle = f0.readline().rstrip('\r\n')
            while len(sBuff) < 5:
                lnbuf = f0.readline().rstrip('\r\n')
                #   空行に出くわすか、説明が始まったら終わる
                if not lnbuf or lnbuf == self.sHeader:
                    break
                sBuff.append(lnbuf)
        try:
            sTmp = sBuff.pop()
            if sTmp[-1] == u'訳':
                sBookTranslator = sTmp
                sTmp = sBuff.pop()
                if sBookTranslator[-2:] == u'改訳':
                    sBookTranslator = sTmp + u' / ' + sBookTranslator
                    sTmp = sBuff.pop()
            sBookAuthor = sTmp
            sSubTitle = sBuff.pop()
            if sBookTranslator != u'':
                sOriginalTitle, sSubTitle = sSubTitle, sOriginalTitle
            sSubTitle = sBuff.pop()
            sOriginalsubTitle = sBuff.pop()
            sOriginalsubTitle, sSubTitle = sSubTitle, sOriginalsubTitle
        except IndexError:
            pass

        if sBookTranslator:
            sBookAuthor = u'%s / %s' % (sBookAuthor ,sBookTranslator)

        sBookTitle = u'%s %s %s %s' % (sBookTitle, sSubTitle,
                                            sOriginalTitle, sOriginalsubTitle)

        return (sBookTitle.rstrip(), sBookAuthor)

    def formater_pass1( self, sourcefile=u''):
        """ フォーマッタ（第1パス）
            formater より呼び出されるジェネレータ。1行読み込んでもっぱら
            置換処理を行う。
        """
        if not sourcefile:
            sourcefile = self.sourcefile

        headerflag = False      # 書名以降の注釈部分を示す
        boutoudone = False      # ヘッダ処理が終わったことを示す
        footerflag = False
        aozorastack = []        # ［＃形式タグ用のスタック
        pangotagstack = []      # pango タグ用のスタック

        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            yield u'［＃ページの左右中央］' # 作品名を1ページ目に表示する為
            for lnbuf in f0:
                lnbuf = lnbuf.rstrip('\r\n')
                """ ヘッダ【テキスト中に現れる記号について】の処理
                    とりあえずばっさりと削除する
                """
                if self.sHeader == lnbuf:
                    headerflag = False if headerflag else True
                    continue
                if headerflag:
                    continue

                """ 前の行で閉じていなかった青空タグがあれば
                    復元する
                """
                if aozorastack != []:
                    while True:
                        try:
                            lnbuf = aozorastack.pop() + lnbuf
                        except IndexError:
                            break
                    aozorastack = []

                """ 空行及び冒頭の処理
                """
                if not lnbuf:  # len(lnbuf) == 0 よりわずかに速い
                    if boutoudone:
                        yield u'\n'
                    else:
                        boutoudone = True
                        yield u'［＃改ページ］\n'
                    continue

                """ アクセント分解 & を処理するので xml.sax より前に呼ぶこと
                """
                lnbuf = aozoraaccent.replace( lnbuf )

                """ tag 対策
                    pango で引っかかる & < > を 特殊文字に変換する
                """
                lnbuf = xml.sax.saxutils.escape( lnbuf )

                """ フッタ
                """
                tmp = self.reFooter.search(lnbuf)
                if tmp:
                    footerflag = True
                    if tmp.group('type') == u'［＃本文終わり］':
                        lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]

                """ くの字の置換
                """
                lnbuf = self.reKunoji.sub( u'〳〵', lnbuf )
                lnbuf = self.reGunoji.sub( u'〴〵', lnbuf )

                """ ダブルクォーテーションの、ノノカギへの置換
                    カテゴリを調べて、アルファベット以外及び記号以外の
                    何かが出現した場合に日本語とみなして置換する。
                """
                for tmp in self.reNonokagi.finditer( lnbuf ):
                    for s in tmp.group('name'):
                        if unicodedata.category(s) == 'Lo':
                            lnbuf = '%s〝%s〟%s' % (
                                 lnbuf[:tmp.start()],
                                tmp.group('name'),
                                lnbuf[tmp.end():] )
                            break

                """ ［＃　で始まるタグの処理
                """
                isRetry = False # タグが閉じなかった場合の再処理フラグ
                while True:
                    tmp = self.reCTRL2.search(lnbuf)
                    while tmp:
                        try:
                            if lnbuf[tmp.start()-1] == u'※':
                                tmp2 = self.reGaiji3.match(tmp.group())
                                if tmp2:
                                    # 外字置換（JIS第3、第4水準）
                                    k = jis3.sconv(tmp2.group('number'))
                                    if not k:
                                        logging.info( u'未登録の外字を検出：%s' % tmp.group())
                                        k = u'［'+tmp.group()[2:]
                                    lnbuf = lnbuf[:tmp.start()-1] + k + lnbuf[tmp.end():]
                                    tmp = self.reCTRL2.search(lnbuf)
                                    continue

                                tmp2 = self.reGaiji4.match(tmp.group())
                                if tmp2:
                                    # 外字置換（Unicode文字）
                                    try:
                                        k = unicodedata.lookup(
                                            u'CJK UNIFIED IDEOGRAPH-' + tmp2.group('number'))
                                    except KeyError:
                                        k = u'［'+tmp.group()[2:]
                                        logging.info( u'未定義の外字を検出：%s' % k )
                                    lnbuf = lnbuf[:tmp.start()-1] + k + lnbuf[tmp.end():]
                                    tmp = self.reCTRL2.search(lnbuf)
                                    continue

                                tmp2 = self.reKogakiKatakana.match(tmp.group())
                                if tmp2:
                                    #   小書き片仮名
                                    #   ヱの小文字など、JISにフォントが無い場合
                                    lnbuf = u'%s<span size="smaller">%s</span>%s' % (
                                        lnbuf[:tmp.start()].rstrip(u'※'),
                                        tmp2.group(u'name'),
                                        lnbuf[tmp.end():] )
                                    tmp = self.reCTRL2.search(lnbuf)
                                    continue

                                # JISにもUnicodeにも定義されていない文字の注釈
                                # ※［＃「」、底本ページ-底本行］ -> ※「」
                                tmp2 = self.reGaiji5.match(tmp.group())
                                if tmp2:
                                    lnbuf = lnbuf[:tmp.start()] + \
                                            tmp2.group(u'name') + lnbuf[tmp.end():]
                                    tmp = self.reCTRL2.search(lnbuf)
                                    continue
                        except IndexError:
                            pass

                        if tmp.group() in self.dicAozoraTag:
                            # 単純な Pango タグへの置換
                            lnbuf = lnbuf[:tmp.start()] + \
                                    self.dicAozoraTag[tmp.group()] + \
                                    lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reOmit.match(tmp.group()):
                            # 未実装タグの除去
                            logging.info( u'未実装タグを検出: %s' % tmp.group() )
                            self.loggingflag = True
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reFig2.match(tmp.group())
                        if tmp2:
                            # 挿図（キャプション付き他、独立段落）
                            # 次段で処理する
                            # reFigで分離できないのでここでトラップする
                            tmp = self.reCTRL2.search(lnbuf,tmp.end())
                            continue

                        tmp2 = self.reFig.match(tmp.group())
                        if tmp2:
                            # 挿図（段落内挿入）
                            # 拡大・縮小は行わない
                            try:
                                fname = tmp2.group(u'filename')
                                tmpPixBuff = gtk.gdk.pixbuf_new_from_file(
                                    os.path.join(self.get_value(u'aozoradir'),
                                        fname))
                                figheight = tmpPixBuff.get_height()
                                figwidth = tmpPixBuff.get_width()
                                if figwidth > self.linewidth * 2:
                                    # 大きな挿図(幅が2行以上ある)は独立表示へ変換する
                                    sNameTmp = u'［＃「＃＃＃＃＃」のキャプション付きの図（%s、横%d×縦%d）入る］' % (
                                            fname, figwidth, figheight)
                                    del tmpPixBuff
                                    lnbuf = lnbuf[:tmp.start()] + sNameTmp + lnbuf[tmp.end():]
                                    tmp = self.reCTRL2.search(lnbuf)
                                    continue

                                # 図の高さに相当する文字列を得る
                                sPad = u'＃' * int(math.ceil(
                                    float(figheight)/float(self.get_value('fontheight'))))
                                del tmpPixBuff
                            except gobject.GError:
                                # ファイルI/Oエラー
                                self.loggingflag = True
                                logging.info(
                                    u'画像ファイル %s の読み出しに失敗しました。' % fname )
                                lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                                tmp = self.reCTRL2.search(lnbuf)
                                continue

                            lnbuf = lnbuf[:tmp.start()] + \
                                    u'<aozora img="%s" width="%s" height="%s">%s</aozora>' % (
                                        fname, figwidth, figheight, sPad) + \
                                    lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reLeftrubi.match(tmp.group())
                        if tmp2:
                            # 左注記
                            tmpStart,tmpEnd = self.honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<aozora leftrubi="%s" length="%s">%s</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                        tmp2.group(u'rubi'),
                                        len(tmp2.group(u'name')),
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf,tmpStart)
                            continue

                        tmp2 = self.reCaption.match(tmp.group())
                        if tmp2:
                            #   キャプション
                            #   暫定処理：小文字で表示
                            tmpStart,tmpEnd = self.honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name'))
                            #lnbuf = u'%s<span size="smaller">%s</span>%s%s' % (

                            # 横書きにするので内容への修飾を外す
                            sTmp = lnbuf[tmpStart:tmpEnd]
                            postmp = sTmp.find(u'［＃')
                            if postmp != -1:
                                postmp2 = sTmp.rfind(u'］')
                                if postmp2 != -1:
                                    sTmp = sTmp[:postmp]+sTmp[postmp2+1:]
                            lnbuf = u'%s<aozora caption="%s" size="smaller">　</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                        sTmp,
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf,tmpStart)
                            continue

                        tmp2 = self.reMojisize.match(tmp.group())
                        if tmp2:
                            #   文字の大きさ
                            #   文字の大きさ２　と互換性がないので、こちらを
                            #   先に処理すること
                            sNameTmp = tmp2.group(u'name') + tmp2.group(u'size')
                            try:
                                sSizeTmp = self.dicMojisize[sNameTmp]
                            except KeyError:
                                sSizeTmp = u'xx-small' if sNameTmp[:2] == u'小さ' else u'xx-large'

                            tmpStart,tmpEnd = self.honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name2'))
                            lnbuf = u'%s<span size="%s">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            sSizeTmp,
                                                lnbuf[tmpStart:tmpEnd],
                                                lnbuf[tmpEnd:tmp.start()],
                                                    lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reMojisize2.match(tmp.group())
                        if tmp2:
                            #   文字の大きさ２
                            #   文字の大きさ　と互換性がない（誤検出する）ので、
                            #   こちらを後に処理すること
                            sNameTmp = tmp2.group(u'name') + tmp2.group(u'size')
                            try:
                                sSizeTmp = self.dicMojisize[sNameTmp]
                            except KeyError:
                                sSizeTmp = u'xx-small' if sNameTmp[:2] == u'小さ' else u'xx-large'

                            lnbuf = u'%s<span size="%s">%s' % (
                                lnbuf[:tmp.start()], sSizeTmp, lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reLeftBousen.match(tmp.group())
                        if tmp2:
                            #   左に（二重）傍線
                            tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span underline="%s">%s</span>%s%s' % (
                                lnbuf[:tmpStart],
                                'single' if not tmp2.group('type') else 'double',
                                lnbuf[tmpStart:tmpEnd],
                                lnbuf[tmpEnd:tmp.start()],
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reOwari.match(tmp.group()):
                            #   </span>生成用共通処理
                            lnbuf = u'%s</span>%s' % (
                                lnbuf[:tmp.start()], lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reMama.match(tmp.group())
                        if not tmp2:
                            tmp2 = self.reMama2.match(tmp.group())
                        if tmp2:
                            #   ママ注記
                            sNameTmp = tmp2.group(u'name')
                            reTmp = re.compile( ur'%s$' % sNameTmp )
                            lnbuf = u'%s｜%s《%s》%s' % (
                                reTmp.sub( u'', lnbuf[:tmp.start()]),
                                sNameTmp, tmp2.group(u'mama'), lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reRubimama.match(tmp.group()):
                            #   ルビのママ
                            #   直前に出現するルビの末尾に付記する
                            tmpEnd = lnbuf.rfind(u'》',0,tmp.start())
                            if tmpEnd == -1:
                                # 修飾するルビがない場合
                                lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            else:
                                lnbuf = u'%s%s》%s' % (
                                    lnbuf[:tmpEnd], u'(ルビママ)',
                                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reBouten.match(tmp.group())
                        if tmp2:
                            #   傍点・傍線
                            #   rstrip では必要以上に削除する場合があるので
                            #   reのsubで消す
                            tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            reTmp = re.compile(ur'%s$' % tmp2.group('name'))
                            lnbuf = u'%s<aozora bousen="%s">%s</aozora>%s%s' % (
                                lnbuf[:tmpStart],
                                tmp2.group('type') + tmp2.group('type2'),
                                lnbuf[tmpStart:tmpEnd],
                                lnbuf[tmpEnd:tmp.start()],
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reBouten2.match(tmp.group())
                        if tmp2:
                            # ［＃傍点］
                            aozorastack.append(tmp.group())
                            lnbuf = u'%s<aozora bousen="%s">%s' % (
                                lnbuf[:tmp.start()],
                                tmp2.group('type') + tmp2.group('type2'),
                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reBouten2owari.match(tmp.group())
                        if tmp2:
                            # ［＃傍点終わり］
                            if self.reBouten2.match(aozorastack[-1]):
                                aozorastack.pop()
                                lnbuf = lnbuf[:tmp.start()]+u'</aozora>'+lnbuf[tmp.end():]
                            else:
                                # mismatch
                                lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reGyomigikogaki.match(tmp.group())
                        if tmp2:
                            #   行右小書き・上付き小文字、行左小書き・下付き小文字
                            #   pango のタグを流用
                            sNameTmp = tmp2.group(u'name')
                            reTmp = re.compile( ur'%s$' % sNameTmp )
                            lnbuf = u'%s%s%s' % (
                                reTmp.sub( u'', lnbuf[:tmp.start()] ),
                                u'<sup>%s</sup>' % tmp2.group(u'name') if tmp2.group(u'type') == u'行右小書き' or \
                                    tmp2.group('type') == u'上付き小文字' else u'<sub>%s</sub>' % tmp2.group(u'name'),
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reFutoji.match(tmp.group())
                        if tmp2:
                            #   太字
                            #   pango のタグを流用
                            tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span font_desc="Sans">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            lnbuf[tmpStart:tmpEnd],
                                            lnbuf[tmpEnd:tmp.start()],
                                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reSyatai.match(tmp.group())
                        if tmp2:
                            #   斜体
                            #   pango のタグを流用
                            tmpStart,tmpEnd = self.honbunsearch(
                                    lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span style="italic">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            lnbuf[tmpStart:tmpEnd],
                                            lnbuf[tmpEnd:tmp.start()],
                                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reKuntenOkuri.match(tmp.group())
                        if tmp2:
                            #   訓点送り仮名
                            #   pango のタグを流用
                            lnbuf = u'%s<sup>%s</sup>%s' % (
                                lnbuf[:tmp.start()],
                                    tmp2.group(u'name'),
                                        lnbuf[tmp.end():])
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reKaeriten.match(tmp.group())
                        if tmp2:
                            #   返り点
                            #   pango のタグを流用
                            lnbuf = u'%s<sub>%s</sub>%s' % (
                                lnbuf[:tmp.start()],
                                    tmp2.group(u'name'),
                                        lnbuf[tmp.end():])
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        #   見出し
                        #   ここでは正確なページ番号が分からないので、
                        #   見出し出現のフラグだけ立てて、目次作成は後段で行う。
                        #   ここでは複数行見出しはサポートしない
                        matchMidashi = self.reMidashi.match(tmp.group())
                        if matchMidashi:
                            # 1行見出し
                            self.inMidashi = True
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            self.midashi = matchMidashi.group(u'midashi')
                            tmpStart,tmpEnd = self.honbunsearch(
                                    lnbuf[:tmp.start()],self.midashi)
                            lnbuf = u'%s<span face="Sans"%s>%s</span>%s%s' % (
                                lnbuf[:tmpStart],
                                u' size="larger"' if self.sMidashiSize == u'大' else u'',
                                lnbuf[tmpStart:tmpEnd],
                                lnbuf[tmpEnd:tmp.start()],
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue


                        #   上記以外のタグは後続処理に引き渡す
                        tmp = self.reCTRL2.search(lnbuf,tmp.end())

                    if not isRetry and aozorastack:
                        # タグ処理で同一行にて閉じていないものがある場合
                        # 一旦閉じてタグ処理を完結させる。
                        # スタックに捨てタグを積むことに注意
                        aozorastack.append(aozorastack[-1])
                        tmp2 = self.reCTRL3.match(aozorastack[-1])
                        try:
                            sNameTmp = tmp2.group('name')
                        except IndexError:
                            sNameTmp = u''
                        lnbuf += u'［＃%s終わり］' % sNameTmp
                        isRetry = True # フラグで1回だけ実行させる
                        continue

                    # ［＃　で始まるタグの処理 終わり
                    break

                if footerflag:
                    """ フッタにおける年月日を漢数字に置換
                    """
                    ln = u''
                    priortail = 0
                    for tmp in self.reNenGetsuNichi.finditer(lnbuf):
                        ln += lnbuf[priortail:tmp.start()]
                        priortail = tmp.end()
                        for s in tmp.group():
                            try:
                                ln += u'〇一二三四五六七八九'[eval(s)]
                            except:
                                ln += s
                    ln += lnbuf[priortail:]
                    lnbuf = ln

                """ 処理の終わった行を返す
                """
                yield lnbuf + u'\n'

        """ 最初の1ページ目に作品名・著者名を左右中央で表示するため、
            最初に［＃ページの左右中央］を出力している。最初の空行出現時に
            これを閉じている。
            このため、冒頭からまったく空行のないテキストだと、本文処理に遷移
            しないまま処理が終了してしまう。そのためここで出力する。
            なお、副作用として目次は作成されない。
        """
        if not boutoudone:
            yield u'［＃改ページ］'

    def boutencount(self, honbun):
        """ 本文を遡って傍点の打込位置を探し、キャラクタ数を返す
        """
        c = 0
        pos = len(honbun) - 1
        inRubi = False
        inTag = False
        inAtag = False
        while pos >= 0:
            if honbun[pos] == u'｜':
                break
            elif honbun[pos:pos+2] == u'［＃':
                inAtag = False
            elif honbun[pos] == u'］':
                inAtag = True
            elif inAtag:
                pass
            elif honbun[pos] == u'<':
                inTag = False
            elif honbun[pos] == u'>':
                inTag = True
            elif inTag:
                pass
            elif honbun[pos] == u'《':
                inRubi = False
            elif honbun[pos] == u'》':
                inRubi = True
            elif inRubi:
                pass
            else:
                c += 1
            pos -= 1
        return c

    def honbunsearch(self, honbun, name):
        """ 本文を遡って name を検索し、その出現範囲を返す。
            name との比較に際して
                ルビ、<tag></tag>、［］は無視される。
            比較は行末から行頭に向かって行われることに注意。
            見つからなければ start とend に同じ値を返す。
            これを配列添字に使えばヌル文字となる。
        """
        start = -1
        end = -1
        l = len(name)
        pos = len(honbun)
        inRubi = False
        inRubiDetect = False
        inTag = False
        inAtag = False
        while l > 0 and pos > 0:
            pos -= 1
            if honbun[pos:pos+2] == u'［＃':
                inAtag = False
            elif honbun[pos] == u'］':
                inAtag = True
            elif inAtag:
                pass
            elif honbun[pos] == u'<':
                inTag = False
            elif honbun[pos] == u'>':
                inTag = True
            elif inTag:
                pass
            elif honbun[pos] == u'《':
                inRubi = False
            elif honbun[pos] == u'》':
                inRubi = True
                inRubiDetect = True
            elif inRubiDetect and honbun[pos] == u'｜':
                pass
            elif inRubi:
                pass
            else:
                if name[l-1] == honbun[pos]:
                    if end < 0:
                        end = pos
                    start = pos
                    l -= 1
                    if l == 0:
                        # match
                        break
                else:
                    # mismatch の場合はその位置から照合しなおす
                    l = len(name)
                    end = -1
        else:
            # non match
            start = -1
            end = -2

        if end > -1:
            # 検出した文字列の直後にルビが続くなら文字列を拡張して返す
            # ルビが閉じていなければ拡張しない
            try:
                if honbun[end+1] == u'《':
                    pos = honbun.find(u'》', end+1)
                    if pos != -1:
                        end = pos
            except IndexError:
                pass
        return (start,end+1)

    def formater( self, output_file=u'', mokuji_file=u'' ):
        """ フォーマッタ
        """
        if output_file:
            self.destfile = output_file
        if mokuji_file:
            self.mokujifile = mokuji_file

        (self.BookTitle, self.BookAuthor) = self.get_booktitle_sub()
        logging.info( u'****** %s ******' % self.sourcefile )

        with file(self.destfile, 'w') as fpMain, file(self.mokujifile, 'w') as self.mokuji_f:
            dfile = fpMain                      # フォーマット済出力先
            self.pagecenterflag = False         # ページ左右中央用フラグ
            self.countpage = True               # ページ作成フラグ
            self.linecounter = 0                # 出力した行数
            self.pagecounter = 0                # 出力したページ数
            self.pageposition=[] # フォーマット済ファイルにおける各ページの絶対位置
            self.pageposition.append(dfile.tell())  # 1頁目のファイル位置を保存
            self.midashi = u''
            self.inMidashi = False
            self.inFukusuMidashi = False        # 複数行におよぶ見出し
            self.FukusuMidashiOwari = False     # 複数行におよぶ見出しの終わり
            self.loggingflag = False            # デバッグ用フラグ、ページ数用
            self.tagstack = []                  # <tag> のスタック

            currchars = self.charsmax           # 1行の表示文字数
            jizume = 0                          # 字詰指定
            jisage = 0                          # 字下指定
            jisage2 = 0                         # 折り返し字下指定
            jisage3 = 0                         # 折り返し字下げ退避用
            jiage = 0                           # 字上指定
            inIndent = False                    # ブロックインデント
            inJizume = False                    # ブロック字詰
            inJiage = False                     # ブロック字上・地付き
            inKeikakomi = False                 # 罫囲み

            workfilestack = []                  # 作業用一時ファイル

            for lnbuf in self.formater_pass1():
                lnbuf = lnbuf.rstrip('\n')
                yield
                """ 空行の処理
                """
                if not lnbuf: #len(lnbuf) == 0:
                    self.write2file( dfile, '\n' )
                    continue

                """ 制御文字列の処理
                    読み込んだ行に含まれる［＃.*?］を全てチェックする。
                    タグより前方を参照するタグは取り扱わない。
                """
                IndentJitsuki = False
                while True:
                    tmp = self.reCTRL2.search(lnbuf)
                    while tmp:
                        tmp2 = self.reTatenakayoko.match(tmp.group())
                        if tmp2:
                            #   縦中横
                            #   本文を書き換えることに注意
                            tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<aozora tatenakayoko="%s">　</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        matchFig = self.reFig.match(tmp.group())
                        if matchFig:
                            #挿図
                            #    キャンバスの大きさに合わせて画像を縮小する。
                            #    幅　　上限　キャンバスの半分迄
                            #    高さ　上限　キャンバスの高さ迄
                            #
                            #    ページからはみ出るようであれば挿図前に
                            #    改ページする。
                            try:
                                fname = matchFig.group(u'filename')
                                tmpPixBuff = gtk.gdk.pixbuf_new_from_file(
                                    os.path.join(self.get_value(u'aozoradir'),
                                        fname))
                                figheight = tmpPixBuff.get_height()
                                figwidth = tmpPixBuff.get_width()
                                #del tmpPixBuff
                            except gobject.GError:
                                # ファイルI/Oエラー
                                self.loggingflag = True
                                logging.info(
                                    u'画像ファイル %s の読み出しに失敗しました。' % fname )
                                lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                                tmp = self.reCTRL2.search(lnbuf)
                                continue

                            tmpH = float(self.get_value(u'scrnheight')) - \
                                    float(self.get_value(u'bottommargin')) - \
                                            float(self.get_value(u'topmargin')) - \
                                            float(self.get_value(u'fontheight'))*5
                            tmpW = float(self.get_value(u'scrnwidth')) - \
                                    float(self.get_value(u'rightmargin')) - \
                                            float(self.get_value(u'leftmargin'))
                            tmpW //= 2. # 許可される最大幅
                            # 表示領域に収まるような倍率を求める
                            tmpRasio = min((tmpH / figheight),(tmpW / figwidth))
                            if tmpRasio > 1.0:
                                tmpRasio = 1.0

                            # 画像幅をピクセルから行数に換算する
                            figspan = int(round(figwidth*tmpRasio / float(self.linewidth)))

                            if self.linecounter + figspan >= self.pagelines:
                                # 画像がはみ出すようなら改ページする
                                while not self.write2file(dfile, '\n'):
                                    pass
                            while figspan > 0:
                                self.write2file(dfile, '\n')
                                figspan -= 1
                            self.write2file( dfile,
                                u'<aozora img2="%s" width="%s" height="%s" rasio="%0.2f">　</aozora>\n' % (
                                    fname, figwidth, figheight, tmpRasio ))

                            lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ ページの左右中央
                        """
                        if tmp.group() == u'［＃ページの左右中央］':
                            self.pagecenterflag = True
                            # カレントハンドルを退避して、一時ファイルを
                            # 作成して出力先を切り替える。
                            workfilestack.append(dfile)
                            dfile = tempfile.NamedTemporaryFile(mode='w+',delete=True)
                            # 一時ファイル使用中はページカウントしない
                            self.countpage = False

                            lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 改ページ・改訂・改段
                        """
                        if self.reKaipage.match(tmp.group()):
                            if self.pagecenterflag:
                                # ページの左右中央の処理
                                self.pagecenterflag = False
                                if len(workfilestack) == 1:
                                    # 退避してあるハンドルをフォーマット出力先
                                    # と見てページカウントを再開する。
                                    self.countpage = True

                                # 一時ファイルに掃き出された行数を数えて
                                # ページ中央にくるようにパディングする
                                dfile.seek(0)
                                iCenter = self.pagelines
                                for sCenter in dfile:
                                    iCenter -= 1
                                while iCenter > 1:
                                    self.write2file(workfilestack[-1], '\n')
                                    iCenter -= 2
                                # 一時ファイルの内容を退避してあるハンドル先へ
                                # コピーする
                                dfile.seek(0)
                                iCenter = 0
                                for sCenter in dfile:
                                    self.write2file(workfilestack[-1], sCenter)
                                dfile.close()
                                dfile = workfilestack.pop()

                            if self.linecounter != 0:
                                # ページ先頭に出現した場合は改ページしない
                                while not self.write2file(dfile, '\n'):
                                    pass
                            lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 見出し(複数行に及ぶ)
                            ここでは正確なページ番号が分からないので、
                            見出し出現のフラグだけ立てて、目次作成は後段で行う。
                        """
                        matchMidashi = self.reMidashi2.match(tmp.group())
                        if matchMidashi:
                            # <見出し>
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            self.inMidashi = True
                            self.inFukusuMidashi = True
                            self.midashi = u''
                            lnbuf = u'%s<span face="Sans"%s>%s' % (
                                lnbuf[:tmp.start()],
                                u' size="larger"' if self.sMidashiSize == u'大' else u'',
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        matchMidashi = self.reMidashi2owari.match(tmp.group())
                        if matchMidashi:
                            # <見出し終わり>
                            self.FukusuMidashiOwari = True
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            lnbuf = u'%s</span>%s' % (
                                lnbuf[:tmp.start()], lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 字下げ
                        """
                        tmp2 = self.reIndent.match(tmp.group())
                        if tmp2:
                            jisage = self.zentoi(tmp2.group('number'))
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reIndentStart.match(tmp.group())
                        if tmp2:
                            inIndent = True
                            jisage = self.zentoi(tmp2.group('number'))
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reIndentEnd.match(tmp.group()):
                            inIndent = False
                            jisage = 0
                            jisage2 = 0
                            jisage3 = 0
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reKokokaraSage.match(tmp.group())
                        if tmp2:
                            jisage = self.zentoi(tmp2.group('number'))
                            jisage2 = self.zentoi(tmp2.group('number2'))
                            inIndent = True
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = self.reKaigyoTentsuki.match(tmp.group())
                        if tmp2:
                            jisage = 0
                            jisage2 = self.zentoi(tmp2.group('number'))
                            inIndent = True
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 字詰
                        """
                        tmp2 = self.reJizume.match(tmp.group())
                        if tmp2:
                            jizume = self.zentoi(tmp2.group('number'))
                            inJizume = True
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reJizumeowari.match(tmp.group()):
                            inJizume = False
                            jizume = 0
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 字上
                        """
                        if self.reJiage.match(tmp.group()):
                            """ 行途中で出現する字上げは後段へそのまま送る
                            """
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        tmp2 = self.reKokokaraJiage.match(tmp.group())
                        if tmp2:
                            inJiage = True
                            jiage = self.zentoi(tmp2.group('number'))
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reJiageowari.match(tmp.group()):
                            inJiage = False
                            jiage = 0
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 地付き
                        """
                        if self.reKokokaraJitsuki.match(tmp.group()):
                            inJiage = True
                            jiage = 0
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        if self.reJitsukiowari.match(tmp.group()):
                            inJiage = False
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 罫囲み
                            天と地に罫線描画用に1文字の空きが必要に
                            なるのでインデント処理を勘案してここで
                            準備する。
                        """
                        if self.reKeikakomi.match(tmp.group()):
                            inKeikakomi = True
                            # カレントハンドルを退避して、一時ファイルを
                            # 作成して出力先を切り替える。
                            workfilestack.append(dfile)
                            dfile = tempfile.NamedTemporaryFile(mode='w+',delete=True)
                            # 一時ファイル使用中はページカウントしない
                            self.countpage = False
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        if self.reKeikakomiowari.match(tmp.group()):
                            inKeikakomi = False
                            if len(workfilestack) == 1:
                                # 退避してあるハンドルをフォーマット出力先と
                                # 見てページカウントを再開
                                self.countpage = True

                            # 一時ファイルに掃き出された行数を数える
                            dfile.seek(0)
                            iCenter = 0
                            for sCenter in dfile:
                                iCenter += 1
                            if iCenter < self.pagelines:
                                # 罫囲みが次ページへまたがる場合は改ページする。
                                # 但し、１ページを越える場合は無視する。
                                if self.linecounter + iCenter >= self.pagelines:
                                    while not self.write2file(workfilestack[-1], '\n' ):
                                        pass

                            # 一時ファイルからコピー
                            dfile.seek(0)
                            iCenter = 0
                            for sCenter in dfile:
                                self.write2file(workfilestack[-1], sCenter)
                            dfile.close()
                            dfile = workfilestack.pop()
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        """ 未定義タグ
                            青空形式を外して本文に残す
                        """
                        if tmp:
                            lnbuf = u'%s%s%s' % (
                                lnbuf[:tmp.start()],
                                tmp.group().lstrip(u'［＃').rstrip(u'］'),
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)

                        # end of loop

                    break

                """ ルビの処理
                    文字種が変わる毎にルビ掛かり始めとみなして、anchorを
                    セットする。
                """
                retline = u''
                inRubi = False
                inTag = False
                pos = 0
                anchor = 0
                isSPanchor = False
                tp = u'...'
                for s in lnbuf:
                    # タグをスキップ
                    if s == u'>':
                        inTag = False
                    elif s == u'<':
                        inTag = True
                    elif inTag:
                        pass
                    elif s == u'｜':
                        isSPanchor = True
                        retline += lnbuf[anchor:pos]
                        anchor = pos + 1
                    elif s == u'《':
                        inRubi = True
                        rubiTop = pos
                    elif s == u'》':
                        inRubi = False
                        isSPanchor = False
                        retline += u'<aozora rubi="%s" length="%s">%s</aozora>' % (
                            lnbuf[rubiTop+1:pos],
                            self.boutencount(lnbuf[anchor:rubiTop]),#本文側長さ
                            lnbuf[anchor:rubiTop] )
                        anchor = pos + 1
                    elif inRubi:
                        pass
                    else:
                        # 文字種類の違いを検出してルビ掛かり始め位置を得る
                        # 但し、 ｜　で示された掛かり始めが未使用であれば
                        # それが使われる迄ひっぱる
                        if not isSPanchor:
                            tplast = tp
                            tp = unicodedata.name(s, u'...').split()[0]
                            # 非漢字でも漢字扱いとする文字
                            # http://www.aozora.gr.jp/KOSAKU/MANUAL_2.html#ruby
                            if tp != u'CJK':
                                if s in u'仝〆〇ヶ〻々':
                                    tp = u'CJK'
                            if tplast != tp:
                                # 新しいルビ掛かり始め位置
                                retline += lnbuf[anchor:pos]
                                anchor = pos
                    pos += 1

                retline += lnbuf[anchor:pos]
                lnbuf = retline

                """ インデント一式 (字下げ、字詰、字上げ、地付き)
                            |<---------- self.chars ------------>|
                          行|<--------- self.charsmax --------->||行
                            |<------ currchars ----->           ||
                            |<--jisage-->                       ||
                            |  <--jisage2-->                    ||
                          頭|            <--jizume-->           ||末
                            |                        <--jiage-->||
                """
                jisage3 = jisage
                while lnbuf != '':
                    #   1行の表示桁数の調整
                    #   優先順位
                    #       jiage > jisage > jizume
                    currchars = self.charsmax - jiage
                    if inJiage:
                        # ブロック地付き及びブロック字上げ
                        # 字下げはキャンセルされる
                        lenN = self.linelengthcount(lnbuf)
                        if jizume > 0 and lenN > jizume:
                            lenN = jizume
                        if lenN < currchars:
                            sIndent = u'　' * (currchars - lenN)
                            lnbuf = sIndent + lnbuf
                    else:
                        # インデントの挿入
                        if jisage + jizume > currchars:
                            currjisage = 1 if currchars - jisage < 0 else jisage
                        else:
                            if jizume > 0:
                                currchars = jisage + jizume
                            currjisage = jisage

                        if currjisage > 0:
                            sIndent = u'　' * currjisage
                            lnbuf = sIndent + lnbuf

                        # 地付きあるいは字上げ(同一行中を含む)
                        # 出現した場合、字詰はキャンセルされる
                        #  name2 [tag] name
                        tmp2 = self.reJiage.match(lnbuf)
                        if tmp2:
                            sP = u'' if not tmp2.group('name2') else tmp2.group('name2')
                            lenP = self.linelengthcount(sP)
                            sN = u'' if not tmp2.group('name') else tmp2.group('name')
                            lenN = self.linelengthcount(sN)
                            try:
                                # 字上げ n
                                n = self.zentoi(tmp2.group('number'))
                            except TypeError, IndexError:
                                # 地付き
                                n = 0
                            currchars = self.charsmax - n
                            if lenP >= currchars:
                                # 地付きする文字列の前に１行以上の長さが残って
                                # いる場合はそのまま分割処理に送る。
                                pass
                            elif lenN >= currchars:
                                # 地付きする文字列が1行の長さを越えている場合、
                                # 通常の行として終わる。
                                # 地付きはこれで良いが、字上げの場合はタグの
                                # 次行繰越処理を追加したい
                                #（ここで処理できないのでlinesplitで）
                                lnbuf = sP + sN
                                currchars = self.charsmax
                            elif lenP + lenN <= currchars:
                                # 表示が1行分に収まる場合は処理する。
                                sPad = u'　' * (currchars -lenP -lenN)
                                lnbuf = sP + sPad + sN
                                # ルビ表示 地付きタグ分を取り除くこと
                            else:
                                # 収まらない場合、空白で次行にはみ出させて分割
                                # 処理に送る。
                                sPad = u'　' * (currchars - lenP)
                                lnbuf = sP + sPad + lnbuf[tmp2.start('tag'):]

                    #   画面上の1行で収まらなければ分割して次行を得る
                    self.ls, lnbuf = self.linesplit(lnbuf, currchars)

                    """ 行をバッファ(中間ファイル)へ掃き出す
                    """
                    self.write2file(dfile, "%s\n" % self.ls)

                    #   折り返しインデント
                    if lnbuf != '':
                        if jisage2 != 0:
                            if jisage2 != jisage:
                                jisage3 = jisage # 初段字下げ幅退避
                                jisage = jisage2
                    else:
                        jisage = jisage3 # 初段回復

                    #   単発か否か
                    if not inIndent:
                        jisage = 0
                    if not inJizume:
                        jizume = 0
                    if not inJiage:
                        jiage = 0

    def linesplit(self, sline, smax=0.0):
        """ 文字列を分割する
            禁則処理、行末におけるルビ及び挿入画像の分ち書きの調整も行う。
            sline   : 本文
            smax    : 1行における文字数（全角文字を1文字とした換算数）
        """
        tagname = u''
        lcc = 0.0           # 全角１、半角0.5で長さを積算
        honbun = u''        # 本文（カレント行）
        honbun2 = u''       # 本文（分割時の次行）
        inTag = False       # <tag>処理のフラグ
        inSplit = False     # 行分割処理のフラグ

        fontsizename = u'normal'

        """ 前回の呼び出しで引き継がれたタグがあれば付け足す。
        """
        while self.tagstack != []:
            # 行頭からの空白（字下げ等）を飛ばす
            pos = 0
            endpos = len(sline)
            while pos < endpos and sline[pos] == u'　':
                pos += 1
            sline = sline[:pos] + self.tagstack.pop() + sline[pos:]

        for lsc in sline:
            if inSplit:
                # 本文の分割
                honbun2 += lsc
                continue

            if smax:
                if round(lcc) >= smax:
                    inSplit = True
                    honbun2 += lsc
                    continue

            honbun += lsc
            if lsc == u'>':
                # tagスタックの操作
                tagname += lsc
                if tagname[:2] == u'</':
                    # </tag>の出現とみなしてスタックから取り除く
                    # ペアマッチの処理は行わない
                    try:
                        tmp = self.reFontsizefactor.search(self.tagstack.pop())
                        if tmp:
                            if tmp.group('name') in self.fontsizefactor:
                                fontsizename = u'normal' # 文字サイズの復旧
                    except IndexError:
                        pass
                else:
                    tmp = self.reFontsizefactor.search(tagname)
                    if tmp:
                        if tmp.group('name') in self.fontsizefactor:
                            fontsizename = tmp.group('name') # 文字サイズ変更
                    self.tagstack.append(tagname)
                    tagname = u''
                inTag = False
            elif lsc == u'<':
                inTag = True
                tagname = lsc
            elif inTag:
                tagname += lsc
            else:
                # 画面上における全長を計算
                lcc += self.charwidth(lsc) * self.fontsizefactor[fontsizename]

        """ 行末禁則処理
            次行先頭へ追い出す
            禁則文字が続く場合は全て追い出す
        """
        while honbun[-1] in self.kinsoku2:
            honbun2 = honbun[-1] + honbun2
            honbun = honbun[:-1] + u'　'

        """ 行頭禁則処理 ver 2
            前行末にぶら下げる。
            但し2文字(以上)続く場合は括弧類ならさらにぶら下げ、
            それ以外は前行の末尾をチェックし、非禁則文字なら
            行頭へ追い込む。
            例）シ　(改行) ャーロック・ホームズ ->
                (改行)シャーロック・ホームズ
            前行の閉じタグが行頭に回り込んでいる場合は、前行末へ
            ぶら下げる
        """
        if honbun2: # len(honbun2)>0 よりわずかに速い
            pos = 0
            if honbun2[0:2] == u'</':
                # 閉じタグなら前行へぶら下げる
                pos = honbun2.find(u'>',pos+2)
                #pos += 2
                #while honbun2[pos] != u'>':
                #    pos += 1
                pos += 1
                self.tagstack.pop()
                honbun += honbun2[:pos]
                honbun2 = honbun2[pos:]
                pos = 0

            try:
                while honbun2[pos] == u'<':
                    # タグをスキップ
                    pos = honbun2.find(u'>',pos+1)
                    #pos += 1
                    #while honbun2[pos] != u'>':
                    #    pos += 1
                    pos += 1

                if honbun2[pos] in self.kinsoku:
                    honbun += honbun2[pos]
                    honbun2 = honbun2[:pos]+honbun2[pos+1:]

                    if honbun2[pos:]:
                        # ２文字目チェック
                        while honbun2[pos] == u'<':
                            # タグをスキップする
                            pos = honbun2.find(u'>',pos+1)
                            #pos += 1
                            #while honbun2[pos] != u'>':
                            #    pos += 1
                            pos += 1
                        if honbun2[pos] in self.kinsoku:
                            if honbun2[pos] in self.kinsoku4:
                                honbun += honbun2[pos]
                                honbun2 = honbun2[:pos]+honbun2[pos+1:]
                            else:
                                # 括弧類以外（もっぱら人名対策）
                                if not (honbun[-2] in self.kinsoku):
                                    honbun2 = honbun[-2:] + honbun2
                                    honbun = honbun[:-2]
                                    # 前行末を変更したので行末禁則処理を
                                    # 再度実施
                                    while honbun[-1] in self.kinsoku2:
                                        honbun2 = honbun[-1] + honbun2
                                        honbun = honbun[:-1] + u'　'
                                    honbun += u'　　'
            except IndexError:
                pass

        """ tag の処理（１）
            行末のタグの分かち書き対策
        """
        substack = []
        honbunpos = 0 if honbun[-1] == u'>' else honbun.rfind(u'>') + 1
        honbuntail = honbun[honbunpos:]
        while self.tagstack:
            chktag = self.tagstack.pop()
            # 本文側がタグだけで終わっている場合はタグを閉じるのみ
            if honbunpos > 0:
                if chktag.find(u'<aozora ') != -1:
                    tagname = chktag.split(u'=')[0].split()[1]
                    hlen = len(honbuntail) # 本文側掛かり部分の長さ
                    tagpos = honbun.rfind(chktag) # 本文中のタグ位置
                    if tagpos == -1:
                        # 本文側にタグが無い（エラー）
                        print u'not found ',chktag

                    elif tagname == u'rubi' or tagname == u'leftrubi':
                        # ルビの分かち書きの有無
                        rubi = chktag.split()[1].split(u'=')[1].strip(u'">')
                        rubiafter = u''
                        hlenorigin = int(chktag.split()[2].split(u'=')[1].strip(u'">'))
                        # ルビを分割、本文の長さを勘案して分割
                        rubilen = int(round(hlen * float(len(rubi)) /
                                                        float(hlenorigin)) )
                        rubiafter = rubi[rubilen:]
                        rubi = rubi[:rubilen]
                        # ルビを分割するなら現在行のルビを修正し、残りを次行へ持ち越し
                        if rubiafter:
                            honbun = u'%s<aozora %s="%s" length="%d">%s' % (
                                        honbun[:tagpos],
                                        tagname, rubi, hlen,
                                        honbun[tagpos+len(chktag):] )
                            # 次行の先頭に字下げ用の空白などが連なる場合は、
                            # 飛ばしてルビタグを打つ
                            pos = 0
                            while honbun2[pos] == u'　':
                                pos += 1
                            honbun2 = u'%s<aozora %s="%s" length="%d">%s' % (
                                        honbun2[:pos],
                                        tagname, rubiafter, hlenorigin - hlen,
                                        honbun2[pos:] )
                        honbun += u'</aozora>'
                        continue

                    elif tagname == u'img':
                        # 埋め込み画像 <aozora img="" width="" height="">
                        # 行末に充分な表示領域が見込めれば次行へ引き継がない。
                        # でなければ、行末側を削除して次行行頭のみ表示する
                        h = int(chktag.split()[3].split(u'=')[1].strip('">'))
                        if hlen * int(self.get_value('fontheight')) < h:
                            # 行末の画像表示域が見込めなければ次行行頭へ移動
                            pos = 0
                            while honbun2[pos] == u'　':
                                pos += 1
                            sPad = u'＃' * int(math.ceil(
                                    float(h)/float(self.get_value('fontheight'))))
                            endpos = len(honbun2)
                            pos2 = pos
                            while pos2 < endpos and honbun2[pos2] == u'＃':
                                pos2 += 1
                            honbun2 = u'%s%s%s</aozora>%s' % (
                                    honbun2[:pos], chktag, sPad, honbun2[pos2:] )
                            # 本文側のタグを削除
                            pos = tagpos
                            pos += len(chktag)
                            endpos = len(honbun)
                            while pos < endpos and honbun[pos] == u'＃':
                                pos += 1
                            honbun = honbun[:tagpos] + honbun[pos:]
                        continue
                    else:
                        pass

            # 分かち書き以外のタグは単純に一旦閉じる
            honbun += u'</%s>' % chktag.split()[0].rstrip(u'>').lstrip(u'<')
            substack.append(chktag) # 退避


        """ tag の処理（２）
            スタックに積み直す
        """
        while substack:
            self.tagstack.append(substack.pop())

        return (honbun, honbun2)

    def write2file(self, fd, s):
        """ formater 下請け
            1行出力後、改ページしたらその位置を記録して True を返す。
            目次作成もここで行う。
            出力時の正確なページ数と行数が分かるのはここだけ。
        """
        rv = False
        if self.countpage:
            if self.inMidashi:
                # 見出し書式
                if self.sMidashiSize == u'大':
                    sMokujiForm = u'%-s  % 4d\n'
                elif self.sMidashiSize == u'中':
                    sMokujiForm = u'  %-s  % 4d\n'
                elif self.sMidashiSize == u'小':
                    sMokujiForm = u'    %-s  % 4d\n'
                # 目次作成
                if self.inFukusuMidashi:
                    self.midashi += s.rstrip('\n')

                    if self.FukusuMidashiOwari:
                        # 複数行に及ぶ見出しが終わった場合
                        self.FukusuMidashiOwari = False
                        self.inFukusuMidashi = False
                        self.mokuji_f.write( sMokujiForm % (
                            self.reTagRemove.sub(u'',
                                self.midashi.lstrip(u' 　').rstrip('\n')),
                            self.pagecounter +1))
                        self.inMidashi = False
                else:
                    self.mokuji_f.write( sMokujiForm % (
                        self.reTagRemove.sub(u'',
                            self.midashi.lstrip(u' 　').rstrip('\n')),
                        self.pagecounter +1))
                    self.inMidashi = False

        if self.loggingflag:
            logging.debug( u'　位置：%dページ、%d行目' % (
                                    self.pagecounter+1,self.linecounter+1 ))
            self.loggingflag = False

        fd.write(s)         # 本文
        if self.countpage:
            self.linecounter += 1
            if self.linecounter >= self.pagelines:
                # 1頁出力し終えたらその位置を記録する
                self.pagecounter += 1
                self.pageposition.append(fd.tell())
                self.linecounter = 0
                fd.flush()
                rv = True
        return rv


@contextmanager
def cairocontext(surface):
    try:
        context = cairo.Context(surface)
        yield context
    finally:
        del context

@contextmanager
def pangocairocontext(cairoctx):
    try:
        pangoctx = pangocairo.CairoContext(cairoctx)
        yield pangoctx
    finally:
        del pangoctx

class expango(HTMLParser, AozoraScale, ReaderSetting):
     # 右側傍点及び傍線
    dicBouten = {
        u'白ゴマ傍点':u'﹆',
        u'丸傍点':u'●',      u'白丸傍点':u'○',    u'黒三角傍点':u'▲',
        u'白三角傍点':u'△',  u'二重丸傍点':u'◎',  u'蛇の目傍点':u'◉',
        u'ばつ傍点':u'×',    u'傍点':u'﹅',
        u'波線':u'〜〜' }

    def __init__(self, canvas):
        HTMLParser.__init__(self)
        AozoraScale.__init__(self)
        ReaderSetting.__init__(self)
        self.tagstack = []
        self.attrstack = []
        self.sf = canvas
        self.xposoffsetold = 0
        self.oldlength = 0


    def settext(self, s, xpos, ypos):
        self.source = s
        self.xpos = xpos
        self.ypos = ypos

        self.feed('<span font_desc="%s %s">%s</span>' % (
                        self.fontname, self.fontsize, s))
    def convcolor(self, s):
        """ カラーコードを16進文字列からRGB(0..1)に変換して返す
        """
        p = (len(s)-1)/3
        return(
            float(eval(u'0x'+s[1:1+p])/65535.0),
            float(eval(u'0x'+s[1+p:1+p+p])/65535.0),
            float(eval(u'0x'+s[1+p+p:1+p+p+p])/65535.0) )

    def setcolour(self, fore, back):
        """ 描画色・背景色を得る
        """
        (self.foreR,self.foreG,self.foreB) = self.convcolor(fore)
        (self.backR,self.backG,self.backB) = self.convcolor(back)

    def setfont(self, font, size, rubisize):
        """ フォント
        """
        self.fontname = font
        self.fontsize = size
        self.fontrubisize = rubisize
        self.fontheight = int(round(float(size)*(16./12.)))
        self.fontwidth = self.fontheight # 暫定

        self.font = pango.FontDescription(u'%s %s' % (font,size))
        self.font_rubi = pango.FontDescription(u'%s %s' % (font,rubisize))

    def getforegroundcolour(self):
        return (self.foreR,self.foreG,self.foreB)

    def getbackgroundcolour(self):
        return (self.backR,self.backG,self.backB)

    def handle_starttag(self, tag, attr):
        self.tagstack.append(tag)
        self.attrstack.append(attr)

    def handle_endtag(self, tag):
        if self.tagstack != []:
            if self.tagstack[-1] == tag:
                self.tagstack.pop()
                self.attrstack.pop()

    def handle_data(self, data):
        """ 挟まれたテキスト部分が得られる
        """
        vector = 0
        fontspan = 1
        xposoffset = 0
        dicArg = {}
        sTmp = data
        try:
            # タグスタックに積まれている書式指定を全て付す
            pos = -1
            while True:
                s = self.tagstack[pos]
                if s == u'aozora':
                    # 拡張したタグは必ず引数をとる
                    for i in self.attrstack[pos]:
                        dicArg[i[0]] = i[1]
                    # 一部のタグは本文を引数で置換する
                    if u'tatenakayoko' in dicArg:
                        sTmp = dicArg[u'tatenakayoko']
                    pos -= 1
                    continue
                elif s == u'sup':
                    #<sup>単独ではベースラインがリセットされる為、外部で指定する
                    xposoffset = int(math.ceil(self.fontwidth / 3.))
                    fontspan = self.fontmagnification(u'<%s>' % s)
                elif s == u'sub':
                    #<sub>単独ではベースラインがリセットされる為、外部で指定する
                    xposoffset = -int(math.ceil(self.fontwidth / 3.))
                    fontspan = self.fontmagnification(u'<%s>' % s)
                else:
                    # 引数復元
                    if self.attrstack[pos] != []:
                        for i in self.attrstack[pos]:
                            s += u' %s="%s"' % (i[0],i[1])

                sTmp = '<%s>%s</%s>'% (s,sTmp,self.tagstack[pos])
                pos -= 1
        except IndexError:
            pass

        # 表示
        with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
            ctx.set_source_rgb(self.foreR,self.foreG,self.foreB) # 描画色
            layout = pangoctx.create_layout()
            layout.set_font_description(self.font)
            honbunxpos = 0
            if u'img' in dicArg:
                sTmp = sTmp.replace(u'＃',u'　')
                layout.set_markup(sTmp)
                # 段落埋め込みの画像
                # 描画位置の調整
                length, y = layout.get_pixel_size() #幅と高さを返す(実際のピクセルサイズ)
                imgtmpx = int(math.ceil(float(dicArg[u'width'])/2.))
                imgtmpy = int(math.ceil((length - float(dicArg[u'height']))/2.))
                pangoctx.translate(self.xpos + xposoffset - imgtmpx,
                                        self.ypos+imgtmpy)
                pangoctx.rotate(0)
                img = cairo.ImageSurface.create_from_png(
                        os.path.join(self.get_value(u'aozoradir'),
                        dicArg[u'img']))
                ctx.set_source_surface(img,0,0) # 直前のtranslateが有効
                ctx.paint()

            elif u'img2' in dicArg:
                # 画像
                pangoctx.translate(self.xpos + xposoffset,
                    self.ypos + int(self.get_value(u'fontheight'))*2)
                pangoctx.rotate(0)
                img = cairo.ImageSurface.create_from_png(
                            os.path.join(self.get_value(u'aozoradir'),
                            dicArg[u'img2']))

                ctx.scale(float(dicArg[u'rasio']),float(dicArg[u'rasio']))
                # scaleで画像を縮小すると座標系全てが影響を受ける為、
                # translate で指定したものを活かす
                sp = cairo.SurfacePattern(self.sf)
                sp.set_filter( cairo.FILTER_BEST )#FILTER_GAUSSIAN )#FILTER_NEAREST)
                ctx.set_source_surface(img,0,0)
                ctx.paint()
                length = int(float(self.get_value(u'fontheight'))*2 +
                    math.ceil(float(dicArg[u'height'])*float(dicArg[u'rasio'])))
                self.oldlength = length

            elif u'caption' in dicArg:
                # キャプション
                # 直前に画像がなかったり改ページされている場合は失敗する
                sTmp = u'<span size="%s">%s</span>' % (dicArg[u'size'], dicArg[u'caption'])
                layout.set_markup(sTmp)
                length, y = layout.get_pixel_size() #x,yを入れ替えることに注意
                pangoctx.translate(self.xpos + int(self.get_value(u'linewidth')),
                                            self.ypos + y/2. + self.oldlength)
                pangoctx.rotate(0)
                pc = layout.get_context() # Pango を得る
                pc.set_base_gravity('auto')
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc
                length = y

            elif u'tatenakayoko' in dicArg:
                # 縦中横 直前の表示位置を元にセンタリングする
                layout.set_markup(sTmp)
                y, length = layout.get_pixel_size() #x,yを入れ替えることに注意
                pangoctx.translate(self.xpos + xposoffset - int(math.ceil(y/2.)),
                                                    self.ypos)
                pangoctx.rotate(0)
                pc = layout.get_context() # Pango を得る
                pc.set_base_gravity('auto')
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc

            else:
                layout.set_markup(sTmp)
                length, span = layout.get_pixel_size() #幅と高さを返す(実際のピクセルサイズ)
                honbunxpos = int(math.ceil(span/2.))
                pangoctx.translate(self.xpos + xposoffset + honbunxpos,
                                self.ypos)  # 描画位置
                pangoctx.rotate(3.1415/2.) # 90度右回転、即ち左->右を上->下へ
                pc = layout.get_context() # Pango を得る
                pc.set_base_gravity('auto')
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc

            del layout

        if u'rubi' in dicArg:
            with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                # ルビ
                layout = pangoctx.create_layout()
                layout.set_font_description(self.font_rubi)
                layout.set_markup(dicArg[u'rubi'])
                rubilength,rubispan = layout.get_pixel_size()
                # 表示位置センタリング
                y = self.ypos + int((length-rubilength) // 2.)
                if y < 0:
                    y = 0
                pangoctx.translate(self.xpos + honbunxpos + rubispan,y)
                pangoctx.rotate(3.1415/2.) # 90度右回転、即ち左->右を上->下へ
                pc = layout.get_context() # Pango を得る
                pc.set_base_gravity('auto')
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc
                del layout

        if u'bousen' in dicArg:
            # 傍線 但し波線を実装していません
            with cairocontext(self.sf) as ctx:
                ctx.set_antialias(cairo.ANTIALIAS_NONE)
                if dicArg[u'bousen'][-1] == u'線':
                    ctx.new_path()
                    ctx.set_line_width(1)
                    if dicArg[u'bousen'] == u'破線':
                        ctx.set_dash((3.5,3.5,3.5,3.5))
                    elif dicArg[u'bousen'] == u'鎖線':
                        ctx.set_dash((1.5,1.5,1.5,1.5))
                    elif dicArg[u'bousen'] == u'二重傍線':
                        ctx.move_to(self.xpos + honbunxpos +2, self.ypos)
                        ctx.rel_line_to(0, length)
                        ctx.stroke()
                    elif dicArg[u'bousen'] == u'波線':
                        pass
                    ctx.move_to(self.xpos + honbunxpos, self.ypos)
                    ctx.rel_line_to(0, length)
                    ctx.stroke()
                else:
                    # 傍点 但し本文をトレースしない
                    sB = u''
                    for s in data:
                        sB += self.dicBouten[dicArg[u'bousen']]
                    with pangocairocontext(ctx) as pangoctx:
                        layout = pangoctx.create_layout()
                        layout.set_font_description(self.font)
                        layout.set_text(sB)
                        pangoctx.translate(
                            self.xpos + honbunxpos + int(round(honbunxpos*1.4)),
                            self.ypos)
                        pangoctx.rotate(3.1515/2.)
                        pc = layout.get_context()
                        pc.set_base_gravity('auto')
                        pangoctx.update_layout(layout)
                        pangoctx.show_layout(layout)
                        del pc
                        del layout

        if u'leftrubi' in dicArg:
            with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                # 左ルビ
                layout = pangoctx.create_layout()
                layout.set_font_description(self.font_rubi)
                layout.set_markup(dicArg[u'leftrubi'])
                rubilength,rubispan = layout.get_pixel_size()
                # 表示位置センタリング
                y = self.ypos + int((length-rubilength) // 2.)
                if y < 0:
                    y = 0
                pangoctx.translate(self.xpos - honbunxpos ,y)
                pangoctx.rotate(3.1415/2.) # 90度右回転、即ち左->右を上->下へ
                pc = layout.get_context() # Pango を得る
                pc.set_base_gravity('auto')
                pangoctx.update_layout(layout)
                pangoctx.show_layout(layout)
                del pc
                del layout

        # ypos 更新
        self.ypos += length


class CairoCanvas(Aozora):
    """ cairo / pangocairo を使って文面を縦書きする
    """
    def __init__(self):
        Aozora.__init__(self)
        self.canvas_width       = int(self.get_value( u'scrnwidth' ))
        self.canvas_height      = int(self.get_value( u'scrnheight'))
        self.canvas_topmargin   = int(self.get_value( u'topmargin'))
        self.canvas_rightmargin = int(self.get_value( u'rightmargin' ))
        self.canvas_fontsize    = float(self.get_value( u'fontsize' ))
        self.canvas_rubisize    = float(self.get_value( u'rubifontsize' ))
        self.canvas_linewidth   = int(self.get_value(u'linewidth'))
        self.canvas_rubispan    = int(self.get_value(u'rubiwidth'))
        self.canvas_fontname    = self.get_value(u'fontname')

        self.BEDEBUG = False #True
    def writepage(self, pagenum, buffname=u''):
        """ 指定したページを描画する
        """
        if not buffname:
            buffname = self.get_outputname()

        inKeikakomi = False # 罫囲み
        maxchars = 0            # 囲み内に出現する文字列の最大長
        offset_y = 0            # 文字列の書き出し位置
        tmpwidth = 0
        tmpheight = 0
        fontheight = int(self.get_value(u'fontheight'))
        fontwidth = fontheight # 暫定

        xpos = self.canvas_width - self.canvas_rightmargin - int(math.ceil(self.canvas_linewidth/2.))
        KeikakomiXendpos = xpos
        KeikakomiYendpos = self.canvas_height - self.canvas_topmargin - int(self.get_value(u'bottommargin'))

        # キャンバスの確保
        self.sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                        self.canvas_width, self.canvas_height)
        # 文字列表示
        self.drawstring = expango(self.sf)
        self.drawstring.setcolour(self.get_value(u'fontcolor'),
                                    self.get_value(u'backcolor'))
        self.drawstring.setfont(self.get_value( u'fontname' ),
                                        self.get_value(u'fontsize'),
                                        self.get_value(u'rubifontsize') )
        """ 画面クリア
        """
        with cairocontext(self.sf) as ctx:
            ctx.rectangle(0, 0, self.canvas_width, self.canvas_height)
            r,g,b = self.drawstring.getbackgroundcolour()
            ctx.set_source_rgb(r, g, b)
            ctx.fill()

            if self.BEDEBUG:
            # マージンに境界線を引く（デバッグ用）
                r,g,b = self.drawstring.getforegroundcolour()
                ctx.set_source_rgb(r, g, b)
                ctx.set_antialias(cairo.ANTIALIAS_NONE)
                ctx.new_path()
                ctx.set_line_width(1)
                ctx.set_dash((3.5,3.5,3.5,3.5))
                tmpwidth = self.canvas_width - int(self.get_value('leftmargin')) - self.canvas_rightmargin
                tmpheight = self.canvas_height - self.canvas_rightmargin - int(self.get_value('bottommargin'))
                ctx.move_to(self.canvas_width - self.canvas_rightmargin, self.canvas_topmargin)
                ctx.rel_line_to(0, tmpheight)
                ctx.rel_line_to(-tmpwidth, 0)
                ctx.rel_line_to(0, -tmpheight)
                ctx.rel_line_to(tmpwidth, 0)
                ctx.stroke()

                tmpwidth = 0
                tmpheight = 0

        if self.BEDEBUG:
            # 行番号の表示（デバッグ用）
            tmpxpos = self.canvas_width - self.canvas_rightmargin - int(math.ceil(self.canvas_linewidth/2.))
            n = 1
            while tmpxpos > 0:
                with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                    sTmp = u'<span size="xx-small">%d</span>' % n
                    layout = pangoctx.create_layout()
                    layout.set_markup(sTmp)
                    length,y = layout.get_pixel_size()
                    pangoctx.translate(tmpxpos - int(math.ceil(length/2.)),0)
                    pangoctx.rotate(0)
                    pc = layout.get_context() # Pango を得る
                    pc.set_base_gravity('auto')
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del pc
                    tmpxpos -= self.canvas_linewidth
                    n += 1

            tmpxpos = self.canvas_topmargin
            n = 1
            while tmpxpos < self.canvas_height:
                with cairocontext(self.sf) as ctx, pangocairocontext(ctx) as pangoctx:
                    sTmp = u'<span size="xx-small">%d</span>' % n
                    layout = pangoctx.create_layout()
                    layout.set_markup(sTmp)
                    length,y = layout.get_pixel_size()
                    pangoctx.translate(0, tmpxpos )
                    pangoctx.rotate(0)
                    pc = layout.get_context() # Pango を得る
                    pc.set_base_gravity('auto')
                    pangoctx.update_layout(layout)
                    pangoctx.show_layout(layout)
                    del pc
                    tmpxpos += int(self.get_value('fontheight'))
                    n += 1


        with codecs.open(buffname, 'r', 'UTF-8') as f0:
            try:
                f0.seek(self.pageposition[pagenum])
            except IndexError:
                logging.error( u'存在しないページ(%d)を指定しました。' % pagenum )
            else:
                for i in xrange(self.pagelines):
                    s0 = f0.readline().rstrip('\n')

                    tmpxpos = s0.find(u'［＃ここから罫囲み］')
                    if tmpxpos != -1:
                        # 罫囲み開始
                        inKeikakomi = True
                        offset_y = self.chars
                        maxchars = 0
                        s0 = s0[:tmpxpos] + s0[tmpxpos+len(u'［＃ここから罫囲み］'):]
                        KeikakomiXendpos = xpos# + int(round(self.canvas_linewidth/2.))

                    tmpxpos = s0.find(u'［＃ここで罫囲み終わり］')
                    if tmpxpos != -1:
                        # 罫囲み終わり
                        inKeikakomi = False
                        s0 = s0[:tmpxpos] + s0[tmpxpos+len(u'［＃ここで罫囲み終わり］'):]
                        if offset_y > 0:
                            offset_y -= 1
                        maxchars -= offset_y
                        if maxchars < self.chars:
                            maxchars += 1
                        #tmpwidth = KeikakomiXendpos - xpos - (self.canvas_linewidth/2)
                        tmpwidth = KeikakomiXendpos - xpos
                        with cairocontext(self.sf) as ctx:
                            ctx.set_antialias(cairo.ANTIALIAS_NONE)
                            ctx.new_path()
                            ctx.set_line_width(1)
                            #ctx.move_to(xpos - (self.canvas_linewidth/2),
                            ctx.move_to(xpos,
                                    self.canvas_topmargin + offset_y * fontheight)
                            ctx.rel_line_to(tmpwidth,0)
                            ctx.rel_line_to(0, maxchars * fontheight)
                            ctx.rel_line_to(-tmpwidth,0)
                            ctx.close_path()
                            ctx.stroke()

                    if inKeikakomi:
                        # 罫囲み時の最大高さを得る
                        tmpheight = self.linelengthcount(s0)
                        if  tmpheight > maxchars:
                            maxchars = tmpheight
                        # 文字列の最低書き出し位置を求める
                        sTmp = s0.strip()
                        if sTmp:
                            tmpheight = s0.find(sTmp)
                            if tmpheight < offset_y:
                                offset_y = tmpheight

                    self.drawstring.settext(s0, xpos, self.canvas_topmargin)
                    xpos -= self.canvas_linewidth

        self.sf.write_to_png(os.path.join(self.get_value(u'workingdir'),
                                                            'thisistest.png'))
        self.sf.finish()





