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
from readersub_nogui import ReaderSetting, AozoraScale
import aozoraaccent
import aozoradialog

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

import gtk
import gobject

import sys
sys.stdout=codecs.getwriter('UTF-8')(sys.stdout)

class AozoraCurrentTextinfo(ReaderSetting):
    """ 現在扱っているテキストの情報を保持する

        テキストタイトル
        目次
        スクリーンレイアウト
    """
    def __init__(self):
        ReaderSetting.__init__(self)
        self.currentpage = []
        self.pagecounter = 0
        self.sourcefile= u''
        self.booktitle = u''
        self.bookauthor = u''
        self.booktranslator = u''
        self.zipfilename = u''
        self.worksid = 0

    def get_booktitle(self):
        """ 処理したファイルの書名、著者名を返す。
        """
        return (self.booktitle, self.bookauthor)


class AozoraTag(object):
    """ 青空タグの検出　ネスティング対応版
    """
    def __init__(self, regex=ur'［＃.*?］'):
        self.reTmp = re.compile(regex)

    def __sub_1(self, s, pos=0):
        """ s[pos]から終わり迄、［＃ を探してインデックスを返す。
            見つからない場合は -1 を返す。
        """
        try:
            while 1:
                if s[pos:pos+2] == u'［＃':
                    index = self.__sub_1(s, pos+2)
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
        index = self.__sub_1(s,pos)
        return None if index == -1 else self.reTmp.search(s,index)


class Aozora(ReaderSetting, AozoraScale):
    """
    """
    # ヘッダ・フッタ境界
    sHeader = u'-------------------------------------------------------'
    reFooter = re.compile(ur'(?P<type>(^(翻訳の)?底本：)|(［＃本文終わり］))')
    # 外字置換
    reGaiji3 = re.compile(ur'(※［＃.*?、.*?(?P<number>\d+\-\d+\-\d+\d*)］)')
    reGaiji4 = re.compile(ur'(※［＃.+?、U\+(?P<number>[0-9A-F]+?)、.+?］)')
    reGaiji5 = re.compile(ur'(※［＃(?P<name>.+?)、.+?］)' )
    reGaiji6 = re.compile(ur'(※［＃ローマ数字(?P<num>\d\d?)、.+?］)' )
    # このプログラムで特に予約された文字
    dicReserveChar = {
        u'感嘆符三つ':u'<aozora tatenakayoko="!!!">!!!</aozora>', # 例）河童、芥川龍之介
        u'「IIII」':u'<aozora tatenakayoko="IIII">IIII</aozora>'   # 例）ランボオ詩集、中原中也訳
        }
    # 役物置換
    reKunoji = re.compile(ur'(／＼)')
    reGunoji = re.compile(ur'(／″＼)')
    reNonokagi = re.compile(ur'((“)(?P<name>.+?)(”))')
    # 青空文庫タグ抽出
    reCTRL = re.compile(ur'(?P<aozoratag>［＃.*?］)')
    reCTRL2 = AozoraTag(ur'(?P<aozoratag>［＃.*?］)') # ネスティング対応
    reCTRL3 = re.compile(ur'(［＃(?P<name>.*?)］)')
    reCTRLGaiji = re.compile(ur'(?P<aozoratag>※［＃.*?］)')
    # 傍線・傍点
    reBouten = re.compile(ur'(［＃「(?P<name>.+?)」(?P<position>の左)?に(?P<type>.*?)' + \
                        ur'(?P<type2>(傍点)|(傍線)|(波線)|(破線)|(鎖線))］)')
    reBouten2 = re.compile(ur'［＃(?P<position>左に)?(?P<type>.*?)' + \
                        ur'(?P<type2>(傍点)|(傍線)|(波線)|(破線)|(鎖線))］')
    reBouten2owari = re.compile(ur'［＃(?P<position>左に)?(?P<type>.*?)' + \
                        ur'(?P<type2>(傍点)|(傍線)|(波線)|(破線)|(鎖線))' + \
                        ur'終わり］' )

    reGyomigikogaki = re.compile(ur'(［＃「(?P<name>.+?)」は' +
                        ur'(?P<type>(行右小書き)|(上付き小文字)|' +
                        ur'(行左小書き)|(下付き小文字))］)')

    reMama = re.compile(ur'(［＃「(?P<name>.+?)」(に|は)(?P<type>(「(?P<mama>.+?)」の注記)|(.??ママ.??))］)')
    reKogakiKatakana = re.compile(ur'(※［＃小書(き)?片仮名(?P<name>.+?)、.+?］)')

    reRubi = re.compile(ur'《.*?》')
    reRubiclr = re.compile(ur'＃')
    reRubimama = AozoraTag(ur'(［＃ルビの「(?P<name>.+?)」はママ］)')

    reFutoji = re.compile(ur'［＃「(?P<name>.+?)」は太字］')
    reSyatai = re.compile(ur'［＃「(?P<name>.+?)」は斜体］')

    # 左注記
    reLeftrubi = re.compile(ur'［＃「(?P<name>.+?)」の左に「(?P<rubi>.+?)」の(?P<type>(注記)|(ルビ))］')
    reLeftrubi2 = re.compile(ur'［＃左に注記付き］')
    reLeftrubi2owari = re.compile(ur'［＃左に「(?P<name>.+?)」の注記付き終わり］')

    # 注記
    reChuki = re.compile(ur'［＃注記付き］')
    reChukiowari = re.compile(ur'［＃「(?P<name>.+?)」の注記付き終わり］')

    # キャプション
    reCaption = re.compile(ur'(［＃「(?P<name>.*?)」はキャプション］)')
    reCaption2 = re.compile(ur'(［＃キャプション］(?P<name>.*?)［＃キャプション終わり］)')

    # 文字サイズ
    reMojisize = re.compile(ur'(［＃「(?P<name2>.+?)」は(?P<size>.+?)段階(?P<name>.+?)な文字］)')
    reMojisize2 = re.compile(ur'(［＃(ここから)?(?P<size>.+?)段階(?P<name>.+?)な文字］)')

    # 縦中横
    reTatenakayoko = re.compile(ur'(［＃「(?P<name>.+?)」は縦中横］)')

    # 割り注
    reWarichu = re.compile(ur'(［＃(ここから)??割り注］)')
    reWarichuOwari = re.compile(ur'(［＃(ここで)??割り注終わり］)')

    # 横組み
    reYokogumi = re.compile(ur'(［＃「(?P<name>.+?)」は横組み］)')

    # 底本注記
    reTeibon = re.compile(
                ur'(［＃(?P<rubi>ルビの)??「(?P<name>.+?)」は底本では「(?P<name2>.+?)」］)')

    # ルーチン内に直書きしているタグ
    """     ＃ページの左右中央
            ＃ここからキャプション ＃ここでキャプション終わり
            ＃本文終わり
            ＃改行（割り注内でのみ出現）
            ＃縦中横　＃縦中横終わり
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
    # 罫囲み（行中）
    reKeikakomiGyou = re.compile(ur'(［＃「(?P<name>.+?)」は罫囲み］)')

    # 見出し
    reMidashi = re.compile(ur'［＃「(?P<midashi>.+?)」は(?P<type>同行|窓)??(?P<midashisize>大|中|小)見出し］')
    reMidashi2name = re.compile(ur'((<.+?)??(?P<name>.+?)[<［\n]+?)')
    reMidashi2 = re.compile(ur'(［＃(?P<type>同行|窓)?(?P<midashisize>大|中|小)見出し］)')
    reMidashi2owari = re.compile(ur'(［＃(?P<type>同行|窓)?(?P<midashisize>大|中|小)見出し終わり］)')
    reMidashi3 = re.compile(ur'(［＃ここから(?P<type>同行|窓)?(?P<midashisize>大|中|小)見出し］)')
    reMidashi3owari = re.compile(ur'(［＃ここで(?P<type>同行|窓)?(?P<midashisize>大|中|小)見出し終わり］)')

    # 改ページ・改丁・ページの左右中央
    reKaipage = re.compile(ur'［＃改ページ］|［＃改丁］|［＃改段］|［＃改見開き］')

    # 挿図
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

    # 描画対策
    reDash = re.compile( ur'(?P<name>―{2,})' ) # 2文字以上のDASHの連結

    # 禁則
    kinsoku = u'\r,)]｝）］｝〕〉》」』】〙〗〟’”｠»ヽヾ。、．，ーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻‐゠–〜?!‼⁇⁈⁉・:;！？'
    kinsoku2 = u'([{（［｛〔〈《「『【〘〖〝‘“｟«〳〴'
    kinsoku4 = u'\r,)]｝）］｝〕〉》」』】〙〗〟’”｠»。、．，'
    kinsoku5 = u'\r,)]｝）］｝〕〉》」』】〙〗、'

    # 送り調整を要する文字
    kakko = u',)]｝、）］｝〕〉》」』】〙〗〟’”｠»・。、．，([{（［｛〔〈《「『【〘〖〝‘“｟«'
    hajimekakko = u'（［｛〔〈《「『【〘〖〝‘“｟«'
    owarikakko =  u'）］｝〕〉》」』】〙〗〟’”｠»'

    # 文字の大きさ
    dicMojisize = {
        u'大き１':u'large',    u'大き２':u'x-large',
        u'小さ１':u'small',    u'小さ２':u'x-small' }

    # Pangoタグを除去する
    reTagRemove = re.compile(ur'<[^>]*?>')

    # 青空タグを除去する
    reAozoraTagRemove = re.compile( ur'<aozora.+?>|</aozora>' )

    def __init__( self, chars=40, lines=25 ):
        ReaderSetting.__init__(self)
        AozoraScale.__init__(self)
        self.readcodecs = u'shift_jis'
        self.currentText = AozoraCurrentTextinfo()
        self.set_source()
        self.charsmax = self.currentText.chars - 1 # 最後の1文字は禁則処理用に確保

        # 単純な置換
        # 設定ファイルから変数を拾うため、ここに移動。
        self.dicAozoraTag = {
            u'［＃行右小書き］':u'<sup>',   u'［＃行右小書き終わり］':u'</sup>',
            u'［＃行左小書き］':u'<sub>',   u'［＃行左小書き終わり］':u'</sub>',
            u'［＃上付き小文字］':u'<sup>', u'［＃上付き小文字終わり］':u'</sup>',
            u'［＃下付き小文字］':u'<sub>', u'［＃下付き小文字終わり］':u'</sub>',
            u'［＃太字］':(u'<span font_desc="%s">' % self.get_value( "boldfontname" )),
            u'［＃ここから太字］':(u'<span font_desc="%s">' % self.get_value( "boldfontname" )),
            u'［＃斜体］':u'<span style="italic">',
            u'［＃ここから斜体］':u'<span style="italic">' ,
            u'［＃大きな文字終わり］':u'</span>',
            u'［＃ここで大きな文字終わり］':u'</span>',
            u'［＃小さな文字終わり］':u'</span>',
            u'［＃ここで小さな文字終わり］':u'</span>',
            u'［＃斜体終わり］':u'</span>',
            u'［＃ここで斜体終わり］':u'</span>',
            u'［＃太字終わり］':u'</span>',
            u'［＃ここで太字終わり］':u'</span>',
            u'［＃横組み］':u'<aozora yokogumi="dmy">',
            u'［＃ここから横組み］':u'<aozora yokogumi="dmy">',
            u'［＃横組み終わり］':u'</aozora>',
            u'［＃ここで横組み終わり］':u'</aozora>',
            u'［＃罫囲み］':u'<aozora keikakomigyou="0">',
            u'［＃罫囲み終わり］':u'</aozora>' }


    def set_source( self, s=u'', z=u'', w=0 ):
        """ 青空文庫ファイルをセット
        """
        self.currentText.sourcefile= s
        self.currentText.zipfilename = z
        self.currentText.worksid = w

    def get_form( self ):
        """ ページ設定を返す。
        """
        return (self.currentText.chars, self.currentText.pagelines)

    def mokuji_itre(self):
        """ 作成した目次のイテレータ。UI向け。
        """
        with file(self.currentText.mokujifile,'r') as f0:
            for s in f0:
                yield s.strip('\n')

    def __get_booktitle_sub( self, sourcefile=u'' ):
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
            sourcefile = self.currentText.sourcefile

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

    def romasuji(self, num):
        """ 10進数字文字列をローマ数字に変換する
            表せるのは 1〜3999 迄であることに注意
        """
        try:
            n = int(num)
            if n > 3999 or n < 1:
                # error
                return None
        except:
            return None

        if n >= 1 and n <=12:
            # 1 .. 12 は unicode １文字で返す
            return unichr(0x215F+n)

        rv = []
        s = [int(i) for i in u'%d' % n][::-1] # 反転
        for l in xrange(len(s)-1,-1,-1):
            if l == 0:
                rv.append((u'' if s[l] == 0 else unichr(0x215F+s[l])))
            elif l == 1:
                rv.append([u'',u'Ⅹ', u'ⅩⅩ',u'ⅩⅩⅩ',u'ⅩⅬ',
                            u'Ⅼ',u'ⅬⅩ',u'ⅬⅩⅩ',u'ⅬⅩⅩⅩ',u'ⅩⅭ'][s[l]])
            elif l == 2:
                rv.append([u'',u'Ⅽ',u'ⅭⅭ',u'ⅭⅭⅭ',u'ⅭⅮ',
                            u'Ⅾ',u'ⅮⅭ',u'ⅮⅭⅭ',u'ⅮⅭⅭⅭ',u'ⅭⅯ'][s[l]])
            elif l == 3:
                rv.append(u'Ⅿ'*s[l])
        return ''.join(rv)


    def __searchtag(self, s, pos=0):
        """ タグを見つけてその最初と終わりを返す
            見つからない場合は -1, -1
            タグが閉じていない場合は start, -1
            ネスティングに対応する
        """
        end = -1
        start = s.find(u'<',pos)
        while start != -1:
            pos = s.find(u'<',start+1)
            if pos == -1:
                end = s.find(u'>',start+1)
                if end != -1:
                    end += 1
                break
            else:
                start = pos
        return start, end

    def __removetag(self, sTmp):
        """ 文字列中に含まれるタグ（［＃］及び<>）を取り除く
        """
        # ［＃］
        tmp3 = self.reCTRL2.search(sTmp)
        while tmp3:
            sTmp = sTmp[:tmp3.start()]+sTmp[tmp3.end():]
            tmp3 = self.reCTRL2.search(sTmp)
        # <>
        s0, e0 = self.__searchtag(sTmp)
        while s0 != -1:
            sTmp = sTmp[:s0]+sTmp[e0:]
            s0, e0 = self.__searchtag(sTmp)
        return sTmp

    def __formater_pass1( self, sourcefile=u''):
        """ フォーマッタ（第1パス）
            formater より呼び出されるジェネレータ。1行読み込んでもっぱら
            置換処理を行う。

            開始／終了型タグの処理について
            ［＃タグ］本文［＃タグ終わり］で示されるタグについては、本文中に
            おける改行の有無について、青空文庫は仕様で明記していません。
            このため、とりあえず下記のように整理して処理を実装しています。

            改行が含まれる可能性があるもの（修飾される本文が複数行に及ぶ）
                傍点、傍線

            同一行で完結すると見込まれるもの
                縦中横、注記、左注記

                且つ複数行に及ぶ本文向けに同一機能のタグを別途用意しているもの
                    キャプション、見出し

                且つ特殊タグで明示されるもの
                    割り注　このタグでのみ用いられる［＃改行］が存在します。

            実装上の区別を要しないもの
                文字の大きさ

                且つ青空形式からxml形式への置換で完了するもの
                行右小書き、太字、左傍線など

        """
        def __dashsub(a):
            """ ２文字以上のDASHの連結の下請け
            """
            if a.group('name'):
                return u'<aozora dash="dmy">%s</aozora>' % a.group('name')
            return u''

        def __aozoratag_replace(a):
            """ 単純なPangoタグへの置換の下請け
            """
            if a.group() in self.dicAozoraTag:
                return self.dicAozoraTag[a.group()]
            return a.group()

        def __gaiji_replace(a):
            """ Shift-jis 未収録文字の置換
            """
            a2 = self.reGaiji3.match(a.group())
            if a2:
                # 外字置換（JIS第3、第4水準）
                k = jis3.sconv(a2.group('number'))
                if not k:
                    #logging.info( u'JIS未登録の外字を検出：%s' % a.group())
                    k = u'［'+a.group()[2:]
                return k

            a2 = self.reGaiji4.match(a.group())
            if a2:
                # 外字置換（Unicode文字）
                return unichr(int(a2.group('number'),16))

            a2 = self.reKogakiKatakana.match(a.group())
            if a2:
                #   小書き片仮名
                #   ヱの小文字など、JISにフォントが無い場合
                return u'<span size="smaller">%s</span>' % a2.group(u'name')

            a2 = self.reGaiji6.match(a.group())
            if a2:
                #   ローマ数字対策
                #   1 - 3999 迄
                return u'［＃縦中横］%s［＃縦中横終わり］' % self.romasuji(a2.group('num'))

            # JISにもUnicodeにも定義されていない文字の注釈
            # こちらで準備するか、そうでなければ
            # ※［＃「」、底本ページ-底本行］ -> ※「」
            a2 = self.reGaiji5.match(a.group())
            if a2:
                if a2.group(u'name') in self.dicReserveChar:
                    k = self.dicReserveChar[a2.group(u'name')]
                else:
                    k = a2.group(u'name').strip(u'「」')
                    #logging.info(u'未定義文字を検出 : %s' % k )
                    #loggingflag = True
                return k

            return u''

        """----------------------------------------------------------------
        """

        if not sourcefile:
            sourcefile = self.currentText.sourcefile

        headerflag = False          # 書名以降の注釈部分を示す
        boutoudone = False          # ヘッダ処理が終わったことを示す
        footerflag = False
        aozorastack = []            # ［＃形式タグ用のスタック

        posstack = []               # 開始/終了型タグ処理用スタック

        kansuuji = u'〇一二三四五六七八九'

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
                    aozorastack.append(lnbuf)
                    lnbuf = u''.join(aozorastack)
                    aozorastack = []

                """ 空行及び冒頭の処理
                """
                if not lnbuf:
                    if boutoudone:
                        yield u''
                    else:
                        boutoudone = True
                        yield u'［＃改ページ］'
                    continue

                """ アクセント分解 & を処理するので xml.sax より前に呼ぶこと
                """
                lnbuf = aozoraaccent.replace( lnbuf )

                """ tag 対策
                    pango で引っかかる & < > を 特殊文字に変換する
                """
                lnbuf = xml.sax.saxutils.escape( lnbuf )

                """ くの字の置換
                """
                lnbuf = self.reKunoji.sub( u'〳〵', lnbuf )
                lnbuf = self.reGunoji.sub( u'〴〵', lnbuf )

                """ 描画対策
                    dash の途切れ及び縦書きフォント無しを回避
                """
                lnbuf = self.reDash.sub(__dashsub, lnbuf)

                """ Shift-jis未定義の文字を得る
                """
                lnbuf = self.reCTRLGaiji.sub(__gaiji_replace, lnbuf)

                """ ルビにつくママ
                    ルビに変換する
                """
                tmp = self.reRubimama.search(lnbuf)
                while tmp:
                    #   ルビのママ
                    #   直前に出現するルビの末尾に付記する
                    tmpEnd = lnbuf.rfind(u'》',0,tmp.start())
                    if tmpEnd == -1:
                        # 修飾するルビがない場合
                        lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                    else:
                        lnbuf = u'%s%s》%s' % (
                            lnbuf[:tmpEnd], u'〔ルビママ〕',
                                                lnbuf[tmp.end():] )
                    tmp = self.reRubimama.search(lnbuf)

                """ ルビの処理
                    文字種が変わる毎にルビ掛かり始めとみなして、anchorを
                    セットする。
                """
                retline = []
                inRubi = False
                inTag = False
                pos = 0
                anchor = 0
                isSPanchor = False
                tp = u'...'
                for s in lnbuf:
                    # タグをスキップ
                    if inTag:
                        if s == u'>':
                            inTag = False
                    elif s == u'<':
                        inTag = True
                    elif s == u'｜':
                        isSPanchor = True
                        retline.append(lnbuf[anchor:pos])
                        anchor = pos + 1
                    elif s == u'《':
                        inRubi = True
                        rubiTop = pos
                    elif s == u'》':
                        inRubi = False
                        isSPanchor = False
                        retline.append(u'<aozora rubi="%s" length="%s">%s</aozora>' % (
                            lnbuf[rubiTop+1:pos],
                            self.__boutencount(self.reTagRemove.sub(u'', lnbuf[anchor:rubiTop])),#本文側長さ
                            lnbuf[anchor:rubiTop] ))
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
                                retline.append(lnbuf[anchor:pos])
                                anchor = pos
                    pos += 1
                retline.append(lnbuf[anchor:pos])
                lnbuf = u''.join(retline)

                """ 二重山括弧の代替に算術記号を使っているテキストが
                    あるので、その対策
                """
                lnbuf = lnbuf.replace(u'≫', u'》').replace(u'≪', u'《')

                """ 連続して出現する括弧類の送り量の調整
                """
                retline = []
                pos = 0
                anchor = 0
                end = len(lnbuf)
                inAozora = 0
                inTag = False
                while pos < end:
                    try:
                        if inTag:
                            if lnbuf[pos] == u'>':
                                inTag = False
                        elif lnbuf[pos] == u'<':
                            inTag = True
                        elif inAozora:
                            if lnbuf[pos] == u'］':
                                inAozora -= 1
                        elif lnbuf[pos:pos+2] == u'［＃':
                            inAozora += 1
                            pos += 1
                        elif lnbuf[pos] in self.kakko:
                            # 括弧類を検出
                            if lnbuf[pos] in u'、・' and pos > 0:
                                # 、・の場合は前後に漢数字があるか調べる
                                if kansuuji.find(lnbuf[pos-1]) != -1 and kansuuji.find(lnbuf[pos+1]) != -1:
                                    if lnbuf[pos] == u'・':
                                        retline.append(
                                            u'%s<aozora half="0.75">%s</aozora><aozora half="0.75">%s</aozora>' % (
                                                lnbuf[anchor:pos-1],
                                                lnbuf[pos-1],
                                                lnbuf[pos]))
                                    else:
                                        retline.append(
                                            u'%s<aozora half="0.5">%s</aozora>' % (
                                                lnbuf[anchor:pos], lnbuf[pos] ))
                                    pos += 1
                                    anchor = pos
                                    continue

                            if lnbuf[pos+1] in self.kakko and lnbuf[pos+1:pos+3] != u'［＃':
                                if not (lnbuf[pos] in self.hajimekakko and lnbuf[pos+1] in self.owarikakko):
                                    # 後ろにも括弧が続くか、且つタグの開始でないか
                                    # 但し開閉の順()で続く場合は調整しない。
                                    retline.append(
                                    u'%s<aozora half="0.5">%s</aozora>' % (lnbuf[anchor:pos], lnbuf[pos]))
                                    pos += 1
                                    anchor = pos
                                    continue
                    except IndexError:
                        pass
                    pos += 1
                retline.append(lnbuf[anchor:])

                lnbuf = u''.join(retline)

                """ フッタの検出
                """
                tmp = self.reFooter.search(lnbuf)
                if tmp:
                    footerflag = True
                    if tmp.group('type') == u'［＃本文終わり］':
                        lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]

                """ ［＃　で始まるタグの処理
                """

                """ 単純な Pango タグへの置換
                """
                lnbuf = self.reCTRL.sub( __aozoratag_replace, lnbuf )

                isRetry = False # タグが閉じなかった場合の再処理フラグ
                while True:
                    tmp = self.reCTRL2.search(lnbuf)
                    while tmp:
                        """ 縦中横
                        """
                        tmp2 = self.reTatenakayoko.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<aozora tatenakayoko="%s">%s</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ （類似処理のまとめ）
                        """
                        if tmp.group() == u'［＃縦中横］':
                            posstack.append(tmp.span())
                            posstack.append(tmp.group())
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        """ 縦中横（開始／終了型）
                            直後に閉じタグが出現すること　及び
                            複数行に及ぶことがないことを前提にフラグで処理する
                        """
                        """ 縦中横（開始／終了型）終わり
                        """
                        if tmp.group() == u'［＃縦中横終わり］':
                            if posstack[-1] != u'［＃縦中横］':
                                logging.error( u'%s を検出しましたがマッチしません。%s で閉じられています。' % (posstack[-1],tmp.group()) )
                            posstack.pop()
                            pos_start,pos_end = posstack.pop()
                            lnbuf = u'%s<aozora tatenakayoko="%s">%s</aozora>%s' % (
                                lnbuf[:pos_start],
                                lnbuf[pos_end:tmp.start()],
                                lnbuf[pos_end:tmp.start()],
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 注記（開始／終了型）
                            直後に閉じタグが出現すること　及び
                            複数行に及ぶことがないことを前提にフラグで処理する
                        """
                        if self.reChuki.match(tmp.group()):
                            posstack.append(tmp.span())
                            posstack.append(u'［＃注記］')
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        """ 注記（開始／終了型）終わり
                        """
                        tmp2 = self.reChukiowari.match(tmp.group())
                        if tmp2:
                            if posstack[-1] != u'［＃注記］':
                                logging.error( u'%s を検出しましたがマッチしません。%s で閉じられています。' % (posstack[-1],tmp.group()) )
                            posstack.pop()
                            pos_start,pos_end = posstack.pop()

                            sTmp = lnbuf[pos_end:tmp.start()]
                            lnbuf = u'%s<aozora rubi="〔%s〕" length="%d">%s</aozora>%s' % (
                                lnbuf[:pos_start],
                                tmp2.group('name'), len(sTmp),
                                sTmp.strip(u'〔〕'),
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 左注記（開始／終了型）
                            直後に閉じタグが出現すること　及び
                            複数行に及ぶことがないことを前提にフラグで処理する
                        """
                        if self.reLeftrubi2.match(tmp.group()):
                            posstack.append(tmp.span())
                            posstack.append(u'［＃左注記］')
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        """ 左注記（開始／終了型）終わり
                        """
                        tmp2 = self.reLeftrubi2owari.match(tmp.group())
                        if tmp2:
                            if posstack[-1] != u'［＃左注記］':
                                logging.error( u'%s を検出しましたがマッチしません。%s で閉じられています。' % (posstack[-1],tmp.group()) )
                            posstack.pop()
                            pos_start,pos_end = posstack.pop()
                            sTmp = lnbuf[pos_end:tmp.start()]
                            lnbuf = u'%s<aozora leftrubi="%s" length="%d">%s</aozora>%s' % (
                                lnbuf[:pos_start],
                                tmp2.group('name'), len(sTmp),
                                sTmp,
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 割り注
                            同一行内に割り注終わりが存在するはず
                        """
                        if self.reWarichu.match(tmp.group()):
                            posstack.append(tmp.span())
                            posstack.append(u'［＃割り注］')
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        """ 割り注終わり
                        """
                        tmp2 = self.reWarichuOwari.match(tmp.group())
                        if tmp2:
                            if posstack[-1] != u'［＃割り注］':
                                logging.error( u'%s を検出しましたがマッチしません。%s で閉じられています。' % (posstack[-1],tmp.group()) )
                            posstack.pop()
                            pos_start,pos_end = posstack.pop()

                            sTmp = lnbuf[pos_end:tmp.start()]
                            if sTmp.find(u'<aozora') != -1 or sTmp.find(u'<span') != -1:
                                # 本文にタグを検出した場合、割り注を放棄する
                                lnbuf = u'%s%s%s' % (
                                    lnbuf[:pos_start],
                                    sTmp,
                                    lnbuf[tmp.end():] )
                            else:
                                # 割り注表示部分の高さを求める
                                if sTmp.find(u'［＃改行］') == -1:
                                    # 改行位置が明示されていなければ、全長の半分
                                    l = int(math.ceil(len(sTmp)/2.))
                                else:
                                    # 明示されていれば長いほうとする
                                    l = 0
                                    for s0 in sTmp.split(u'［＃改行］'):
                                        if len(s0) > l:
                                            l = len(s0)
                                lnbuf = u'%s<aozora warichu="%s" height="%d">%s</aozora>%s' % (
                                    lnbuf[:pos_start], sTmp, l,
                                    u'　' * int(math.ceil(
                                        l * self.fontmagnification(u'size="smaller"'))),
                                    lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 挿図（キャプション付き他、独立段落）
                            次段で処理する
                            reFigで分離できないのでここでトラップする
                        """
                        if self.reFig2.match(tmp.group()):
                        #tmp2 = self.reFig2.match(tmp.group())
                        #if tmp2:
                            tmp = self.reCTRL2.search(lnbuf,tmp.end())
                            continue

                        """ 挿図（段落内挿入）
                            拡大・縮小は行わない
                        """
                        tmp2 = self.reFig.match(tmp.group())
                        if tmp2:
                            try:
                                fname = tmp2.group(u'filename')
                                tmpPixBuff = gtk.gdk.pixbuf_new_from_file(
                                    os.path.join(self.currentText.aozoratextdir, fname))
                                figheight = tmpPixBuff.get_height()
                                figwidth = tmpPixBuff.get_width()
                                if figwidth > self.currentText.canvas_linewidth * 2:
                                    # 大きな挿図(幅が2行以上ある)は独立表示へ変換する
                                    #sNameTmp = u'［＃「＃＃＃＃＃」のキャプション付きの図（%s、横%d×縦%d）入る］' % (
                                    lnbuf = u'%s［＃「＃＃＃＃＃」のキャプション付きの図（%s、横%d×縦%d）入る］%s' % (
                                            lnbuf[:tmp.start()], fname, figwidth, figheight, lnbuf[tmp.end():])
                                    del tmpPixBuff
                                    #lnbuf = lnbuf[:tmp.start()] + sNameTmp + lnbuf[tmp.end():]
                                    tmp = self.reCTRL2.search(lnbuf)
                                    continue

                                # 図の高さに相当する文字列を得る
                                sPad = u'＃' * int(math.ceil(
                                    float(figheight)/float(self.currentText.get_value('fontheight'))))
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

                        """ 横組み
                        """
                        tmp2 = self.reYokogumi.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<aozora yokogumi="dmy">%s</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                            lnbuf[tmpStart:tmpEnd],
                                            lnbuf[tmpEnd:tmp.start()],
                                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 左注記あるいは左ルビ
                        """
                        tmp2 = self.reLeftrubi.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name'))
                            tmprubi = tmp2.group(u'rubi')
                            if tmp2.group(u'type') != u'ルビ':
                                 if not (tmprubi[0] in self.hajimekakko and tmprubi[-1] in self.owarikakko):
                                    # 注記であることを示すため亀甲括弧を付すが、
                                    # 注記の両端に括弧類がある場合はくどいので付さない
                                    tmprubi = u'〔%s〕' % tmp2.group(u'rubi')
                            lnbuf = u'%s<aozora leftrubi="%s" length="%s">%s</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                        tmprubi,
                                        len(tmp2.group(u'name')),
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf,tmpStart)
                            continue

                        """ 底本注記を左注釈として表示
                            但し、ルビについては省略
                        """
                        tmp2 = self.reTeibon.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name'))
                            if tmp2.group(u'rubi'):
                                # ルビに対する注記は表示しない（できない）
                                lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                                tmp = self.reCTRL2.search(lnbuf)
                            else:
                                # <>による修飾は抜去される
                                lnbuf = u'%s<aozora leftrubi="〔底本では%s〕" length="%d">%s</aozora>%s%s' % (
                                        lnbuf[:tmpStart],
                                        self.reTagRemove.sub(u'', tmp2.group(u'name2')),
                                        len(self.reTagRemove.sub(u'', tmp2.group(u'name'))),
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                        lnbuf[tmp.end():] )
                                tmp = self.reCTRL2.search(lnbuf, tmpStart)
                            continue

                        """ 文字の大きさ
                            文字の大きさ２　と互換性がないので、こちらを
                            先に処理すること
                        """
                        tmp2 = self.reMojisize.match(tmp.group())
                        if tmp2:
                            sNameTmp = tmp2.group(u'name') + tmp2.group(u'size')
                            try:
                                sSizeTmp = self.dicMojisize[sNameTmp]
                            except KeyError:
                                sSizeTmp = u'xx-small' if sNameTmp[:2] == u'小さ' else u'xx-large'

                            tmpStart,tmpEnd = self.__honbunsearch(
                                            lnbuf[:tmp.start()],tmp2.group(u'name2'))
                            lnbuf = u'%s<span size="%s">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            sSizeTmp,
                                                lnbuf[tmpStart:tmpEnd],
                                                lnbuf[tmpEnd:tmp.start()],
                                                    lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 文字の大きさ２
                            開始／終了型　及び　ブロック修飾兼用
                            文字の大きさ　と互換性がない（誤検出する）ので、
                            こちらを後に処理すること
                            閉じタグは</span>に単純置換される
                        """
                        tmp2 = self.reMojisize2.match(tmp.group())
                        if tmp2:
                            sNameTmp = tmp2.group(u'name') + tmp2.group(u'size')
                            try:
                                sSizeTmp = self.dicMojisize[sNameTmp]
                            except KeyError:
                                sSizeTmp = u'xx-small' if sNameTmp[:2] == u'小さ' else u'xx-large'

                            lnbuf = u'%s<span size="%s">%s' % (
                                lnbuf[:tmp.start()], sSizeTmp, lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 傍点・傍線
                        """
                        tmp2 = self.reBouten.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<aozora %s%s="%s%s">%s</aozora>%s%s' % (
                                lnbuf[:tmpStart],
                                u'' if not tmp2.group('position') else u'left',
                                u'bouten' if tmp2.group('type2') == u'傍点' else u'bousen',
                                tmp2.group('type'),        tmp2.group('type2'),
                                lnbuf[tmpStart:tmpEnd],
                                lnbuf[tmpEnd:tmp.start()], lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 傍点・傍線
                            開始／終了型
                        """
                        tmp2 = self.reBouten2.match(tmp.group())
                        if tmp2:
                            # ［＃傍点］
                            aozorastack.append(tmp.group())
                            lnbuf = u'%s<aozora %s="%s">%s' % (
                                lnbuf[:tmp.start()],
                                u'bousen' if not tmp2.group('position') else u'leftbousen',
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

                        """ 行右小書き・上付き小文字、行左小書き・下付き小文字
                            pango のタグを流用
                        """
                        tmp2 = self.reGyomigikogaki.match(tmp.group())
                        if tmp2:
                            sNameTmp = tmp2.group(u'name')
                            #reTmp = re.compile( ur'%s$' % sNameTmp )
                            # lnbuf[:tmp.start()] の終わりにある修飾対象文字を
                            # 取り除くのに正規表現を使いたいのだが、()[]等が
                            # 含まれているとエラーになるので、文字列置換で代替
                            # している。終わり部分だけ取り除けば良いので、
                            # [::-1]で一度ひっくり返して一回だけ''に置換している。
                            lnbuf = u'%s%s%s' % (
                                #reTmp.sub( u'', lnbuf[:tmp.start()] ),
                                lnbuf[:tmp.start()][::-1].replace( sNameTmp[::-1], u'',1)[::-1],
                                u'<sup>%s</sup>' % tmp2.group(u'name') if tmp2.group(u'type') == u'行右小書き' or \
                                    tmp2.group('type') == u'上付き小文字' else u'<sub>%s</sub>' % tmp2.group(u'name'),
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 太字
                            pango のタグを流用
                        """
                        tmp2 = self.reFutoji.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span font_desc="%s">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            self.get_value("boldfontname"),
                                            lnbuf[tmpStart:tmpEnd],
                                            lnbuf[tmpEnd:tmp.start()],
                                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 斜体
                            pango のタグを流用
                        """
                        tmp2 = self.reSyatai.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                    lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<span style="italic">%s</span>%s%s' % (
                                        lnbuf[:tmpStart],
                                            lnbuf[tmpStart:tmpEnd],
                                            lnbuf[tmpEnd:tmp.start()],
                                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 訓点送り仮名
                            pango のタグを流用
                        """
                        tmp2 = self.reKuntenOkuri.match(tmp.group())
                        if tmp2:
                            lnbuf = u'%s<sup>%s</sup>%s' % (
                                lnbuf[:tmp.start()],
                                    tmp2.group(u'name'),
                                        lnbuf[tmp.end():])
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 返り点
                            pango のタグを流用
                        """
                        tmp2 = self.reKaeriten.match(tmp.group())
                        if tmp2:
                            lnbuf = u'%s<sub>%s</sub>%s' % (
                                lnbuf[:tmp.start()],
                                    tmp2.group(u'name'),
                                        lnbuf[tmp.end():])
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 注記 及び ママ註記
                        """
                        tmp2 = self.reMama.match(tmp.group())
                        if tmp2:
                            sNameTmp = tmp2.group(u'name')
                            #reTmp = re.compile( ur'%s$' % sNameTmp )
                            tmprubipos = sNameTmp.find(u'rubi="')
                            if tmprubipos != -1:
                                # 親文字にルビタグが含まれる場合は結合する
                                # 本文側の修飾対象を正規表現で削除しようと
                                # すると、\によるエスケープが必要になる
                                # 場合があるので、replaceに変更。末尾側から
                                # 一つだけ削除するので [::-1]で反転している。
                                tmprubipos2 = sNameTmp[tmprubipos+6:].find(u'"')
                                lnbuf = u'%s%s%s%s%s' % (
                                    #reTmp.sub( u'', lnbuf[:tmp.start()]),
                                    lnbuf[:tmp.start()][::-1].replace(sNameTmp[::-1],u'',1)[::-1],
                                    sNameTmp[:tmprubipos+6+tmprubipos2],
                                    u'〔ママ〕' if tmp2.group('type').find(u'ママ') != -1 else u'',
                                    sNameTmp[tmprubipos+6+tmprubipos2:],
                                    lnbuf[tmp.end():])
                            else:
                                sNameTmp2 = tmp2.group('type') if not tmp2.group(u'mama') else tmp2.group(u'mama')
                                lnbuf = u'%s<aozora rubi="〔%s〕" length="%d">%s</aozora>%s' % (
                                    #reTmp.sub( u'', lnbuf[:tmp.start()]),
                                    lnbuf[:tmp.start()][::-1].replace(sNameTmp[::-1],u'',1)[::-1],
                                    sNameTmp2.strip(u'（〔〕）'), len(sNameTmp),
                                    sNameTmp, lnbuf[tmp.end():] )

                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 罫囲み
                        """
                        tmp2 = self.reKeikakomiGyou.match(tmp.group())
                        if tmp2:
                            tmpStart,tmpEnd = self.__honbunsearch(
                                    lnbuf[:tmp.start()],tmp2.group(u'name'))
                            lnbuf = u'%s<aozora keikakomigyou="0">%s</aozora>%s%s' % (
                                    lnbuf[:tmpStart],
                                        lnbuf[tmpStart:tmpEnd],
                                        lnbuf[tmpEnd:tmp.start()],
                                            lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 見出し
                            ここでは正確なページ番号が分からないので、
                            見出し出現のフラグだけ立てて、目次作成は後段で行う。
                            ここでは複数行見出しはサポートしない
                        """
                        tmp2 = self.reMidashi.match(tmp.group())
                        if tmp2:
                            # 1行見出し
                            self.inMidashi = True
                            self.sMidashiSize = tmp2.group('midashisize')
                            self.midashi = tmp2.group(u'midashi')
                            tmpStart,tmpEnd = self.__honbunsearch(
                                    lnbuf[:tmp.start()],self.midashi)
                            lnbuf = u'%s<span face="%s"%s>%s</span>%s%s' % (
                                lnbuf[:tmpStart],
                                self.get_value("boldfontname"),
                                u' size="larger"' if self.sMidashiSize == u'大' else u'',
                                lnbuf[tmpStart:tmpEnd],
                                lnbuf[tmpEnd:tmp.start()],
                                lnbuf[tmp.end():] )
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        """ 見出し(開始／終了型)
                            ここでは正確なページ番号が分からないので、
                            見出し出現のフラグだけ立てて、目次作成は後段で行う。
                        """
                        if self.reMidashi2.match(tmp.group()):
                            # ［＃見出し］
                            self.inMidashi = True
                            self.midashi = u''
                            posstack.append(tmp.span())
                            posstack.append(u'［＃見出し］')
                            tmp = self.reCTRL2.search(lnbuf, tmp.end())
                            continue

                        tmp2 = self.reMidashi2owari.match(tmp.group())
                        if tmp2:
                            # ［＃見出し終わり］
                            if posstack[-1] != u'［＃見出し］':
                                logging.error( u'%s を検出しましたがマッチしません。%s で閉じられています。' % (posstack[-1],tmp.group()) )
                            posstack.pop()
                            pos_start,pos_end = posstack.pop()
                            #   目次用にタグを外す
                            self.midashi = self.__removetag(lnbuf[pos_end:tmp.start()])
                            self.sMidashiSize = tmp2.group('midashisize')

                            lnbuf = u'%s<span face="%s"%s>%s</span>%s' % (
                                lnbuf[:pos_start],
                                self.get_value("boldfontname"),
                                u' size="larger"' if self.sMidashiSize == u'大' else u'',
                                lnbuf[pos_end:tmp.start()],
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
                    ln = []
                    priortail = 0
                    for tmp in self.reNenGetsuNichi.finditer(lnbuf):
                        ln.append(lnbuf[priortail:tmp.start()])
                        priortail = tmp.end()
                        for s in tmp.group():
                            try:
                                ln.append(u'〇一二三四五六七八九'[eval(s)])
                            except:
                                ln.append(s)
                    ln.append(lnbuf[priortail:])
                    lnbuf = u''.join(ln)

                """ ダブルクォーテーションのノノカギへの置換
                    クォーテーションで括られた内容を調べて
                    Lo (Other_Letter)を日本語と見做して置換する。
                """
                for tmp in self.reNonokagi.finditer(lnbuf):
                    inTag = False
                    for s in tmp.group('name'):
                        if inTag:
                            if s == u'>':
                                inTag = False
                        elif s == u'<':
                            # tag を読み飛ばす
                            inTag = True
                        elif unicodedata.category(s) == 'Lo':
                            lnbuf = '%s〝%s〟%s' % (
                                 lnbuf[:tmp.start()],
                                tmp.group('name'),
                                lnbuf[tmp.end():] )
                            break

                """ 処理の終わった行を返す
                """
                yield lnbuf #+ u'\n'

        """ 最初の1ページ目に作品名・著者名を左右中央で表示するため、
            最初に［＃ページの左右中央］を出力している。最初の空行出現時に
            これを閉じている。
            このため、冒頭からまったく空行のないテキストだと、本文処理に遷移
            しないまま処理が終了してしまう。そのためここで出力する。
            なお、副作用として目次は作成されない。
        """
        if not boutoudone:
            yield u'［＃改ページ］'

    def __boutencount(self, honbun):
        """ 本文を遡って傍点の打込位置を探し、キャラクタ数を返す
        """
        c = 0
        pos = len(honbun) - 1
        inRubi = False
        inTag = 0
        inAtag = 0
        while pos >= 0:
            if honbun[pos] == u'｜':
                break
            elif inAtag:
                if honbun[pos:pos+2] == u'［＃':
                    inAtag -= 1
            elif honbun[pos] == u'］':
                inAtag += 1
            elif inTag:
                if honbun[pos] == u'<':
                    inTag -= 1
            elif honbun[pos] == u'>':
                inTag += 1
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

    def __honbunsearch(self, honbun, name):
        """ 本文を遡って name を検索し、その出現範囲を返す。
            name との比較に際して
                <tag></tag>、［＃］は無視される。
            但し、name 自体に <tag></tag>や［＃］を含む場合は
            比較対象とする

            比較は行末から行頭に向かって行われることに注意。
            見つからなければ start とend に同じ値を返す。
            これを配列添字に使えばヌル文字となる。

            name が hoge の場合
            <span>hoge</span>
            ^start           ^end
        """
        start = -1
        end = -1
        l = len(name)
        pos = len(honbun)
        inTag = False
        inAtag = False
        tagstack = []

        TagEnable = True if name.find(u'<') == -1 else False
        AtagEnable = True if name.find(u'［＃') == -1 else False

        while l > 0 and pos > 0:
            pos -= 1
            if inAtag:
                if honbun[pos:pos+2] == u'［＃':
                    inAtag = False
            elif AtagEnable and honbun[pos] == u'］':
                inAtag = True
            elif inTag:
                if honbun[pos] == u'<':
                    inTag = False
                    if honbun[pos:pos+2] == u'</':
                        # 閉じタグの場合はスタックに保存する
                        tagstack.append(pos)
                    else:
                        # タグの場合はスタックを減ずる
                        if tagstack != []:
                            postmp = tagstack.pop()
                        if end < postmp:
                            # 照合が閉じタグの前から始まっていたら拡張する
                            if end != -1:
                                end = honbun.find(u'>', postmp)

            elif TagEnable and honbun[pos] == u'>':
                inTag = True
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

        if tagstack != [] and start >= 0:
            # 閉じタグのみを検出した場合は、上流にタグがあるものとして
            # 文字列を拡張する
            try:
                pos = start
                while tagstack != []:
                    pos = honbun.rfind(u'>',0,pos)
                    if pos != -1:
                        pos = honbun.rfind(u'<',0,pos)
                        if pos != -1:
                            if honbun[pos:pos+2] == u'</':
                                tagstack.append(pos)
                            else:
                                l = honbun.find(u'>',tagstack.pop())
                                if l > end:
                                    # 閉じタグ終端へ拡張する
                                    end = l
                            continue
                    raise IndexError
                start = pos
            except IndexError:
                logging.error( "閉じられていないタグを検出  %s" % honbun )

        return (start,end+1)

    def formater(self, output_file=u'', mokuji_file=u''):
        """ フォーマッタ
        """

        def __insertfig(tag, lines):
            """ 挿図出力の下請け
                図の挿入に際しては、事前に改行を送り込んで表示領域を取得する必要が
                あるため、ここにまとめる。
            """
            if self.linecounter + lines >= self.currentText.pagelines:
                # 画像がはみ出すようなら改ページする
                while not self.__write2file(dfile, '\n'):
                    pass
            while lines > 0:
                self.__write2file(dfile, '\n')
                lines -= 1
            self.__write2file(dfile, tag)

        if output_file:
            self.destfile = output_file
        if mokuji_file:
            self.mokujifile = mokuji_file

        (self.currentText.booktitle, self.currentText.bookauthor) = self.__get_booktitle_sub()
        logging.info( u'****** %s ******' % self.currentText.sourcefile)

        with file(self.currentText.destfile, 'w') as fpMain, file(self.currentText.mokujifile, 'w') as self.mokuji_f:
            dfile = fpMain                      # フォーマット済出力先
            self.pagecenterflag = False         # ページ左右中央用フラグ
            self.countpage = True               # ページ作成フラグ
            self.linecounter = 0                # 出力した行数
            self.currentText.pagecounter = 0    # 出力したページ数
            self.currentText.currentpage=[] # フォーマット済ファイルにおける各ページの絶対位置
            self.currentText.currentpage.append(dfile.tell())  # 1頁目のファイル位置を保存
            self.midashi = u''
            self.inMidashi = False
            self.inFukusuMidashi = False        # 複数行におよぶ見出し
            self.FukusuMidashiOwari = False     # 複数行におよぶ見出しの終わり
            self.loggingflag = False            # デバッグ用フラグ、ページ数用
            self.tagstack = []                  # 書式引き継ぎ用

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
            isNoForming = False                 # 行の整形を抑止する

            figstack = []                       # 画像用スタック
            figcapcount = 0                     # 挿図からキャプションまでの行数を保持

            for lnbuf in self.__formater_pass1():
                lnbuf = lnbuf.rstrip('\n')
                yield

                """ 挿図が出現中
                """
                if figstack:
                    figcapcount += 1
                    if not lnbuf:
                        # 空行であれば挿図して終わる
                        a = figstack.pop()
                        __insertfig(a[0]+'\n',a[1])
                        figcapcount = 0
                        continue

                """ 空行の処理
                """
                if not lnbuf: #len(lnbuf) == 0:
                    self.__write2file( dfile, '\n' )
                    continue

                """ 制御文字列の処理
                    読み込んだ行に含まれる［＃.*?］を全てチェックする。
                    タグより前方を参照するタグは取り扱わない。
                """
                IndentJitsuki = False
                tmp = self.reCTRL2.search(lnbuf)
                while tmp:
                    """ 挿図
                        キャンバスの大きさに合わせて画像を縮小する。
                        ページからはみ出るようであれば挿図前に改ページする。
                        挿図タグは単独で出現することを前提とする。即ち、同一行中に他の
                        テキストを持たない。
                        描画はキャプションの出現まで保留される。
                    """
                    matchFig = self.reFig.match(tmp.group())
                    if matchFig:
                        if figstack:
                            # 挿図が連続する場合等、未出力の挿図がある場合はここで描画する
                            a = figstack.pop()
                            __insertfig(a[0], a[1])
                            figcapcount = 0

                        try:
                            fname = matchFig.group(u'filename')
                            tmpPixBuff = gtk.gdk.pixbuf_new_from_file(
                                os.path.join(self.currentText.aozoratextdir, fname))
                            figheight = tmpPixBuff.get_height()
                            figwidth = tmpPixBuff.get_width()
                            del tmpPixBuff
                        except gobject.GError:
                            # ファイルI/Oエラー
                            self.loggingflag = True
                            logging.info(
                                u'画像ファイル %s の読み出しに失敗しました。' % fname )
                            lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                            tmp = self.reCTRL2.search(lnbuf)
                            continue

                        tmpH = float(self.currentText.get_value(u'scrnheight')) - \
                                float(self.currentText.get_value(u'bottommargin')) - \
                                        float(self.currentText.get_value(u'topmargin'))
                        tmpW = float(self.currentText.get_value(u'scrnwidth')) - \
                                float(self.currentText.get_value(u'rightmargin')) - \
                                        float(self.currentText.get_value(u'leftmargin'))

                        # 表示領域に収まるような倍率を求める
                        # 高さはキャプション表示領域分を考慮して0.8, 幅はあふれた場合を
                        # 考慮して0.9程度の定数を乗じている。
                        tmpRasio = min(
                                    min((tmpH / figheight)*0.8, (tmpW / figwidth)*0.9),
                                    1.0)
                        # 画像幅をピクセルから行数に換算する
                        # ここで改行しないことに注意。改行はキャプションで行う。
                        figstack.append((u'<aozora img2="%s" width="%s" height="%s" rasio="%0.2f"> </aozora>' % (
                                        fname, figwidth, figheight, tmpRasio),
                                        int(round(figwidth*tmpRasio / float(self.currentText.canvas_linewidth)))) )
                        figcapcount = 0
                        lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                        tmp = self.reCTRL2.search(lnbuf)
                        continue

                    """ キャプション
                        挿図の直下に横書きで表示する。キャプション出現中は行の分割及び
                        ページカウントは抑止される。
                    """
                    tmp2 = self.reCaption.match(tmp.group())
                    if tmp2:
                        tmpStart,tmpEnd = self.__honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                        # 直前に挿図があるかチェックする。もし、挿図が無ければこのキャプションは
                        # 無視される。
                        if figstack:
                            a = figstack.pop()
                            __insertfig(a[0], a[1])
                            self.countpage = False
                            self.__write2file(dfile,
                                    u'<aozora caption="dmy">%s</aozora>\n' %
                                        self.reAozoraTagRemove.sub(u'',lnbuf[tmpStart:tmpEnd]))
                            self.countpage = True
                        lnbuf = u'%s%s' % (lnbuf[:tmpStart], lnbuf[tmp.end():])
                        figcapcount = 0
                        tmp = self.reCTRL2.search(lnbuf,tmpStart)
                        continue

                    """ キャプション（開始/終了型）
                        同一行中に閉じられることを期待して
                        挿図の直下に横書きで表示する。キャプション出現中は行の分割及び
                        ページカウントは抑止される。
                    """
                    if tmp.group() == u'［＃キャプション］':
                        tmp = self.reCaption2.search(lnbuf)
                        if tmp:
                            # 直前に挿図があるかチェックする。もし、挿図が無ければこのキャプションは
                            # 無視される。
                            if figstack:
                                # 行の分割を回避するため、結果を直接書き出す。
                                a = figstack.pop()
                                __insertfig(a[0], a[1])
                                self.countpage = False
                                self.__write2file(dfile,
                                    u'<aozora caption="dmy">%s</aozora>\n' %
                                        self.reAozoraTagRemove.sub(u'',tmp.group(u'name')))
                                self.countpage = True
                            lnbuf = u'%s%s' % (lnbuf[:tmp.start()], lnbuf[tmp.end():])
                        else:
                            # [＃キャプション終わり]で閉じていなければ、捨てて終わる
                            if figstack:
                                figstack.pop()
                            lnbuf = u'%s%s' % (lnbuf[:tmp.start()], lnbuf[tmp.end():])
                        figcapcount = 0
                        tmp = self.reCTRL2.search(lnbuf)
                        continue

                    """ 複数行に及ぶキャプション
                        行の整形を抑止し、出力先を一時ファイルに
                        切り替える。
                        挿図の直下に横書きで表示する。キャプション出現中は行の分割及び
                        ページカウントは抑止される。
                    """
                    if tmp.group() == u'［＃ここからキャプション］':
                        # キャプションの完成を待たないで取り敢えず挿図を行う
                        if figstack:
                            a = figstack.pop()
                            __insertfig(a[0], a[1])
                            figcapcount = 0

                        # カレントハンドルを退避して、一時ファイルを作成して出力先を切り替える。
                        workfilestack.append(dfile)
                        dfile = tempfile.NamedTemporaryFile(mode='w+',delete=True)
                        # 一時ファイル使用中はページカウントしない
                        self.countpage = False
                        # 行の整形を抑止
                        isNoForming = True
                        lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                        tmp = self.reCTRL2.search(lnbuf)
                        continue

                    if tmp.group() == u'［＃ここでキャプション終わり］':
                        # 一時ファイルに掃き出されたキャプションを結合
                        sTmp = u''
                        dfile.seek(0)
                        for sCenter in dfile:
                            sTmp += sCenter.rstrip(u'\n') # +u'\\n'
                        if tmp.start() > 0:
                            # 青空文庫の揺らぎへの対策
                            # このタグは本来行頭に置かれる（単独で出現する）べきものだが、
                            # キャプションの行末に置かれているテキストがあり、その場合は
                            # レイアウトが崩れるため、それをここで回避する。
                            sTmp += lnbuf[:tmp.start()]

                        # 出力先を復元
                        dfile.close()
                        dfile = workfilestack.pop()
                        # 行の整形を再開
                        isNoForming = False
                        # キャプション
                        self.__write2file(dfile,
                                u'<aozora caption="dmy">%s</aozora>\n' % self.reAozoraTagRemove.sub(u'',sTmp))

                        lnbuf = u'%s%s' % (lnbuf[:tmp.start()], lnbuf[tmp.end():])
                        tmp = self.reCTRL2.search(lnbuf)
                        # ページカウントを再開
                        self.countpage = True
                        continue

                    #
                    if figstack:
                        a = figstack.pop()
                        __insertfig(a[0]+'\n', a[1])

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

                    """ 改ページ・改丁・改段
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
                            iCenter = self.currentText.pagelines
                            for sCenter in dfile:
                                iCenter -= 1
                            while iCenter > 1:
                                self.__write2file(workfilestack[-1], '\n')
                                iCenter -= 2
                            # 一時ファイルの内容を、退避してあるハンドル先へ
                            # コピーする
                            dfile.seek(0)
                            iCenter = 0
                            for sCenter in dfile:
                                self.__write2file(workfilestack[-1], sCenter)
                            dfile.close()
                            dfile = workfilestack.pop()

                        if self.linecounter != 0:
                            # ページ先頭に出現した場合は改ページしない
                            while not self.__write2file(dfile, '\n'):
                                pass
                        lnbuf = lnbuf[:tmp.start()]+lnbuf[tmp.end():]
                        tmp = self.reCTRL2.search(lnbuf)
                        continue

                    """ 見出し(複数行に及ぶ可能性の有る)
                        ここでは正確なページ番号が分からないので、
                        見出し出現のフラグだけ立てて、目次作成は後段で行う。
                    """
                    matchMidashi = self.reMidashi3.match(tmp.group())
                    if matchMidashi:
                        print u'Debug %s' % matchMidashi.group('type')
                        # ［＃ここから見出し］
                        self.sMidashiSize = matchMidashi.group('midashisize')
                        self.inMidashi = True
                        self.inFukusuMidashi = True
                        self.midashi = u''

                        if matchMidashi.group('type') == u'窓':
                            lnbuf = u'%s<aozora mado="dmy" font="%s" size="%s">%s' % (
                                lnbuf[:tmp.start()],
                                self.get_value("boldfontname"),
                                u' size="larger"' if self.sMidashiSize == u'大' else u'',
                                lnbuf[tmp.end():] )

                        else:
                            lnbuf = u'%s<span face="%s"%s>%s' % (
                                lnbuf[:tmp.start()],
                                self.get_value("boldfontname"),
                                u' size="larger"' if self.sMidashiSize == u'大' else u'',
                                lnbuf[tmp.end():] )

                        tmp = self.reCTRL2.search(lnbuf)
                        continue

                    matchMidashi = self.reMidashi3owari.match(tmp.group())
                    if matchMidashi:
                        # ［＃ここで見出し終わり］
                        self.FukusuMidashiOwari = True
                        self.sMidashiSize = matchMidashi.group('midashisize')

                        if matchMidashi.group('type') == u'窓':
                            lnbuf = u'%s</aozora>%s' % (
                                lnbuf[:tmp.start()], lnbuf[tmp.end():] )
                        else:
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

                    """ ここから地付き
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
                        lnbuf = u'%s<aozora keikakomi="start"></aozora>%s' % (
                            lnbuf[:tmp.start()], lnbuf[tmp.end():] )
                        tmp = self.reCTRL2.search(lnbuf)
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
                        if iCenter < self.currentText.pagelines:
                            # 罫囲みが次ページへまたがる場合は改ページする。
                            # 但し、１ページを越える場合は無視する。
                            if self.linecounter + iCenter >= self.currentText.pagelines:
                                while not self.__write2file(workfilestack[-1], '\n' ):
                                    pass

                        # 一時ファイルからコピー
                        dfile.seek(0)
                        iCenter = 0
                        for sCenter in dfile:
                            self.__write2file(workfilestack[-1], sCenter)
                        dfile.close()
                        dfile = workfilestack.pop()
                        lnbuf = u'%s<aozora keikakomi="end"></aozora>%s' % (
                            lnbuf[:tmp.start()], lnbuf[tmp.end():] )
                        tmp = self.reCTRL2.search(lnbuf)
                        continue

                    """ 割り注内で使われる特殊タグをいかす
                    """
                    if tmp.group() == u'［＃改行］':
                        tmp = self.reCTRL2.search(lnbuf, tmp.end())
                        continue

                    """ 未定義タグ
                        本文より抜去してログへ書き出す。
                    """
                    if tmp:
                        logging.info(u'未定義のタグを検出： %s' % tmp.group().strip(u'［＃］'))
                        loggingflag = True
                        lnbuf = lnbuf[:tmp.start()] + lnbuf[tmp.end():]
                        tmp = self.reCTRL2.search(lnbuf)


                if isNoForming:
                    """ 行の折り返し・分割処理を無視してファイルに出力する
                    """
                    # 未出力の挿図があればバッファへ出力する
                    if figcapcount:
                        if figstack:
                            a = figstack.pop()
                            __insertfig(a[0]+'\n', a[1])
                            figcapcount = 0

                    self.__write2file(dfile, "%s\n" % lnbuf)
                    continue



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
                            #if lenP >= currchars:
                            if lenP >= self.charsmax:
                                # 地付きする文字列の前に１行以上の長さが残って
                                # いる場合はそのまま分割処理に送る。
                                currchars = self.charsmax
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
                    self.ls, lnbuf = self.__linesplit(lnbuf, currchars)

                    """ 未出力の挿図があればバッファへ出力する
                    """
                    if figcapcount:
                        if figstack:
                            a = figstack.pop()
                            __insertfig(a[0]+'\n', a[1])
                            figcapcount = 0

                    """ 行をバッファ(中間ファイル)へ掃き出す
                    """
                    self.__write2file(dfile, "%s\n" % self.ls)

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

    def __linesplit(self, sline, smax=0.0):
        """ 文字列を分割する
            禁則処理、行末におけるルビ及び挿入画像の分ち書きの調整も行う。
            sline   : 本文
            smax    : 1行における文字数（全角文字を1文字とした換算数）
        """
        lcc = 0.0           # 全角１、半角0.5で長さを積算
        inTag = False       # <tag>処理のフラグ
        sTestCurrent = []   # sline を分割しながら格納
        sTestNext = []      # 〃（次行先頭部分）
        fLenCurrent = []    # 文字の画面上の長さ（全角を１とする比）
        adjCurrent = []     # 文字間隔調整可能文字位置を保持する

        fontsizename = u'normal'
        reAozoraWarichu = re.compile(ur'<aozora warichu="(?P<name>.+?)" height="(?P<height>\d+)">')
        reAozoraTatenakayoko = re.compile(ur'<aozora tatenakayoko="(?P<target>.+?)">')
        kakkochosei = 1.    # 連続して出現する括弧類の送り量の調整
        fontheight = self.currentText.get_linedata(self.currentText.canvas_fontsize,0)[0]

        # 行末合わせ調整対象文字　優先順位兼用
        adjchars = u'　 、，．。）］｝〕〉》」』】〙〗（［｛〔〈《「『【〘〖｟,.'

        """ 前回の呼び出しから引き継がれたタグがあれば付加する
        """
        if self.tagstack:
            for pos, a in enumerate(sline):
                if a != u'　':
                    break
            sline = sline[:pos] + u''.join(self.tagstack) + sline[pos:]
            self.tagstack = []

        """ 行の分割
            文字列の長さと実際の画面上における長さが一致しないことに注意
            ・<>, </> はカウントしない
            ・<aozora yokogumi="">hoge</aozora> は常に１文字分の高さしか
            　持たない
            ・<sub>, <sup> では文字の大きさが変わる
            ・連続して出現する括弧類及び漢数字内の読点は送り量が調整される
        """
        pos = 0
        slinelen = len(sline)
        tagnamestart = 0        # tag の開始位置
        skipspc = True
        pixelsmax = smax * fontheight           # 1行の長さのピクセル値
        pixellcc = 0.0                          # 描画時の全長（ピクセル値）
        substack = []

        while pos < slinelen:
            if pixellcc >= pixelsmax:
                """ 文字列の長さ（描画時ピクセル数）が所定を越えたら
                    禁則処理及び行末合わせ調整を行って終了する。
                """
                if sline[pos] in u'…—‥―':
                    """ 分離禁止処理（仮）
                    """
                    if sline[pos] == sTestCurrent[-1][0]:
                        if len(adjCurrent) > 1 and pixellcc == pixelsmax:
                            # 行末へぶら下げ
                            pixellcc += fLenCurrent[-1]
                            fLenCurrent.append(fLenCurrent[-1])
                            sTestCurrent.append(sline[pos])
                            pos += 1
                        else:
                            # 調整余裕が無ければ次行先頭へ
                            sTestNext.insert(0,sTestCurrent.pop())
                            pixellcc -= fLenCurrent.pop()

                sTestTmp = []
                fLenTmp = []
                try:
                    """ ワードラップ
                    """
                    # URL を検出した場合はラップしない
                    sTest0 = u''.join(sTestCurrent)
                    for a in [u'http:', u'https:', u'mailto:']:
                        if a in sTest0:
                            raise IndexError

                    # 前方参照してワードの区切りを探す
                    while sTestCurrent[-1][0] in self.charwidth_serif and \
                                                sTestCurrent[-1][0].isalnum():
                        sTestTmp.insert(0, sTestCurrent.pop())
                        fLenTmp.insert(0,fLenCurrent.pop())

                    for a in sTestCurrent:
                        # 無限ループを回避するため、ラップしたワードが1行の
                        # 長さを上回るようならキャンセルする。本来ならそれだ
                        # けでよいのだが、この後インデントで行頭に空白が付され
                        # １行の長さを上回ると無限ループとなる。
                        # その為、長さに関わらずラップしたワードが（空白以外）の
                        # 行先頭要素であればキャンセルする。
                        if not a[0] in [u' ', u'　']:#0x20,全角空白
                            # 正常終了
                            sTestNext = sTestTmp + sTestNext
                            pixellcc -= sum(fLenTmp)
                            break
                    else:
                        # キャンセル
                        sTestCurrent += sTestTmp
                        fLenCurrent += fLenTmp
                except IndexError:
                    # 行末から行頭まで連綿と英数字が続く場合はエラーになる
                    # ラップ不可能としてキャンセルする
                    sTestCurrent += sTestTmp
                    fLenCurrent += fLenTmp

                if sTestCurrent[-1][0] in self.kinsoku2 or \
                    (sTestCurrent[-1][:2] == u'</' and (sTestCurrent[-2][0] in self.kinsoku2)):
                    """ 行末禁則処理
                        禁則文字が続く場合は全て次行先頭へ追い出す
                    """
                    try:
                        while True:
                            if sTestCurrent[-1][:2] == u'</' and (sTestCurrent[-2][0] in self.kinsoku2):
                                # タグ付きの場合の処理
                                # 閉じタグを移動
                                sTestNext.insert(0, sTestCurrent.pop())
                                pixellcc -= fLenCurrent.pop()
                                # 禁則文字を移動
                                sTestNext.insert(0, sTestCurrent.pop())
                                pixellcc -= fLenCurrent.pop()
                                # タグを移動
                                sTestNext.insert(0, sTestCurrent.pop())
                                pixellcc -= fLenCurrent.pop()
                                continue

                            if sTestCurrent[-1][0] in self.kinsoku2:
                                sTestNext.insert(0, sTestCurrent.pop())
                                pixellcc -= fLenCurrent.pop()
                                continue

                            break

                    except IndexError:
                        print u'行末禁則処理IndexErrro'
                        pass

                elif not sTestNext: # 次行先頭への送り込みがなければ
                    """ 行頭禁則処理
                        調整可能な範囲で前行末へ追い出す。
                        追い出しきれない場合は、前行末から行頭へ移す。
                    """
                    sTestTmp = []
                    fLenTmp = []

                    if pixellcc == pixelsmax and sline[pos] in u'、。．，':
                        # 句読点のぶら下げ
                        sTestCurrent.append(sline[pos])
                        fLenCurrent.append(fontheight * self.charwidth(sline[pos]) * self.fontsizefactor[fontsizename])
                        # 調整余地があれば後段で処理するよう全長を調整する
                        if adjCurrent and sline[pos] in u'、，':
                            pixellcc += fLenCurrent[-1]
                        elif len(adjCurrent) >= 2:
                            pixellcc += fLenCurrent[-1]
                        pos += 1
                    else:
                        try:
                            while sline[pos] in u'<>' + self.kinsoku:
                                # 行頭禁則文字を一時リストへ取り出す
                                if sline[pos:pos+2] == u'</':
                                    # 閉じタグ
                                    tagnamestart = pos
                                    pos = sline.find(u'>',pos+2) + 1
                                    substack.pop()
                                    sTestTmp.append(sline[tagnamestart:pos])
                                    fLenTmp.append(0.0)
                                elif sline[pos] == u'<':
                                    # タグ
                                    tagnamestart = pos
                                    pos = sline.find(u'>',pos+2) + 1
                                    substack.append(sline[tagnamestart:pos])
                                    sTestTmp.append(sline[tagnamestart:pos])
                                    fLenTmp.append(0.0)
                                else:
                                    # 禁則文字
                                    sTestTmp.append(sline[pos])
                                    fLenTmp.append(fontheight * self.charwidth(sline[pos]) * self.fontsizefactor[fontsizename])
                                    pos += 1
                        except IndexError:
                            pass

                        # 調整可能文字での調整量は１文字高の半分が目安
                        #n = fontheight * math.ceil(len(adjCurrent) / 2.) - pixellcc + pixelsmax
                        #n = fontheight * round(len(adjCurrent) / 2.) - pixellcc + pixelsmax
                        n = fontheight * len(adjCurrent) / 2. - pixellcc + pixelsmax

                        if n >= sum(fLenTmp):
                            # ピクセル値で調整可能範囲と比較
                            # 行末に収容できるなら接続
                            sTestCurrent += sTestTmp
                            fLenCurrent += fLenTmp
                            pixellcc += sum(fLenTmp)
                        else:
                            # 収容できなければ、行末から次行先頭に移動
                            while True:
                                if sTestCurrent[-1][0] == u'<' or sTestCurrent[-1][0] in self.kinsoku:
                                    # タグあるいは行頭禁則文字なら移動して継続
                                    sTestTmp.insert(0, sTestCurrent.pop())
                                    fLenTmp.insert(0, fLenCurrent.pop())
                                    pixellcc -= fLenTmp[0]
                                else:
                                    # 移動
                                    sTestTmp.insert(0, sTestCurrent.pop())
                                    fLenTmp.insert(0, fLenCurrent.pop())
                                    pixellcc -= fLenTmp[0]
                                    if sTestTmp[0][0] in u'…—‥―' and \
                                        sTestTmp[0][0] == sTestCurrent[-1][0]:
                                        # 分離禁止文字の例外処理
                                        sTestTmp.insert(0, sTestCurrent.pop())
                                        fLenTmp.insert(0, fLenCurrent.pop())
                                        pixellcc -= fLenTmp[0]

                                    #終了
                                    break

                            sTestNext = sTestTmp + sTestNext

                """ 行末における送り量の調整
                        JIS X 4051 による
                        (但し参照元はhttp://www.w3.org/TR/jlreq/ja/#characters_not_starting_a_line)
                            終わり括弧、句点はベタ組
                            読点は二分空き
                            中点は前四分後ろベタ
                """
                if pixellcc >= pixelsmax:
                    currpos = -1
                    while sTestCurrent[currpos][0] == u'<':
                        currpos -= 1
                    pixellcc -= fLenCurrent[currpos]
                    if sTestCurrent[currpos-1].find(u'<aozora half') == -1:
                        # 送り量調整がかかっていなければ調整する
                        if sTestCurrent[currpos][0] in self.kinsoku5:
                            fLenCurrent[currpos] *= 0.5
                        elif sTestCurrent[currpos][0] == u'・':
                            fLenCurrent[currpos] *= 0.75
                    pixellcc += fLenCurrent[currpos]

                if pixellcc != pixelsmax and adjCurrent:
                    """ 行末合わせ
                            調整箇所文字の表示開始位置をずらす
                            調整箇所文字の送り量を増減する
                        ことで、行末を揃える。
                        溢れる場合は詰め、そうでない場合は延ばす。
                        不足する場合、行末が句読点ならばそのまま。
                    """
                    try:
                        # 拾い出された調整箇所全てで文字間調整を行う
                        # 但し行末の閉じ括弧類は除外する

                        # 行末の閉じ括弧類が登録されていれば除外
                        currpos = -1
                        while sTestCurrent[currpos][0] == u'<':
                            currpos -= 1
                        if sTestCurrent[currpos][0] in self.kinsoku4:
                            currpos = len(sTestCurrent) + currpos
                            if adjCurrent[-1][1] == currpos:
                                adjCurrent.pop()

                        # 禁則処理で移動した要素を参照していれば抜去する
                        adjTmp = []
                        for a0 in adjCurrent:
                            try:
                                b = sTestCurrent[a0[1]]
                                adjTmp.append(a0)
                            except IndexError:
                                continue

                        adj = pixellcc - pixelsmax      # 調整量
                        adjsgn = float(-cmp(adj, 0))
                        adj = abs(adj)
                        adjn = adj / float(len(adjTmp))
                        # （全ての箇所で同じ調整量が適用される）
                        adjTmp.sort()
                        a = len(adjTmp) - 1
                        while a >= 0:
                            if a == 0 and adj >= 0.:
                                adjn = adj # 最後は残り全部

                            if sTestCurrent[adjTmp[a][1]] in self.kinsoku2:
                                # 開き括弧類は書き出し位置をずらす
                                sTestCurrent.insert(adjTmp[a][1],
                                    u'<aozora ofset="%f">%s</aozora>' % (
                                    (adjn * adjsgn), # 調整ピクセル値
                                    sTestCurrent[adjTmp[a][1]] ))
                            else:
                                # それ以外は送り量を増減する
                                sTestCurrent.insert(adjTmp[a][1],
                                    u'<aozora adj="%f">%s</aozora>' % (
                                    (adjn * adjsgn), # 調整ピクセル値
                                    sTestCurrent[adjTmp[a][1]] ))
                            sTestCurrent.pop(adjTmp[a][1]+1)
                            adj -= adjn
                            a -= 1

                    except ZeroDivisionError:
                        # 調整可能箇所なし
                        pass
                        #logging.info(
                        #    u'行末調整用の文字が不足しています。%d ページ付近、%s' % (
                        #    self.currentText.pagecounter, u''.join(sTestCurrent[0:20])) )
                else:
                    # 調整可能箇所なし
                    pass
                    #logging.info(
                    #    u'行末調整用の文字が不足しています。%d ページ付近、%s' % (
                    #    self.currentText.pagecounter, u''.join(sTestCurrent[0:20])) )

                #-------------
                # End of Loop
                #-------------
                sTestNext.append(sline[pos:])
                break

            if inTag:
                if sline[pos] == u'>':
                    inTag = False
                    # tagスタックの操作
                    pos += 1
                    sTestCurrent.append(sline[tagnamestart:pos])
                    fLenCurrent.append(0.0)
                    if sline[tagnamestart:tagnamestart+2] == u'</':
                        # </tag>の出現とみなしてスタックから取り除く
                        if substack != []:
                            # 訓点・返り点対応
                            if substack[-1] in [u'<sup>', u'<sub>']:
                                fontsizename = u'normal'
                            # 連続して出現する括弧類
                            elif substack[-1][:12] == u'<aozora half':
                                kakkochosei = 1.
                            # 抜去しつつフォントサイズかどうかチェック
                            tmp = self.reFontsizefactor.search(substack.pop())
                            if tmp:
                                if tmp.group('name') in self.fontsizefactor:
                                    fontsizename = u'normal' # 文字サイズの復旧

                    else:
                        # tag 別の処理
                        tmp = self.reImgtag.search(sline[tagnamestart:pos])
                        if tmp:
                            # 埋め込みイメージ
                            tagnamestart = pos
                            pos = sline.find(u'</',pos)
                            imgheight = float(len(sline[tagnamestart:pos]) * fontheight)
                            if pixellcc +  imgheight > pixelsmax:
                                # 行末までに収まらなければ次行へ送る
                                sTestNext.insert(0, u'</aozora>')
                                sTestNext.insert(0, sline[tagnamestart:pos])
                                sTestNext.insert(0, sTestCurrent.pop())
                                fLenCurrent.pop()
                                pos += 9 # len(u'</aozora>')
                                pixellcc = pixelsmax # ループ終了条件を満たす
                            else:
                                sTestCurrent.append(sline[tagnamestart:pos])
                                fLenCurrent.append(imgheight)
                                pixellcc += imgheight
                                substack.append(sTestCurrent[-1])
                            continue

                        tmp = reAozoraWarichu.search(sline[tagnamestart:pos])
                        if tmp:
                            # 割り注
                            wariheight = int(tmp.group('height'))
                            if pixellcc + fontheight * wariheight * self.fontsizefactor['size="x-small"'] > pixelsmax:
                                # 行末迄に収まらなければ割り注を分割する
                                sTestCurrent.pop()
                                fLenCurrent.pop()

                                warisize = int(math.floor((pixelsmax - pixellcc) / (fontheight * self.fontsizefactor['size="x-small"'])))
                                waribun = tmp.group('name').replace(u'［＃改行］', u'')
                                waricurrent = waribun[:warisize*2]
                                warinext = waribun[warisize*2:]
                                try:
                                    while warinext[0] in self.kinsoku:
                                        # 次行への行頭禁則文字の持ち越しを回避する
                                        waricurrent += warinext[0]
                                        warinext = warinext[1:]
                                        warisize += 0.5 # 表示高さ補正
                                except IndexError:
                                    pass
                                warisize = int(math.ceil(warisize))
                                heightcurrent = int(math.ceil((pixelsmax - pixellcc) / float(fontheight) ))
                                heightnext = int(math.ceil(math.ceil(len(warinext)/2.) * self.fontsizefactor['size="x-small"']))

                                sTestCurrent.append(u'<aozora warichu="%s" height="%d">' % (waricurrent, warisize))
                                fLenCurrent.append(0.0)
                                sTestCurrent.append(u'　' * heightcurrent)
                                fLenCurrent.append(float(heightcurrent)*fontheight+1)
                                pixellcc += fLenCurrent[-1]
                                if pixellcc < pixelsmax:
                                    pixellcc = pixelsmax # ループ終了条件を満たす
                                sTestCurrent.append(u'</aozora>')
                                fLenCurrent.append(0.0)

                                # 残りを次行へ送る
                                sTestNext.insert(0, u'</aozora>')
                                sTestNext.insert(0, u'　' * heightnext)
                                sTestNext.insert(0, u'<aozora warichu="%s" height="%d">' % (warinext, math.ceil(len(warinext)/2.)))

                                pos = sline.find(u'</aozora>',pos) + 9
                                continue

                        elif sline[tagnamestart:tagnamestart+20] == u'<aozora tatenakayoko':
                            # 縦中横　特殊処理　本文文字列高さを常に１文字+1pixelとみなす
                            # 先頭が連続する括弧の一部であれば、直前の送り量調整を解除する
                            tatenakapos = sline.find(u'>',tagnamestart)+1
                            if sline[tatenakapos] in self.kakko:
                                tatenakapos = -1 # 変数名使いまわし
                                try:
                                    while sTestCurrent[tatenakapos][0] == u'<':
                                        # タグスキップ
                                        tatenakapos -= 1
                                    if sTestCurrent[tatenakapos][0] in self.kakko:
                                        targetpos = tatenakapos # 連続する括弧類の前半
                                        tatenakapos -= 1
                                        while True:
                                            tmp = self.reAozoraHalf.search(sTestCurrent[tatenakapos])
                                            if tmp:
                                                # 送り量補正
                                                pixellcc -= fLenCurrent[targetpos]
                                                fLenCurrent[targetpos] /= float(tmp.group(u'name'))
                                                pixellcc += fLenCurrent[targetpos]
                                                sTestCurrent[tatenakapos] = u'<aozora half="1.0">'
                                                break
                                            else:
                                                tatenakapos -= 1
                                except IndexError:
                                    pass

                            # 処理時間を稼ぐためここで閉じる
                            tagnamestart = pos # 変数名使いまわし
                            pos = sline.find(u'</aozora>',pos)
                            sTestCurrent.append(sline[tagnamestart:pos])
                            fLenCurrent.append(1+fontheight * self.fontsizefactor[fontsizename])
                            pixellcc += fLenCurrent[-1]
                            tagnamestart = pos # 変数名使いまわし
                            pos += 9 #len(u'</aozora>')
                            sTestCurrent.append(sline[tagnamestart:pos])
                            fLenCurrent.append(0.0)
                            continue

                        elif sline[tagnamestart:pos] in [u'<sup>', u'<sub>']:
                            # 訓点・返り点対応
                            if fontsizename == u'size="small"':
                                fontsizename = u'size="x-small"'
                            elif fontsizename == u'size="x-small"':
                                fontsizename = u'size="xx-small"'
                            elif fontsizename == u'size="xx-small"':
                                pass
                            else:
                                fontsizename = u'size="small"'
                        else:
                            tmp = self.reAozoraHalf.search(sline[tagnamestart:pos])
                            if tmp:
                                # 送り量の調整
                                kakkochosei = float(tmp.group('name'))
                            else:
                                tmp = self.reFontsizefactor.search(sline[tagnamestart:pos])
                                if tmp:
                                    # 文字サイズ変更
                                    if tmp.group('name') in self.fontsizefactor:
                                        fontsizename = tmp.group('name')
                        # tag をスタックへ保存
                        substack.append(sline[tagnamestart:pos])
                else:
                    pos += 1
            elif sline[pos] == u'<':
                # tag 開始位置を得る
                inTag = True
                tagnamestart = pos
                pos += 1
            else:
                sTestCurrent.append(sline[pos])
                fLenCurrent.append(fontheight * self.charwidth(sline[pos]) * \
                            self.fontsizefactor[fontsizename] * kakkochosei)
                pixellcc += fLenCurrent[-1] # tagでなければ画面上における全長を計算

                """ 行全長調整用の文字位置を記録する
                    行頭の空白（おそらくはインデント分）と最初の括弧類は調整対象から外す
                """
                if skipspc and not sline[pos] in u'　 '+self.kinsoku2:
                    # 行頭の空白や括弧が途切れたらフラグオフ
                    skipspc = False

                i = adjchars.find(sline[pos]) # 調整時の優先順を兼ねる
                if i != -1 and not skipspc:
                    if substack and substack[-1].find(u' ') != -1:
                        # 直前のタグを調べて、調整対象にするか判断する
                        # 属性のないタグ(sup,sub)を避ける為上のifで' 'の有無を見る
                        sTagname = substack[-1].split()[1].split(u'=')[0]
                        if not sTagname in [u'rubi',u'half',u'img',u'img2',u'warichu']:
                            # ルビ類でなければ調整対象
                            adjCurrent.append((i,len(sTestCurrent)-1))
                    else:
                        adjCurrent.append((i,len(sTestCurrent)-1))

                pos += 1

        else:
            """ 行の分割が発生しなかった際の行末調整
                行末が終わり括弧や句読点で、且つ最終桁にかかる場合に限り
                調整する。
            """
            if adjCurrent and pixellcc > pixelsmax - fontheight:
                currpos = -1
                while sTestCurrent[currpos][0] == u'<':
                    currpos -= 1
                if sTestCurrent[currpos][0] in self.kinsoku5 + u'・':
                    # 送り量調整
                    pixellcc -= fLenCurrent[currpos]
                    if sTestCurrent[currpos-1].find(u'<aozora half') == -1:
                        if sTestCurrent[currpos][0] in self.kinsoku5:
                            fLenCurrent[currpos] *= 0.5
                        elif sTestCurrent[currpos][0] == u'・':
                            fLenCurrent[currpos] *= 0.75
                    pixellcc += fLenCurrent[currpos]

                    #"""
                    try:
                        # 拾い出された調整箇所全てで文字間調整を行う
                        # 但し行末の閉じ括弧類は除外する
                        if sTestCurrent[currpos][0] in self.kinsoku4:
                            currpos = len(sTestCurrent) + currpos
                            if adjCurrent[-1][1] == currpos:
                                adjCurrent.pop()

                        # 禁則処理で移動した要素を参照していれば抜去する
                        #adjTmp = []
                        #for a0 in adjCurrent:
                        #    try:
                        #        b = sTestCurrent[a0[1]]
                        #        adjTmp.append(a0)
                        #    except IndexError:
                        #        continue

                        adj = pixellcc - pixelsmax #- fontheight # 調整量
                        adjsgn = float(-cmp(adj, 0))
                        adj = abs(adj)
                        adjn = adj / float(len(adjCurrent))
                        # （全ての箇所で同じ調整量が適用される）
                        adjCurrent.sort()
                        a = len(adjCurrent) - 1
                        while a >= 0:
                            if a == 0 and adj >= 0.:
                                adjn = adj # 最後は残り全部

                            if sTestCurrent[adjCurrent[a][1]] in self.kinsoku2:
                                # 開き括弧類は書き出し位置をずらす
                                sTestCurrent.insert(adjCurrent[a][1],
                                    u'<aozora ofset="%f">%s</aozora>' % (
                                    (adjn * adjsgn), # 調整ピクセル値
                                    sTestCurrent[adjCurrent[a][1]] ))
                            else:
                                # それ以外は送り量を増減する
                                sTestCurrent.insert(adjCurrent[a][1],
                                    u'<aozora adj="%f">%s</aozora>' % (
                                    (adjn * adjsgn), # 調整ピクセル値
                                    sTestCurrent[adjCurrent[a][1]] ))
                            sTestCurrent.pop(adjCurrent[a][1]+1)
                            adj -= adjn
                            a -= 1

                    except ZeroDivisionError:
                        # 調整可能箇所なし
                        pass
                    #"""

        """ 閉じられていないタグを検出する
            あれば一旦閉じて次回へ引き継ぐ。
            ルビの分かち書きもここで処理する。
        """
        substack = []
        for currpos, sTest in enumerate(sTestCurrent):
            try:
                if sTest[0:2] == u'</':
                    substack.pop()
                elif sTest[0] == u'<':
                    if sTest[1:].find(u'</') == -1:
                        # 但し同一要素内でタグが完了していれば追加しない
                        substack.append((currpos, sTest))
                else:
                    pass
            except IndexError:
                #print sTest, currpos, len(sTestCurrent)
                #print u''.join(sTestCurrent)
                pass

        while substack:
            currpos, currtag = substack.pop()
            taginfo = currtag.split() # 属性に空白が含まれるとバグとなる可能性あり

            if len(taginfo) == 1:
                # おそらく <sub> , <sup>
                sTestCurrent.append(u'</%s>' % taginfo[0].strip(u'<>'))
                self.tagstack.insert(0, currtag) # 次回へ引き継ぐ
                continue

            tagattr = taginfo[1].split(u'=')

            if tagattr[0] == u'keikakomigyou':
                # 罫囲みの分割
                # かかる文字の長さを求める
                sTarget = currpos + 1
                while sTarget < len(sTestCurrent) - 1 and sTestCurrent[sTarget][0] != u'<':
                    sTarget += 1
                # 描画内容の遷移テーブル  mode 1 始め 2 中間 3 終わり
                # 例：最初は0 (1,3を得る)  1を分割すると1と2が得られる
                (modeself, modenext) = [(1,3) , (1,2) , (2,2) , (2,3)][int(tagattr[1].strip('">'))]
                sTestCurrent[currpos] = u'<aozora keikakomigyou="%d">' % modeself
                sTestCurrent.append(u'</aozora>')
                self.tagstack.insert(0, u'<aozora keikakomigyou="%d">' % modenext)

            elif tagattr[0] in [u'rubi', u'leftrubi']:
                # ルビの分かち書きの有無
                if tagattr[1][-1] != '"':
                    # ルビ内にスペースが含まれており分断されてしまったので
                    # 修復する
                    tagattr[1] = u'%s %s' % (tagattr[1],taginfo[2])

                rubi = tagattr[1].strip(u'">')
                targetlength = int(taginfo[-1].split(u'=')[1].strip(u'">'))
                if targetlength != 0: # 繰越で生じた空タグならスキップ
                    if currpos < len(sTestCurrent) - 1:
                        # ルビのかかる親文字の長さを求める
                        # （但し，ルビタグより内側に他のタグが無いことを前提としたルーチン）
                        sTarget = currpos + 1
                        while sTarget < len(sTestCurrent) - 1 and sTestCurrent[sTarget][0] != u'<':
                            sTarget += 1
                        hlen = len(u''.join(sTestCurrent[currpos+1:sTarget+1]))
                        # ルビを親文字の長さを勘案して分割
                        # 注記として付与された〔〕をカウントしない
                        rubilen = int(round(len(rubi.strip(u'〔〕')) * (hlen / float(targetlength)) ))
                        if u'〔' in rubi:
                            rubilen += 1 # 分割位置の調整
                        rubiafter = rubi[rubilen:]
                        rubi = rubi[:rubilen]

                        # ルビを分割するなら現在行のルビを修正し、残りを次行へ持ち越し
                        if rubiafter:
                            sTestCurrent[currpos] = u'<aozora %s="%s" length="%d">' % (
                                    tagattr[0], rubi, rubilen )
                            sTestCurrent.append(u'</aozora>')

                            self.tagstack.insert(0, u'<aozora %s="%s" length="%d">' % (
                                tagattr[0], rubiafter, targetlength - rubilen ))
                        else:
                            sTestCurrent.append(u'</aozora>')
                            self.tagstack.insert(0, u'<aozora %s="" length="0">' % tagattr[0] )
                    else:
                        # 行末がこのタグで終わっているなら、全て次行へ持ち越し
                        sTestCurrent.append(u'</aozora>')
                        self.tagstack.insert(0, currtag)

            else:
                sTestCurrent.append(u'</%s>' % taginfo[0].strip(u'<>'))
                self.tagstack.insert(0, currtag) # 次回へ引き継ぐ

        return (u''.join(sTestCurrent), u''.join(sTestNext))

    def __write2file(self, fd, s):
        """ formater 下請け
            1行出力後、改ページしたらその位置を記録して True を返す。
            目次作成もここで行う。
            出力時の正確なページ数と行数が分かるのはここだけ。
        """
        rv = False
        fd.write(s)         # 本文

        if self.loggingflag:
            logging.debug( u'　位置：%dページ、%d行目' % (
                                    self.currentText.pagecounter+1,
                                    self.linecounter+1 ))
            self.loggingflag = False

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
                    # 2行目以降はインデント用（と思われる）空白を除去する。
                    self.midashi += s.rstrip('\n').lstrip(u'　 ') if self.midashi else s.rstrip('\n')
                    if self.FukusuMidashiOwari:
                        # 複数行に及ぶ見出しが終わった場合
                        self.FukusuMidashiOwari = False
                        self.inFukusuMidashi = False
                        self.mokuji_f.write( sMokujiForm % (
                            self.reTagRemove.sub(u'',
                                self.midashi.lstrip(u' 　').rstrip('\n')),
                            self.currentText.pagecounter))
                        self.inMidashi = False
                else:
                    self.mokuji_f.write( sMokujiForm % (
                        self.reTagRemove.sub(u'',
                            self.midashi.lstrip(u' 　').rstrip('\n')),
                        self.currentText.pagecounter))
                    self.inMidashi = False

            self.linecounter += 1
            if self.linecounter >= self.currentText.pagelines:
                # 1頁出力し終えたらその位置を記録する
                self.currentText.pagecounter += 1
                self.currentText.currentpage.append(fd.tell())
                self.linecounter = 0
                fd.flush()
                rv = True
        return rv

