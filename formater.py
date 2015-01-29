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

from __future__ import with_statement

from jis3 import gaiji
from readersub import ReaderSetting, AozoraDialog
from aozoracard import AuthorList

import sys
import codecs
import re
import os.path
import datetime
import unicodedata
import logging
import xml.sax.saxutils
import tempfile

import gtk
import cairo
import pango
import pangocairo
import gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)

class AozoraAccent():
    """ アクセント分解による文字の置換
    """
    accenttable = {
        u'!@':u'¡', u'?@':u'¿',
        u'A`':u'À', u"A'":u'Á', u'A^':u'Â', u'A~':u'Ã', u'A:':u'Ä', u'A&':u'Å',
        u'AE&':u'Æ',
        u'C,':u'Ç',
        u'E`':u'È', u"E'":u'É', u'E^':u'Ê', u'E:':u'Ë',
        u'I`':u'Ì', u"I'":u'Í', u'I^':u'Î', u'I:':u'Ï',
        u'N~':u'Ñ',
        u'O`':u'Ò', u"O'":u'Ó', u'O^':u'Ô', u'O~':u'Õ',u'O:':u'Ö', u'O/':u'Ø',
        u'U`':u'Ù', u"U'":u'Ú', u'U^':u'Û', u'U:':u'Ü',
        u"Y'":u'Ý', u's&':u'ß',
        u'a`':u'à', u"a'":u'á', u'a^':u'â', u'a~':u'ã', u'a:':u'ä', u'a&':u'å',
        u'ae&':u'æ',u'c,':u'ç',
        u'e`':u'è', u"e'":u'é', u'e^':u'ê', u'e:':u'ë',
        u'i`':u'ì', u"i'":u'í', u'i^':u'î', u'i:':u'ï',
        u'n~':u'ñ',
        u'o`':u'ò', u"o'":u'ó', u'o^':u'ô', u'o~':u'õ', u'o:':u'ö', u'o/':u'ø',
        u'u`':u'ù', u"u'":u'ú', u'u^':u'û', u'u:':u'ü',
        u"y'":u'ý', u'y:':u'ÿ',
        u'A_':u'Ā', u'a_':u'ā',
        u'E_':u'Ē', u'e_':u'ē',
        u'I_':u'Ī', u'i_':u'ī',
        u'O_':u'Ō', u'o_':u'ō',
        u'OE&':u'Œ',u'oe&':u'œ',u'U_':u'Ū', u'u_':u'ū' }

        # u'--':u'Ð', u'--':u'Þ', u'--':u'ð', u'--':u'þ',

    def __init__(self):
        pass

    def replace_sub(self, src, pos=0):
        """ アクセント変換文字列〔〕を渡して定義済み文字があれば変換して返す。
            〔〕は閉じていること。
            前後の括弧は取り除かれる。
            無ければ source をそのまま返す。
            ネスティング対応あり。
        """
        try:
            while src[pos] != u'〕':
                if src[pos] == u'〔':
                    tmpSrc, tmpEnd = self.replace_sub( src[pos+1:] )
                    curr = pos
                    pos = len(src[:curr]+tmpSrc)
                    src = src[:curr] + tmpSrc + tmpEnd
                    continue

                sTmp = src[pos:pos+2]
                if sTmp in AozoraAccent.accenttable:
                    # match
                    src = src[:pos] + \
                            AozoraAccent.accenttable[sTmp] + \
                            src[pos+2:]
                    pos += len(AozoraAccent.accenttable[sTmp])
                else:
                    sTmp = src[pos:pos+3]
                    if sTmp in AozoraAccent.accenttable:
                        # match
                        src = src[:pos] + \
                                AozoraAccent.accenttable[sTmp] + \
                                src[pos+3:]
                        pos += len(AozoraAccent.accenttable[sTmp])
                    else:
                        pos += 1
        except IndexError:
            pass

        return src[:pos], src[pos+1:]

    def replace(self, src):
        """ 呼び出し
        """
        r = src.find( u'〔' )
        if r != -1:
            src, src1 = self.replace_sub(src, r)
            src = src + src1
        return src


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
            while True:
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


class Aozora(ReaderSetting):
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

    # 未実装タグ
    reOmit = re.compile(
                ur'(［＃(ここから)??横組み］)|'+
                ur'(［＃(ここで)??横組み終わり］)|' +
                ur'(［＃「.+?」は縦中横］)|' +
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
        u'［＃太字］':u'<span font_desc="Sans bold">',
        u'［＃ここから太字］':u'<span font_desc="Sans bold">',
        u'［＃斜体］':u'<span style="italic">',
        u'［＃ここから斜体］':u'<span style="italic">' }

    # 右側傍点及び傍線
    dicBouten = {
        u'白ゴマ傍点':u'﹆　',
        u'丸傍点':u'●　',      u'白丸傍点':u'○　',    u'黒三角傍点':u'▲　',
        u'白三角傍点':u'△　',  u'二重丸傍点':u'◎　',  u'蛇の目傍点':u'　◉',
        u'ばつ傍点':u'　×',    u'傍点':u'﹅　',
        u'波線':u'〜〜',        u'二重傍線':u'━━',    u'鎖線':u'- - ',
        u'破線':u'─　',        u'傍線':u'──'  }

    # 文字の大きさ
    dicMojisize = {
        u'大き１':u'large',    u'大き２':u'x-large',
        u'小さ１':u'small',    u'小さ２':u'x-small' }

    # Pangoタグを除去する
    reTagRemove = re.compile(ur'<[^>]*?>')

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

    # 文字サイズ変更への暫定対応
    fontsizefactor = {
            u'normal':1.0,
            u'size="smaller"':0.813,        u'size="larger"':1.2000,
            u'size="small"':0.813,          u'size="large"':1.2000,
            u'size="x-small"':0.694,        u'size="x-large"':1.4375,
            u'size="xx-small"':0.555,       u'size="xx-large"':1.7500,
            u'<sup>':0.800,                 u'<sub>':0.800 }
    reFontsizefactor = re.compile( ur'(?P<name>size=".+?")' )

    def __init__( self, chars=40, lines=25 ):
        ReaderSetting.__init__(self)
        self.destfile = os.path.join(self.get_value(u'workingdir'), 'view.txt')    # フォーマッタ出力先
        self.mokujifile = os.path.join(self.get_value( u'workingdir'), 'mokuji.txt')    # 目次ファイル
        self.readcodecs = 'shift_jis'
        self.pagelines = int(self.get_value(u'lines'))  # 1頁の行数
        self.chars = int(self.get_value(u'column'))     # 1行の最大文字数
        self.charsmax = self.chars - 1                  # 最後の1文字は禁則処理用に確保
        self.pagecounter = 0
        self.set_source( None )
        self.BookTitle = u''
        self.BookAuthor = u''
        self.BookTranslator = u''

    def set_source( self, s ):
        """ 青空文庫ファイルをセット
        """
        if s != None:
            self.sourcefile = s         # 青空文庫ファイル（ルビあり、shift-jis）
        else:
            self.sourcefile = u''
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
        try:
            with file(self.mokujifile,'r') as f0:
                for s in f0:
                    yield s.strip('\n')
        except:
            pass

    def get_booktitle_sub( self, sourcefile=None ):
        """ 書名・著者名を取得する。
        """
        iCurrentReadline = 0
        sBookTitle = u''
        sBookTitle2 = u''
        sBookTranslator = u''
        sBookAuthor = u''

        if sourcefile == None:
            sourcefile = self.sourcefile

        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            for line in f0:
                iCurrentReadline += 1
                lnbuf = line.rstrip('\r\n')
                #   空行に出くわすか、説明が始まったら終わる
                if not lnbuf or lnbuf == Aozora.sHeader:
                    if sBookTranslator != u'':
                        sBookAuthor = u'%s / %s' % (sBookAuthor ,sBookTranslator)
                    break
                #   書名、著者名を得る
                if iCurrentReadline == 1:
                    sBookTitle = lnbuf
                #   副題
                if iCurrentReadline == 2:
                    sBookTitle2 = lnbuf
                #   末尾に「訳」とあれば翻訳者扱い
                if lnbuf[-1] == u'訳':
                    sBookTranslator = lnbuf
                else:
                    sBookAuthor = lnbuf

        if sBookTitle2 == sBookAuthor:
            sBookTitle2 = u''
        sBookTitle = u'%s %s' % (sBookTitle, sBookTitle2 )
        return (sBookTitle, sBookAuthor)

    def countlines(self, sourcefile=None ):
        """ ファイル中の行を数える
        """
        if sourcefile == None:
            sourcefile = self.sourcefile
        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            c = 0
            for ln in f0:
                c += 1
        return c

    def formater_pass1( self, sourcefile=None ):
        """ フォーマッタ（第1パス）
            formater より呼び出されるジェネレータ。1行読み込んでもっぱら
            置換処理を行う。
        """
        if sourcefile == None:
            sourcefile = self.sourcefile

        headerflag = False      # 書名以降の注釈部分を示す
        boutoudone = False      # ヘッダ処理が終わったことを示す
        footerflag = False
        aozorastack = []        # ［＃形式タグ用のスタック
        gaijitest = gaiji()
        accenttest = AozoraAccent()

        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            yield u'［＃ページの左右中央］' # 作品名を1ページ目に表示する為
            for lnbuf in f0:
                lnbuf = lnbuf.rstrip('\r\n')
                """ ヘッダ【テキスト中に現れる記号について】の処理
                    とりあえずばっさりと削除する
                """
                if Aozora.sHeader == lnbuf:
                    headerflag = False if headerflag else True
                    continue
                if headerflag == True:
                    continue

                """ 前の行で閉じていなかった青空タグがあれば
                    復元する
                """
                if aozorastack != []:
                    while True:
                        try:
                            lnbuf = aozorastack.pop() + lnbuf
                        except:
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
                lnbuf = accenttest.replace( lnbuf )

                """ tag 対策
                    pango で引っかかる & < > を 特殊文字に変換する
                """
                lnbuf = xml.sax.saxutils.escape( lnbuf )

                """ フッタ
                """
                tmp = Aozora.reFooter.search(lnbuf)
                if tmp:
                    footerflag = True
                    if tmp.group('type') == u'［＃本文終わり］':
                        lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]

                """ くの字の置換
                """
                lnbuf = Aozora.reKunoji.sub( u'〳〵', lnbuf )
                lnbuf = Aozora.reGunoji.sub( u'〴〵', lnbuf )

                """ ダブルクォーテーションの、ノノカギへの置換
                    カテゴリを調べて、アルファベット以外及び記号以外の
                    何かが出現した場合に日本語とみなして置換する。
                """
                for tmp in Aozora.reNonokagi.finditer( lnbuf ):
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
                    tmp = Aozora.reCTRL2.search(lnbuf)
                    while tmp != None:
                        try:
                            if lnbuf[tmp.start()-1] == u'※':
                                tmp2 = Aozora.reGaiji3.match(tmp.group())
                                if tmp2:
                                    # 外字置換（JIS第3、第4水準）
                                    k = gaijitest.sconv(tmp2.group('number'))
                                    if k == None:
                                        logging.info( u'未登録の外字を検出：%s' % tmp.group())
                                        k = u'［'+tmp.group()[2:]
                                    lnbuf = lnbuf[:tmp.start()-1] + k + lnbuf[tmp.end():]
                                    tmp = Aozora.reCTRL2.search(lnbuf)
                                    continue

                                tmp2 = Aozora.reGaiji4.match(tmp.group())
                                if tmp2:
                                    # 外字置換（Unicode文字）
                                    try:
                                        k = unicodedata.lookup(
                                            u'CJK UNIFIED IDEOGRAPH-' + tmp2.group('number'))
                                    except KeyError:
                                        k = u'［'+tmp.group()[2:]
                                        logging.info( u'未定義の外字を検出：%s' % k )
                                    lnbuf = lnbuf[:tmp.start()-1] + k + lnbuf[tmp.end():]
                                    tmp = Aozora.reCTRL2.search(lnbuf)
                                    continue

                                tmp2 = Aozora.reKogakiKatakana.match(tmp.group())
                                if tmp2:
                                    #   小書き片仮名
                                    #   ヱの小文字など、JISにフォントが無い場合
                                    lnbuf = u'%s<span size="smaller">%s</span>%s' % (
                                        lnbuf[:tmp.start()].rstrip(u'※'),
                                        tmp2.group(u'name'),
                                        lnbuf[tmp.end():] )
                                    tmp = Aozora.reCTRL2.search(lnbuf)
                                    continue

                                # JISにもUnicodeにも定義されていない文字の注釈
                                # ※［＃「」、底本ページ-底本行］ -> ※「」
                                tmp2 = Aozora.reGaiji5.match(tmp.group())
                                if tmp2:
                                    lnbuf = lnbuf[:tmp.start()] + \
                                            tmp2.group(u'name') + lnbuf[tmp.end():]
                                    tmp = Aozora.reCTRL2.search(lnbuf)
                                    continue
                        except IndexError:
                            pass

                        if tmp.group() in Aozora.dicAozoraTag:
                            # 単純な Pango タグへの置換
                            lnbuf = lnbuf[:tmp.start()] + \
                                    Aozora.dicAozoraTag[tmp.group()] + \
                                    lnbuf[tmp.end():]
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        if Aozora.reOmit.match(tmp.group()):
                            # 未実装タグの除去
                            logging.info( u'未実装タグを検出: %s' % tmp.group() )
                            self.loggingflag = True
                            lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reCaption.match(tmp.group())
                        if tmp2:
                            #   キャプション
                            #   暫定処理：小文字で表示
                            tmpStart,tmpEnd = self.honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span size="smaller">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf,tmpStart)
                            continue

                        tmp2 = Aozora.reMojisize.match(tmp.group())
                        if tmp2:
                            #   文字の大きさ
                            #   文字の大きさ２　と互換性がないので、こちらを
                            #   先に処理すること
                            sNameTmp = tmp2.group(u'name') + tmp2.group(u'size')
                            try:
                                sSizeTmp = Aozora.dicMojisize[sNameTmp]
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
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reMojisize2.match(tmp.group())
                        if tmp2:
                            #   文字の大きさ２
                            #   文字の大きさ　と互換性がない（誤検出する）ので、
                            #   こちらを後に処理すること
                            sNameTmp = tmp2.group(u'name') + tmp2.group(u'size')
                            try:
                                sSizeTmp = Aozora.dicMojisize[sNameTmp]
                            except KeyError:
                                sSizeTmp = u'xx-small' if sNameTmp[:2] == u'小さ' else u'xx-large'

                            lnbuf = u'%s<span size="%s">%s' % (
                                lnbuf[:tmp.start()], sSizeTmp, lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reLeftBousen.match(tmp.group())
                        if tmp2:
                            #   左に（二重）傍線
                            tmpStart,tmpEnd = self.honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span underline="%s">%s</span>%s%s' % (
                                lnbuf[:tmpStart],
                                'single' if tmp2.group('type') == None else 'double',
                                lnbuf[tmpStart:tmpEnd],
                                lnbuf[tmpEnd:tmp.start()],
                                lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        if Aozora.reOwari.match(tmp.group()):
                            #   </span>生成用共通処理
                            lnbuf = u'%s</span>%s' % (
                                lnbuf[:tmp.start()], lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reMama.match(tmp.group())
                        if tmp2 == None:
                            tmp2 = Aozora.reMama2.match(tmp.group())
                        if tmp2:
                            #   ママ注記
                            sNameTmp = tmp2.group(u'name')
                            reTmp = re.compile( ur'%s$' % sNameTmp )
                            lnbuf = u'%s｜%s《%s》%s' % (
                                reTmp.sub( u'', lnbuf[:tmp.start()]),
                                sNameTmp, tmp2.group(u'mama'), lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reRubimama.match(tmp.group())
                        if tmp2:
                            #   ルビのママ
                            lnbuf = u'%s《%s》%s' % (
                                    lnbuf[:tmp.start()],
                                    u'(ルビママ)',
                                    lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reBouten.match(tmp.group())
                        if tmp2:
                            #   傍点・傍線
                            #   rstrip では必要以上に削除する場合があるので
                            #   reのsubで消す
                            reTmp = re.compile(ur'%s$' % tmp2.group('name'))
                            try:
                                sNameTmp = Aozora.dicBouten[tmp2.group('type') + \
                                                            tmp2.group('type2')]
                            except KeyError:
                                sNameTmp = u''
                            lnbuf = u'%s｜%s《%s》%s' % (
                                reTmp.sub( u'', lnbuf[:tmp.start()]),
                                tmp2.group('name'),
                                self.zenstring(sNameTmp, len(tmp2.group('name'))),
                                        lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        if Aozora.reBouten2.match(tmp.group()):
                            # ［＃傍点］
                            aozorastack.append(tmp.group())
                            lnbuf = lnbuf[:tmp.start()]+u'｜'+lnbuf[tmp.end():]
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reBouten2owari.match(tmp.group())
                        if tmp2:
                            # ［＃傍点終わり］
                            if Aozora.reBouten2.match(aozorastack[-1]):
                                aozorastack.pop()
                                sNameTmp = tmp2.group('type')+tmp2.group('type2')
                                lnbuf = u'%s《%s》%s' % (
                                    lnbuf[:tmp.start()],
                                    self.zenstring(Aozora.dicBouten[sNameTmp],
                                        self.boutencount(lnbuf[:tmp.start()])),
                                    lnbuf[tmp.end():] )
                                tmp = Aozora.reCTRL2.search(lnbuf)
                            else:
                                # mismatch
                                lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            continue

                        tmp2 = Aozora.reGyomigikogaki.match(tmp.group())
                        if tmp2:
                            #   行右小書き・上付き小文字、行左小書き・下付き小文字
                            #   pango のタグを流用
                            sNameTmp = tmp2.group(u'name')
                            reTmp = re.compile( ur'%s$' % sNameTmp )
                            lnbuf = u'%s%s%s' % (
                                reTmp.sub( u'', lnbuf[:tmp.start()] ),
                                u'<sup>%s</sup>' % tmp2.group(u'name') if tmp2.group(u'type') == u'行右小書き' or \
                                    tmp2.group('type') == u'(上付き小文字)' else u'<sub>%s</sub>' % tmp2.group(u'name'),
                                lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reFutoji.match(tmp.group())
                        if tmp2:
                            #   太字
                            #   pango のタグを流用
                            tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span font_desc="Sans bold">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            lnbuf[tmpStart:tmpEnd],
                                            lnbuf[tmpEnd:tmp.start()],
                                                lnbuf[tmp.end():] )
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reSyatai.match(tmp.group())
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
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reKuntenOkuri.match(tmp.group())
                        if tmp2:
                            #   訓点送り仮名
                            #   pango のタグを流用
                            lnbuf = u'%s<sup>%s</sup>%s' % (
                                lnbuf[:tmp.start()],
                                    tmp2.group(u'name'),
                                        lnbuf[tmp.end():])
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        tmp2 = Aozora.reKaeriten.match(tmp.group())
                        if tmp2:
                            #   返り点
                            #   pango のタグを流用
                            lnbuf = u'%s<sub>%s</sub>%s' % (
                                lnbuf[:tmp.start()],
                                    tmp2.group(u'name'),
                                        lnbuf[tmp.end():])
                            tmp = Aozora.reCTRL2.search(lnbuf)
                            continue

                        #   上記以外のタグは後続処理に引き渡す
                        tmp = Aozora.reCTRL2.search(lnbuf,tmp.end())

                    if not isRetry and aozorastack:
                        # タグ処理で同一行にて閉じていないものがある場合
                        # 一旦閉じてタグ処理を完結させる。
                        # スタックに捨てタグを積むことに注意
                        try:
                            aozorastack.append(aozorastack[-1])
                            tmp2 = Aozora.reCTRL3.match(aozorastack[-1])
                            sNameTmp = tmp2.group('name')
                        except:
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
                    for tmp in Aozora.reNenGetsuNichi.finditer(lnbuf):
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
        if boutoudone == False:
            yield u'［＃改ページ］'

    def boutencount(self, honbun):
        """ 本文を遡って傍点の打込位置を探し、キャラクタ数を返す
        """
        c = 0
        pos = len(honbun) - 1
        if pos > 0:
            inRubi = False
            inTag = False
            inAtag = False
            try:
                while honbun[pos] != u'｜':
                    if honbun[pos] == u'［':
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
            except IndexError:
                pass
        return c

    def honbunsearch(self, honbun, name):
        """ 本文を遡って name を検索し、その出現範囲を返す。
            name との比較に際して
                ルビ、<tag></tag>、［］は無視される。
            比較は行末から行頭に向かって行われることに注意。
            見つからなければ start とend に同じ値を返す。
            配列添字に使えばヌル文字となる。
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
            if honbun[pos] == u'［':
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
            elif inRubiDetect == True and honbun[pos] == u'｜':
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

    def formater( self, output_file=None, mokuji_file=None ):
        """ フォーマッタ
        """
        if output_file != None:
            self.destfile = output_file
        if mokuji_file != None:
            self.mokujifile = mokuji_file

        (self.BookTitle, self.BookAuthor) = self.get_booktitle_sub()
        logging.info( u'****** %s ******' % self.sourcefile )


        with file( self.destfile, 'w' ) as fpMain:
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

            with file( self.mokujifile, 'w' ) as self.mokuji_f:
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
                    """
                    retline = u''
                    priortail = 0
                    IndentJitsuki = False
                    for tmp in Aozora.reCTRL.finditer(lnbuf):
                        matchFig = Aozora.reFig.match(tmp.group())
                        if matchFig != None:
                            """ 挿図
                                キャンバスの大きさに合わせて画像を縮小する。
                                幅　　上限　キャンバスの半分迄
                                高さ　上限　キャンバスの高さ迄

                                ページからはみ出るようであれば挿図前に
                                改ページする。

                                tmpRatio : 縮小倍率
                                tmpWidth : 画像横幅
                                figspan  : 画像幅の行数換算値
                            """
                            tmpH = float(self.get_value(u'scrnheight')) - \
                                    float(self.get_value(u'bottommargin')) - \
                                            float(self.get_value(u'topmargin'))
                            tmpW = float(self.get_value(u'scrnwidth')) - \
                                    float(self.get_value(u'rightmargin')) - \
                                            float(self.get_value(u'leftmargin'))
                            tmpW /= 2 # 許可される最大幅

                            #   タグに図のピクセルサイズが正しく登録されていない
                            #   場合があるので、画像ファイルを開いてチェックする
                            try:
                                logging.debug( matchFig.group(u'filename'))
                                fname = matchFig.group(u'filename')
                                tmpPixBuff = gtk.gdk.pixbuf_new_from_file(
                                    os.path.join(self.get_value(u'aozoracurrent'),
                                        fname))
                                figheight = float(tmpPixBuff.get_height())
                                figwidth = float(tmpPixBuff.get_width())
                                tmpRasio = round(tmpH / figheight,4)
                                tmpRasioW = round(tmpW / figwidth,4)

                                del tmpPixBuff
                            except gobject.GError:
                                # ファイルI/Oエラー
                                self.loggingflag = True
                                logging.info(
                                    u'画像ファイル %s の読み出しに失敗しました。' % fname )
                                retline += lnbuf[priortail:tmp.start()]
                                priortail = tmp.end()
                                continue
                            if tmpRasioW > 1.0:
                                tmpRasioW = 1.0
                            if tmpRasio > 1.0:
                                tmpRasio = 1.0
                            if tmpRasioW < tmpRasio:
                                tmpRasio = tmpRasioW
                            if tmpRasioW > tmpRasio:
                                tmpRasioW = tmpRasio

                            tmpWidth = int(round(figwidth * tmpRasioW,0))

                            figspan = int(round(float(tmpWidth) / \
                                    float(self.get_value(u'linewidth'))+0.5,0))
                            if self.linecounter + figspan >= \
                                                int(self.get_value(u'lines')):
                                # 画像がはみ出すようなら改ページする
                                while self.write2file( dfile, '\n' ) != True:
                                    pass
                            self.write2file( dfile,
                                    '%s,%s,%s,%d,%f\n' %
                                        (fname,
                                            tmpWidth,
                                            int(round(figheight * tmpRasio,0)),
                                            figspan,
                                            tmpRasio ) )
                            figspan -= 1
                            while figspan > 0:
                                self.write2file( dfile, '\n' )
                                figspan -= 1
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
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

                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 改ページ・改訂・改段
                        """
                        if Aozora.reKaipage.match(tmp.group()) != None:
                            if self.pagecenterflag:
                                # ページの左右中央の処理
                                self.pagecenterflag = False
                                if len(workfilestack) == 1:
                                    # 退避してあるハンドルをフォーマット出力先
                                    # と見てページカウントを再開する。
                                    self.countpage = True

                                # 一時ファイルに掃き出された行数を数えて
                                # ページ中央にくるようにパディングする
                                # ルビ行が含まれていることに留意
                                dfile.seek(0)
                                iCenter = 0
                                for sCenter in dfile:
                                    iCenter += 1
                                iCenter = int(round((float(self.pagelines) - float(iCenter)/2.)/2.))
                                while iCenter > 0:
                                    self.write2file( workfilestack[-1], '\n' )
                                    iCenter -= 1
                                # 一時ファイルの内容を退避してあるハンドル先へ
                                # コピーする
                                dfile.seek(0)
                                iCenter = 0
                                for sCenter in dfile:
                                    if iCenter == 0:
                                        sRubi = sCenter
                                        iCenter += 1
                                    else:
                                        self.write2file( workfilestack[-1], sCenter,sRubi )
                                        iCenter = 0
                                dfile.close()
                                dfile = workfilestack.pop()

                            if self.linecounter != 0:
                                # ページ先頭に出現した場合は改ページしない
                                while self.write2file( dfile, '\n' ) != True:
                                    pass
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 見出し
                            ここでは正確なページ番号が分からないので、
                            見出し出現のフラグだけ立てて、目次作成は後段で行う。
                            複数行見出しはサポートしない
                            <span face="Sans" size="larger">
                            見出し《ルビ》</span>
                        """
                        matchMidashi = Aozora.reMidashi.match(tmp.group())
                        if matchMidashi != None:
                            # 1行見出し
                            self.inMidashi = True
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            self.midashi = matchMidashi.group(u'midashi')
                            tmpStart,tmpEnd = self.honbunsearch(
                                    lnbuf[:tmp.start()],self.midashi)
                            retline += lnbuf[priortail:tmpStart]
                            #retline += u'<span font_family="Sans"'
                            #retline += u'<span font_desc="Sans"'
                            retline += u'<span face="Sans"'
                            if self.sMidashiSize == u'大':
                                retline += u' size="larger"'
                            retline += u'>%s</span>' % lnbuf[tmpStart:tmpEnd]
                            retline += lnbuf[tmpEnd:tmp.start()]
                            priortail = tmp.end()
                            continue

                        matchMidashi = Aozora.reMidashi2.match(tmp.group())
                        if matchMidashi != None:
                            # <見出し>
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            self.inMidashi = True
                            self.inFukusuMidashi = True
                            self.midashi = u''
                            retline += lnbuf[priortail:tmp.start()]
                            #retline += u'<span font_family="Sans"'
                            #retline += u'<span font_desc="Sans"'
                            retline += u'<span face="Sans"'
                            if self.sMidashiSize == u'大':
                                retline += u' size="larger"'
                            retline += u'>'
                            priortail = tmp.end()
                            continue

                        matchMidashi = Aozora.reMidashi2owari.match(tmp.group())
                        if matchMidashi != None:
                            # <見出し終わり>
                            self.FukusuMidashiOwari = True
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            retline += lnbuf[priortail:tmp.start()]
                            retline += u'</span>'
                            priortail = tmp.end()
                            continue

                        """ 字下げ
                        """
                        tmp2 = Aozora.reIndent.match(tmp.group())
                        if tmp2:
                            jisage = self.zentoi(tmp2.group('number'))
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        tmp2 = Aozora.reIndentStart.match(tmp.group())
                        if tmp2:
                            inIndent = True
                            jisage = self.zentoi(tmp2.group('number'))
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        if Aozora.reIndentEnd.match(tmp.group()):
                            inIndent = False
                            jisage = 0
                            jisage2 = 0
                            jisage3 = 0
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        tmp2 = Aozora.reKokokaraSage.match(tmp.group())
                        if tmp2:
                            jisage = self.zentoi(tmp2.group('number'))
                            jisage2 = self.zentoi(tmp2.group('number2'))
                            inIndent = True
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        tmp2 = Aozora.reKaigyoTentsuki.match(tmp.group())
                        if tmp2:
                            jisage = 0
                            jisage2 = self.zentoi(tmp2.group('number'))
                            inIndent = True
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 字詰
                        """
                        tmp2 = Aozora.reJizume.match(tmp.group())
                        if tmp2:
                            jizume = self.zentoi(tmp2.group('number'))
                            inJizume = True
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        if Aozora.reJizumeowari.match(tmp.group()):
                            inJizume = False
                            jizume = 0
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 字上
                        """
                        if Aozora.reJiage.match(tmp.group()):
                            """ 行途中で出現する字上げは後段へそのまま送る
                            """
                            retline += lnbuf[priortail:tmp.end()]
                            priortail = tmp.end()
                            continue

                        tmp2 = Aozora.reKokokaraJiage.match(tmp.group())
                        if tmp2:
                            inJiage = True
                            jiage = self.zentoi(tmp2.group('number'))
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        if Aozora.reJiageowari.match(tmp.group()):
                            inJiage = False
                            jiage = 0
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 地付き
                        """
                        if Aozora.reKokokaraJitsuki.match(tmp.group()):
                            inJiage = True
                            jiage = 0
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        if Aozora.reJitsukiowari.match(tmp.group()):
                            inJiage = False
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 罫囲み
                            天と地に罫線描画用に1文字の空きが必要に
                            なるのでインデント処理を勘案してここで
                            準備する。
                        """
                        if Aozora.reKeikakomi.match(tmp.group()):
                            inKeikakomi = True
                            # カレントハンドルを退避して、一時ファイルを
                            # 作成して出力先を切り替える。
                            workfilestack.append(dfile)
                            dfile = tempfile.NamedTemporaryFile(mode='w+',delete=True)
                            # 一時ファイル使用中はページカウントしない
                            self.countpage = False
                            continue

                        if Aozora.reKeikakomiowari.match(tmp.group()):
                            inKeikakomi = False
                            if len(workfilestack) == 1:
                                # 退避してあるハンドルをフォーマット出力先と
                                # 見てページカウントを再開
                                self.countpage = True

                            # 一時ファイルに掃き出された行数を数える
                            # ルビ行を含む点に留意。
                            dfile.seek(0)
                            iCenter = 0
                            for sCenter in dfile:
                                iCenter += 1
                            iCenter /= 2
                            if iCenter < self.pagelines:
                                # 罫囲みが次ページへまたがる場合は改ページする。
                                # 但し、１ページを越える場合は無視する。
                                if self.linecounter + iCenter >= self.pagelines:
                                    while self.write2file(workfilestack[-1], '\n' ) != True:
                                        pass

                            # 一時ファイルからコピー
                            dfile.seek(0)
                            iCenter = 0
                            for sCenter in dfile:
                                if iCenter == 0:
                                    sRubi = sCenter
                                    iCenter += 1
                                else:
                                    self.write2file(workfilestack[-1], sCenter,sRubi)
                                    iCenter = 0
                            dfile.close()
                            dfile = workfilestack.pop()
                            continue

                        """ 未定義のタグ
                        """
                        logging.info( u'検出された未定義タグ : %s' % tmp.group() )
                        self.loggingflag = True

                        retline += lnbuf[priortail:tmp.start()]
                        priortail = tmp.end()
                        retline += tmp.group()
                    retline += lnbuf[priortail:]
                    lnbuf = retline

                    """ ルビの処理
                        本文に合わせてサイドライン(rubiline)に全角空白をセットする。
                        文字種が変わる毎にルビ掛かり始めとみなして、＃をセットする。
                        ルビが出現したら直前の ＃までバックしてルビをセットする。
                    """
                    rubiline = u''
                    retline = u''
                    inRubi = False
                    tplast = u''
                    tp = u''
                    rubispan = 0
                    isAnchor = False
                    inTag = False
                    for s in lnbuf:
                        # タグは読み飛ばす
                        if s == u'>':
                            inTag = False
                        elif s == u'<':
                            inTag = True
                        elif inTag:
                            pass
                        else:
                            if s == u'《':
                                isAnchor = False
                                inRubi = True
                                # 直前のルビ打ち込み位置までバック
                                r2 = rubiline.rstrip( u'　' ).rstrip( u'＃' )
                                rubispan = len(rubiline) - len(r2)
                                rubiline = r2
                                continue
                            elif s == u'》':
                                inRubi = False
                                while rubispan > 0:
                                    rubiline += u'　' #u'／'
                                    rubispan -= 1
                                continue
                            elif s == u'｜':
                                rubiline += u'＃'
                                isAnchor = True
                                rubispan -= 1
                                continue
                            if inRubi == True:
                                # ルビ文字をサイドラインバッファへ
                                rubiline += s
                                rubispan -= 1
                                continue

                            # 文字種類の違いを検出してルビ開始位置に
                            # '＃' を打ち込む
                            # 但し 前方に'｜'があればルビが出現するまでスキップする
                            sPad = u'　' # 全角スペース
                            if isAnchor == False:
                                tplast = tp
                                try:
                                    tp = unicodedata.name(s).split()[0]
                                    # 非漢字でも漢字扱いとする文字
                                    # http://www.aozora.gr.jp/KOSAKU/MANUAL_2.html#ruby
                                    if tp != 'CJK':
                                        if s in u'仝〆〇ヶ〻々':
                                            tp = 'CJK'

                                    if tplast != tp:
                                        sPad = u'＃'
                                except:
                                    tp = ''

                            if rubispan < 0:
                                # ルビが本文より長い場合の調整
                                rubispan += 1
                                sPad = u''
                            rubiline += sPad
                            sPad = u'　'
                            if unicodedata.east_asian_width(s) != 'Na' or \
                                unicodedata.category(s) == 'Lu':
                                # 本文が全角文字かラテン大文字であれば幅調整する
                                if rubispan < 0:
                                    # ルビが本文より長い場合の調整
                                    rubispan += 1
                                    sPad = u''
                                rubiline += sPad

                        retline += s

                    rubiline = Aozora.reRubiclr.sub(u'　', rubiline)
                    lnbuf = retline

                    """ 行をバッファ(中間ファイル)へ掃き出す
                    """
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
                        if inJiage == True:
                            # ブロック地付き及びブロック字上げ
                            # 字下げはキャンセルされる
                            lenN = self.linelengthcount(lnbuf)
                            if jizume > 0 and lenN > jizume:
                                lenN = jizume
                            if lenN < currchars:
                                sIndent = self.zenstring(u'　',currchars - lenN)
                                lnbuf = sIndent + lnbuf
                                rubiline = sIndent + sIndent + rubiline
                        else:
                            # インデントの挿入
                            if jisage + jizume > currchars:
                                currjisage = 1 if currchars - jisage < 0 else jisage
                            else:
                                if jizume > 0:
                                    currchars = jisage + jizume
                                currjisage = jisage

                            if currjisage > 0:
                                sIndent = self.zenstring(u'　',currjisage)
                                lnbuf = sIndent + lnbuf
                                rubiline = sIndent + sIndent + rubiline

                            # 地付きあるいは字上げ(同一行中を含む)
                            # 出現した場合、字詰はキャンセルされる
                            #  name2 [tag] name
                            tmp2 = Aozora.reJiage.match(lnbuf)
                            if tmp2:
                                sP = u'' if tmp2.group('name2') == None else tmp2.group('name2')
                                lenP = self.linelengthcount(sP)
                                sN = u'' if tmp2.group('name') == None else tmp2.group('name')
                                lenN = self.linelengthcount(sN)
                                try:
                                    # 字上げ n
                                    n = self.zentoi(tmp2.group('number'))
                                except:
                                    # 地付き
                                    n = 0
                                currchars = self.charsmax - n
                                if lenP + lenN <= currchars:
                                    # 表示が1行分に収まる場合は処理する。
                                    sPad = self.zenstring(u'　',currchars -lenP -lenN)
                                    lnbuf = sP + sPad + sN
                                    # ルビ表示 地付きタグ分を取り除くこと
                                    rubiline = rubiline[:lenP*2] + sPad + sPad + rubiline[lenP*2+len(tmp2.group('tag'))*2 :]
                                else:
                                    #if lenN >= currchars or lenP >= currchars:
                                    if lenN >= currchars:
                                        # 地付きする文字列が1行の長さを越えている場合、通常の
                                        # 行として終わる。
                                        # 地付きはこれで良いが、字上げの場合はタグの次行繰越処理を
                                        # 追加したい（ここで処理できないのでlinesplitで）
                                        lnbuf = sP + sN
                                        rubiline = rubiline[:lenP*2] + rubiline[lenP*2+len(tmp2.group('tag'))*2:]
                                        currchars = self.charsmax
                                    else:
                                        # 収まらない場合、最終行のみ字下げする
                                        if (lenP % self.charsmax + lenN) > currchars:
                                            sPad = self.zenstring(u'　',self.charsmax - lenP % self.charsmax)
                                            sPad += self.zenstring(u'　',currchars - lenN)
                                        else:
                                            sPad = self.zenstring(u'　',currchars -lenN - lenP % self.charsmax)
                                        lnbuf = sP + sPad  + sN
                                        rubiline = rubiline[:lenP*2] + sPad + sPad + rubiline[lenP*2+len(tmp2.group('tag'))*2:]
                                        currchars = self.charsmax

                        #   画面上の1行で収まらなければ分割して次行を得る
                        self.ls, lnbuf, rubi2, rubiline = self.linesplit(
                                                    lnbuf, rubiline, currchars)
                        self.write2file( dfile, "%s\n" % self.ls, "%s\n" % rubi2)

                        #   折り返しインデント
                        if lnbuf != '':
                            if jisage2 != 0:
                                if jisage2 != jisage:
                                    jisage3 = jisage # 初段字下げ幅退避
                                    jisage = jisage2
                        else:
                            jisage = jisage3 # 初段回復

                        #   単発か否か
                        if inIndent == False:
                            jisage = 0
                        if inJizume == False:
                            jizume = 0
                        if inJiage == False:
                            jiage = 0

    def linelengthcount(self, sline):
        """ 文字列の長さを数える
            文字の大きさ変更等に対応
            <tag></tag> はカウントしない。
        """
        l = 0.0
        inTag = False
        inCloseTag = False
        tagname = u''
        tagstack = []
        fontsizename = u'normal'

        for s in sline:
            if s == u'>':
                # tagスタックの操作
                tagname += s
                if inCloseTag:
                    inCloseTag = False
                    # </tag>の出現とみなしてスタックから取り除く
                    # ペアマッチの処理は行わない
                    try:
                        if tagstack.pop() in self.fontsizefactor:
                            # 文字サイズの復旧
                            fontsizename = u'normal'
                    except IndexError:
                        pass
                else:
                    tagstack.append(tagname)
                    tmp = Aozora.reFontsizefactor.search(tagname)
                    if tmp:
                        if tmp.group() in self.fontsizefactor:
                            fontsizename = tmp.group() # 文字サイズ変更
                    tagname = u''
                inTag = False
            elif s == u'<':
                inTag = True
                tagname = s
            elif inTag:
                if s == '/':
                    inCloseTag = True
                else:
                    tagname += s
            else:
                # 画面上における全長を計算
                l += self.charwidth(s) * self.fontsizefactor[fontsizename]
        return int(round(l+0.5,0))

    def charwidth(self, lsc):
        """ 文字の幅を返す
            全角 を１とする
        """
        try:
            # A-Z or a-z
            lcc = Aozora.charwidth_serif[lsc]
        except KeyError:
            if unicodedata.east_asian_width(lsc) == 'Na':
                # 非全角文字
                lcc = 0.5
            else:
                # 全角文字
                lcc = 1
        return lcc


    def linesplit(self, sline, rline, smax=0.0):
        """ 文字列を分割する
            <tag></tag> はカウントしない。
            半角文字は1文字未満として数え、合計時に切り上げる。
            カウント数が smax に達したらそこで文字列を分割して終了する。
            sline : 本文
            rline : ルビ
        """
        tagname = u''
        lcc = 0.0           # 全角１、半角0.5で長さを積算
        honbun = u''        # 本文（カレント行）
        honbun2 = u''       # 本文（分割時の次行）
        rubi = rline        # ルビ（カレント行）
        rubi2 = u''         # ルビ（分割時の次行）
        inTag = False       # <tag>処理のフラグ
        inCloseTag = False  # </tag>処理のフラグ
        inSplit = False     # 行分割処理のフラグ

        fontsizename = u'normal'

        """ 前回の呼び出しで引き継がれたタグがあれば付け足す。
        """
        while self.tagstack != []:
            sline = self.tagstack.pop() + sline

        for lsc in sline:
            if inSplit:
                # 本文の分割
                honbun2 += lsc
                continue

            if smax:
                if lcc >= smax:
                    inSplit = True
                    honbun2 += lsc
                    # ルビの処理
                    # <tag></tag>による修飾を考慮しないので単純に分割して終わる
                    rubi = rline[:int(lcc*2)]
                    rubi2 = rline[int(lcc*2):]
                    continue

            honbun += lsc
            if lsc == u'>':
                # tagスタックの操作
                tagname += lsc
                if inCloseTag:
                    inCloseTag = False
                    # </tag>の出現とみなしてスタックから取り除く
                    # ペアマッチの処理は行わない
                    try:
                        if self.tagstack.pop() in self.fontsizefactor:
                            # 文字サイズの復旧
                            fontsizename = u'normal'
                    except IndexError:
                        pass
                else:
                    self.tagstack.append(tagname)
                    tmp = Aozora.reFontsizefactor.search(tagname)
                    if tmp:
                        if tmp.group() in self.fontsizefactor:
                            fontsizename = tmp.group() # 文字サイズ変更
                    tagname = u''
                inTag = False
            elif lsc == u'<':
                inTag = True
                tagname = lsc
            elif inTag:
                if lsc == '/':
                    inCloseTag = True
                else:
                    tagname += lsc
            else:
                # 画面上における全長を計算
                lcc += self.charwidth(lsc) * self.fontsizefactor[fontsizename]

        """ 行末禁則処理
            次行先頭へ追い出す
            禁則文字が続く場合は全て追い出す
        """
        while honbun[-1] in Aozora.kinsoku2:
            honbun2 = honbun[-1] + honbun2
            honbun = honbun[:-1] + u'　'
            # ルビも同様に処理
            rubi2 = rubi[-2:]+rubi2
            rubi = rubi[:-2] + u'　　'#u'＊＊'

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
                pos += 2
                while honbun2[pos] != u'>':
                    pos += 1
                pos += 1
                self.tagstack.pop()
                honbun += honbun2[:pos]
                honbun2 = honbun2[pos:]
                pos = 0

            try:
                while honbun2[pos] == u'<':
                    # タグをスキップ
                    pos += 1
                    while honbun2[pos] != u'>':
                        pos += 1
                    pos += 1

                if honbun2[pos] in Aozora.kinsoku:
                    honbun += honbun2[pos]
                    honbun2 = honbun2[:pos]+honbun2[pos+1:]
                    # ルビも同様に処理
                    rubi = rubi + rubi2[:2]
                    rubi2 = rubi2[2:]

                    if honbun2[pos:]:
                        # ２文字目チェック
                        while honbun2[pos] == u'<':
                            # タグをスキップする
                            pos += 1
                            while honbun2[pos] != u'>':
                                pos += 1
                            pos += 1
                        if honbun2[pos] in Aozora.kinsoku:
                            if honbun2[pos] in Aozora.kinsoku4:
                                honbun += honbun2[pos]
                                honbun2 = honbun2[:pos]+honbun2[pos+1:]
                                # ルビも同様に処理
                                rubi = rubi + rubi2[:2]
                                rubi2 = rubi2[2:]
                            else:
                                # 括弧類以外（もっぱら人名対策）
                                if not (honbun[-2] in Aozora.kinsoku):
                                    honbun2 = honbun[-2:] + honbun2
                                    honbun = honbun[:-2] + u'　　'
                                    # ルビも同様に処理
                                    rubi2 = rubi[-4:]+rubi2
                                    rubi = rubi[:-4] + u'　　　　'
            except IndexError:
                pass

        """ tag の処理
            閉じていなければ一旦閉じ、次回の呼び出しに備えて
            スタックに積み直す
        """
        substack = []
        while self.tagstack:
            s = self.tagstack.pop()
            substack.append(s)
            honbun += u'</%s>' % s.split()[0].rstrip(u'>').lstrip(u'<')
        while substack:
            self.tagstack.append(substack.pop())

        return ( honbun,  honbun2, rubi, rubi2 )

    def write2file(self, fd, s, rubiline=u'\n'):
        """ formater 下請け
            1行出力後、改ページしたらその位置を記録して True を返す。
            目次作成もここで行う。
            出力時の正確なページ数と行数が分かるのはここだけ。
        """
        rv = False
        if self.countpage:
            if self.inMidashi == True:
                # 見出し書式
                if self.sMidashiSize == u'大':
                    sMokujiForm = u'%-s  % 4d\n'
                elif self.sMidashiSize == u'中':
                    sMokujiForm = u'  %-s  % 4d\n'
                elif self.sMidashiSize == u'小':
                    sMokujiForm = u'    %-s  % 4d\n'
                # 目次作成
                if self.inFukusuMidashi == True:
                    self.midashi += s.rstrip('\n')

                    if self.FukusuMidashiOwari == True:
                        # 複数行に及ぶ見出しが終わった場合
                        self.FukusuMidashiOwari = False
                        self.inFukusuMidashi = False
                        self.mokuji_f.write( sMokujiForm % (
                            Aozora.reTagRemove.sub(u'',
                                self.midashi.lstrip(u' 　').rstrip('\n')),
                            self.pagecounter +1))
                        self.inMidashi = False
                else:
                    self.mokuji_f.write( sMokujiForm % (
                        Aozora.reTagRemove.sub(u'',
                            self.midashi.lstrip(u' 　').rstrip('\n')),
                        self.pagecounter +1))
                    self.inMidashi = False

        if self.loggingflag:
            logging.debug( u'　位置：%dページ、%d行目' % (
                                    self.pagecounter+1,self.linecounter+1 ))
            self.loggingflag = False

        fd.write(rubiline)  # 右ルビ行
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

    def zenstring(self, s, n):
        """ 文字列sをn回繰り返して返す
            n が 0 あるいは 負の場合は '' を返す
        """
        r = ''
        while n > 0:
            r += s
            n -= 1
        return r


class CairoCanvas(Aozora):
    """ cairo / pangocairo を使って文面を縦書きする
    """
    def __init__(self):
        Aozora.__init__(self)
        self.resize()
        # 文字色の分解
        (self.fontR,self.fontG,self.fontB)=self.convcolor(
                                                self.get_value(u'fontcolor'))

    def resize(self):
        self.canvas_width       = int(self.get_value( u'scrnwidth' ))
        self.canvas_height      = int(self.get_value( u'scrnheight'))
        self.canvas_topmargin   = int(self.get_value( u'topmargin'))
        self.canvas_rightmargin = int(self.get_value( u'rightmargin' ))
        self.canvas_fontsize    = float(self.get_value( u'fontsize' ))
        self.canvas_rubisize    = float(self.get_value( u'rubifontsize' ))
        self.canvas_linewidth   = int(self.get_value(u'linewidth'))
        self.canvas_rubispan    = int(self.get_value(u'rubiwidth'))
        self.canvas_fontname    = self.get_value(u'fontname')

    def writepage(self, pagenum, buffname=None):
        """ 指定したページを表示する
        """
        reFig = re.compile( ur'^(?P<filename>.+?),(?P<width>[0-9]+?),(?P<height>[0-9]+?),(?P<lines>[0-9]+?),(?P<rasio>[0-9]+?\.[0-9]+?)$' )
        if buffname == None:
            buffname = self.get_outputname()

        xpos = self.canvas_width - self.canvas_rightmargin

        inKeikakomi = False # 罫囲み
        KeikakomiXendpos = xpos
        KeikakomiYendpos =  self.canvas_height - self.canvas_topmargin - int(self.get_value(u'bottommargin'))
        maxchars = 0            # 囲み内に出現する文字列の最大長
        offset_y = 0            # 文字列の書き出し位置
        tmpwidth = 0
        tmpheight = 0
        fontheight = int(round(float(self.dicSetting[u'fontsize'])*1.24+0.5))

        self.pageinit()
        with codecs.open(buffname, 'r', 'UTF-8') as f0:
            try:
                f0.seek(self.pageposition[pagenum])
            except:
                logging.error( u'SeekError Page number %d' % pagenum )
            else:
                for i in xrange(self.pagelines):
                    sRubiline = f0.readline()
                    s0 = f0.readline()
                    #tmp = Aozora.reKeikakomi.match(s0)
                    tmpxpos = s0.find(u'［＃ここから罫囲み］')
                    if tmpxpos != -1:
                        # 罫囲み開始
                        inKeikakomi = True
                        offset_y = self.chars
                        maxchars = 0
                        s0 = s0[:tmpxpos] + s0[tmpxpos+len(u'［＃ここから罫囲み］'):]
                        KeikakomiXendpos = xpos + (self.canvas_linewidth/2)

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
                        tmpwidth = KeikakomiXendpos - xpos - (self.canvas_linewidth/2)
                        context = cairo.Context(self.sf)
                        context.new_path()
                        context.set_line_width(1)
                        context.move_to(xpos - (self.canvas_linewidth/2),
                                self.canvas_topmargin + offset_y * fontheight)
                        context.rel_line_to(tmpwidth,0)
                        context.rel_line_to(0, maxchars * fontheight)
                        context.rel_line_to(-tmpwidth,0)
                        context.close_path()
                        context.stroke()

                    matchFig = reFig.search(s0)
                    if matchFig != None:
                        # 挿図処理
                        try:
                            img = cairo.ImageSurface.create_from_png(
                                    os.path.join(self.get_value(u'aozoracurrent'),
                                    matchFig.group('filename')) )
                        except cairo.Error, m:
                            logging.error( u'挿図処理中 %s %s' % (
                                m,
                                os.path.joiin(self.get_value(u'aozoracurrent'),
                                                matchFig.group('filename')) ))

                        context = cairo.Context(self.sf)
                        # 単にscaleで画像を縮小すると座標系全てが影響を受ける
                        context.scale(float(matchFig.group('rasio')),
                                                float(matchFig.group('rasio')) )
                        context.set_source_surface(img,
                                round((xpos + int(matchFig.group('lines'))/2 - \
                                   ((int(matchFig.group('lines')) * \
                                   self.canvas_linewidth))) /   \
                                   float(matchFig.group('rasio'))+0.5,0),
                                        self.canvas_topmargin)
                        context.paint()
                    else:
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

                        self.writepageline(
                            xpos,
                            self.canvas_topmargin,
                            '<span font_desc="%s %s">%s</span><span font_desc="%s %s">%s</span>' % (
                                    self.get_value(u'fontname'),
                                    self.canvas_rubisize, sRubiline,
                                    self.get_value(u'fontname'),
                                    self.canvas_fontsize, s0 ) )
                    xpos -= self.canvas_linewidth

        self.pagefinish()

    def pageinit(self):
        """ ページ初期化
        """
        # キャンバスの確保
        self.sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                        self.canvas_width, self.canvas_height)
        """ 表示フォントの設定
        """
        self.font = pango.FontDescription(u'%s %s' % (
                                        self.get_value( u'fontname' ),
                                        self.get_value(u'fontsize')) )
        self.font_rubi = pango.FontDescription(u'%s %s' % (
                                        self.get_value( u'fontname' ),
                                        self.get_value(u'rubifontsize')) )
        """ 画面クリア
        """
        context = cairo.Context(self.sf)
        context.rectangle(0, 0, self.canvas_width, self.canvas_height)
        (nR,nG,nB)=self.convcolor(self.get_value(u'backcolor'))
        context.set_source_rgb(nR,nG,nB)
        context.fill()

    def convcolor(self, s):
        """ カラーコードを16進文字列からRGB(0..1)に変換して返す
        """
        p = (len(s)-1)/3
        nR = float(eval(u'0x'+s[1:1+p])/65535.0)
        nG = float(eval(u'0x'+s[1+p:1+p+p])/65535.0)
        nB = float(eval(u'0x'+s[1+p+p:1+p+p+p])/65535.0)
        return (nR,nG,nB)

    def writepageline(self, x, y, s=u''):
        """ 指定位置へ1行書き出す
        """
        # cairo コンテキストの作成と初期化
        context = cairo.Context(self.sf)
        #context.set_antialias(cairo.ANTIALIAS_GRAY)
        #context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        context.set_antialias(cairo.ANTIALIAS_DEFAULT)
        # cairo 1.12 以降 FAST, GOOD, BEST(未確認)
        #context.set_antialias(cairo.ANTIALIAS_BEST)
        context.set_source_rgb(self.fontR,self.fontG,self.fontB) # 描画色

        # pangocairo の コンテキストをcairoコンテキストを元に作成
        pangocairo_context = pangocairo.CairoContext(context)
        pangocairo_context.translate(x, y)  # 描画位置
        pangocairo_context.rotate(3.1415/2) # 90度右回転、即ち左->右を上->下へ
        # レイアウトの作成
        layout = pangocairo_context.create_layout()
        # 表示フォントの設定
        self.font.set_size(pango.SCALE*12)
        layout.set_font_description(self.font)
        # Pangoにおけるフォントの回転(横倒し対策)
        ctx = layout.get_context() # Pango を得る
        #ctx.set_base_gravity( 'east' )
        ctx.set_base_gravity( 'auto' )

        layout.set_markup(s)
        pangocairo_context.update_layout(layout)
        pangocairo_context.show_layout(layout)

    def pagefinish(self):
        self.sf.write_to_png(os.path.join(self.get_value(u'workingdir'),
                                                            'thisistest.png'))
        self.sf.finish()



