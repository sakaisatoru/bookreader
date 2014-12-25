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

""" フォーマッタ及びレンダラー

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
import sys, codecs, re, os.path, datetime, unicodedata, logging

import gtk, cairo, pango, pangocairo, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)


class Aozora(ReaderSetting):
    """
    """
    reHeader = re.compile( ur'^-------------------------------------------------------' )
    reFooter = re.compile( ur'(^底本：)|(［＃本文終わり］)' )

    reGaiji = re.compile( ur'(※［＃.*?、.*?(?P<number>\d+\-\d+\-\d+\d*)］)' )
    reGaiji2 = re.compile( ur'※［＃「.+?」、U\+(?P<number>[0-9A-F]+?)、(\d+?\-\d+?)］' )
    # ※［＃「口＋世」、U+546D、ページ数-行数］

    reKunoji = re.compile( ur'(／＼)' )
    reGunoji = re.compile( ur'(／″＼)' )
    reCTRL = re.compile( ur'(?P<aozoratag>［＃.*?］)' )
    reHansoku = re.compile( ur'(【＃(?P<name>.+?)】)' )
    reNonokagi = re.compile( ur'(“(?P<name>.+?)”)' )

    reBouten = re.compile( ur'(［＃「(?P<name>.+?)」に(?P<type>.*?)傍点］)' )
    reBouten2 = re.compile( ur'((?P<name>.*?)［＃傍点終わり］)' )
    reBousen = re.compile( ur'(［＃「(?P<name>.+?)」に傍線］)' )
    reNijuBousen = re.compile( ur'(［＃「(?P<name>.+?)」に二重傍線］)' )
    reGyomigikogaki = re.compile( ur'(［＃「(?P<name>.+?)」は((行右小書き)|(上付き小文字))］)' )
    reMama = re.compile( ur'(［＃「(?P<name>.+?)」に「(?P<mama>.??ママ.??)」の注記］)' )
    reMama2 = re.compile( ur'(［＃「(?P<name>.+?)」は(?P<mama>.??ママ.??)］)' )
    reKogakiKatakana = re.compile( ur'(［＃小書(き)?片仮名(?P<name>.+?)、.+?］)' )
    reShitatsukiKomoji = re.compile( ur'(［＃「(?P<name>.+?)」は((行左小書き)|(下付き小文字))］)' )

    reRubi = re.compile( ur'《.*?》' )
    reRubiclr = re.compile( ur'＃' )
    reRubimama = re.compile( ur'(［＃ルビの「(?P<name>.+?)」はママ］)' )


    reFutoji = re.compile( ur'［＃「(?P<name>.+?)」は太字］' )
    reFutoji2 = re.compile( ur'［＃(ここから)?太字］' )
    reSyatai = re.compile( ur'［＃「(?P<name>.+?)」は斜体］' )
    reSyatai2 = re.compile( ur'［＃(ここから)?斜体］' )

    # キャプション
    reCaption = re.compile( ur'(［＃「(?P<name>.*?)」はキャプション］)' )
    # 文字サイズ
    reMojisize = re.compile( ur'(［＃(ここから)?(?P<size>.+?)段階(?P<name>.+?)な文字］)')

    # 処理共通タグ ( </span>生成 )
    reOwari = re.compile(
                ur'(［＃(ここで)?((大き)|(小さ))+な文字終わり］)|' +
                ur'(［＃(ここで)?斜体終わり］)|' +
                ur'(［＃(ここで)?太字終わり］)')

    # 未実装タグ
    reOmit = re.compile(
                ur'(［＃ページの左右中央］)|' +
                ur'(［＃本文終わり］)|' +
                ur'(［＃(ここから)??横組み］)|'+
                ur'(［＃(ここで)??横組み終わり］)|' +
                ur'(［＃「.+?」は縦中横］)|' +
                ur'(［＃割り注.*?］)|' +
                ur'(［＃「.+?」は底本では「.+?」］)|' +
                ur'(［＃ルビの「.+?」は底本では「.+?」］)' )

    # 字下げ、字詰、地付き、地寄せ（地上げ）
    reIndent = re.compile( ur'［＃(天から)??(?P<number>[０-９]+?)字下げ］' )
    reIndentStart = re.compile( ur'［＃ここから(?P<number>[０-９]+?)字下げ］' )
    reKaigyoTentsuki = re.compile( ur'［＃ここから改行天付き、折り返して(?P<number>[０-９]+?)字下げ］' )
    reKokokaraSage = re.compile( ur'［＃ここから(?P<number>[０-９]+?)字下げ、折り返して(?P<number2>[０-９]+?)字下げ］' )
    reIndentEnd = re.compile( ur'［＃(ここで)??字下げ終わり］|［＃字下げおわり］')

    reJiage = re.compile( ur'((?P<name2>.+?)??(?P<tag>［＃地付き］|［＃地から(?P<number>[０-９]+?)字上げ］)(?P<name>.+?)??$)' )
    reKokokaraJiage = re.compile( ur'［＃ここから地から(?P<number>[０-９]+?)字上げ］')
    reJiageowari = re.compile( ur'［＃ここで字上げ終わり］' )

    reKokokaraJitsuki = re.compile( ur'［＃ここから地付き］' )
    reJitsukiowari = re.compile( ur'［＃ここで地付き終わり］' )

    reJizume = re.compile( ur'［＃ここから(?P<number>[０-９]+?)字詰め］' )
    reJizumeowari = re.compile( ur'［＃ここで字詰め終わり］' )

    # 見出し
    reMidashi = re.compile( ur'［＃「(?P<midashi>.+?)」は(同行)??(?P<midashisize>大|中|小)見出し］' )
    reMidashi2name = re.compile( ur'((<.+?)??(?P<name>.+?)[<［\n]+?)' )
    reMidashi2 = re.compile( ur'(［＃(ここから)??(?P<midashisize>大|中|小)見出し］)' )
    reMidashi2owari = re.compile( ur'(［＃(ここで)??(?P<midashisize>大|中|小)見出し終わり］)' )

    # 改ページ・改丁・ページの左右中央
    reKaipage = re.compile( ur'［＃改ページ］|［＃改丁］' )
    # reSayuuchuou = re.compile( ur'［＃ページの左右中央］' )

    # 挿図
    #reFig = re.compile( ur'(［＃(?P<name>.+?)）入る］)' )
    reFig = re.compile(
        ur'(［＃(.+?)?（(?P<filename>[\w\-]+?\.png)(、横\d+?×縦\d+?)??）入る］)' )

    # 訓点・返り点
    reKuntenOkuri = re.compile( ur'(［＃（(?P<name>.+?)）］)' )
    reKaeriten = re.compile(
                    ur'(［＃(?P<name>[レ一二三四五六七八九'+
                            ur'上中下' +
                            ur'甲乙丙丁戊己庚辛壬癸' +
                            ur'天地人' +
                            ur'元亨利貞' +
                            ur'春夏秋冬'+
                            ur'木火土金水'+
                            ur']??)］)' )

    # フッターにおける年月日刷を漢数字に変換
    reNenGetsuNichi = re.compile( ur'((?P<year>\d+?)(（((明治)|(大正)|(昭和)|(平成))??(?P<gengo>\d+?)）)??年)|'+
        ur'((?P<month>\d+?)月)|'+
        ur'((?P<day>\d+?)日)|' +
        ur'((?P<ban>\d+?)版)|' +
        ur'((?P<suri>\d+?)刷)' )

    # pangocairo における & エスケープ用
    reAmp = re.compile( ur'&' )

    # 禁則
    kinsoku = u'\r,)]｝、）］｝〕〉》」』】〙〗〟’”｠»ヽヾーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻‐゠–〜?!‼⁇⁈⁉・:;。、！？'
    kinsoku2 = u'([{（［｛〔〈《「『【〘〖〝‘“｟«'
    kinsoku3 = u'〳〴〵' # —…‥
    kinsoku4 = u'\r,)]｝、）］｝〕〉》」』】〙〗〟’”｠»。、'

    """ ソースに直書きしているタグ
        u'［＃傍点］'
        u'［＃行右小書き］'                 u'［＃行右小書き終わり］'
        u'［＃行左小書き］'                 u'［＃行左小書き終わり］'
        u'［＃上付き小文字］'               u'［＃上付き小文字終わり］'
        u'［＃下付き小文字］'               u'［＃下付き小文字終わり］'
        u'［＃ここからキャプション］'        u'［＃ここでキャプション終わり］'
        u'［＃ここから１段階小さな文字］'    u'［＃ここで小さな文字終わり］'
    """

    def __init__( self, chars=40, lines=25 ):
        ReaderSetting.__init__(self)
        self.destfile = self.get_value( u'workingdir') + '/view.txt'    # フォーマッタ出力先
        self.mokujifile = self.get_value( u'workingdir') + '/mokuji.txt'    # 目次ファイル
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
        reTranslatorName = re.compile( ur'.+?訳' )
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
                #
                #   空行に出くわすか、説明が始まったら終わる
                #
                if lnbuf == '-------------------------------------------------------' or \
                            len(lnbuf) == 0:
                    if sBookTranslator != u'':
                        sBookAuthor = u'%s / %s' % (sBookAuthor ,sBookTranslator)
                    break
                #
                #   書名、著者名を得る
                #
                if iCurrentReadline == 1:
                    sBookTitle = lnbuf
                #
                #   副題
                #
                if iCurrentReadline == 2:
                    sBookTitle2 = lnbuf
                #
                #   末尾に「訳」とあれば翻訳者扱い
                #
                if reTranslatorName.search(lnbuf) != None:
                    sBookTranslator = lnbuf
                else:
                    sBookAuthor = lnbuf

        if sBookTitle2 == sBookAuthor:
            sBookTitle2 = u''
        sBookTitle = u'%s %s' % (sBookTitle, sBookTitle2 )
        return (sBookTitle, sBookAuthor)

    def formater_pass1( self, sourcefile=None ):
        """ フォーマッタ（第1パス）
            formater より呼び出されるジェネレータ。1行読み込んでもっぱら
            置換処理を行う。

                特殊文字
                    繰り返し記号のくの字及びぐの字を本来の文字に置換する。
                外字変換
                    面区点コードで指定されたJIS第3、第4水準文字を実際の文字に
                    変換する。
                ヘッダ
                    削除する。
                フッタ
                    日付の半角数字を全角に変換する。
                傍点・傍線
                    ルビとして付す。
                予約されているが実装されていないタグ
                    単純に削除される
                その他
                    そのまま本文に埋め込んで呼び出し側に渡される。
        """
        if sourcefile == None:
            sourcefile = self.sourcefile

        headerflag = False      # 書名以降の注釈部分を示す
        footerflag = False
        gaijitest = gaiji()

        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            for lnbuf in f0:
                lnbuf = lnbuf.rstrip('\r\n')
                """空行の処理
                """
                if len(lnbuf) == 0:
                    yield u'\n'
                    continue

                """ ヘッダ【テキスト中に現れる記号について】の処理
                    とりあえずばっさりと削除する
                """
                if Aozora.reHeader.search(lnbuf) != None:
                    headerflag = True if headerflag == False else False
                    continue
                if headerflag == True:
                    continue

                """ フッタ
                """
                if Aozora.reFooter.search(lnbuf) != None:
                    footerflag = True

                """ 青空文庫の制御文字列である　［＃］を【＃】と表記する
                    テキストへの対応
                    (絶対矛盾的自己同一　西田幾多郎)
                """
                try:
                    for tmp in Aozora.reHansoku.finditer( lnbuf ):
                        lnbuf ='%s［＃%s］%s' % (
                            lnbuf[:tmp.start()],tmp.group('name'),lnbuf[tmp.end():] )
                except:
                    pass

                """ くの字の置換
                """
                lnbuf = Aozora.reKunoji.sub( u'〳〵', lnbuf )
                lnbuf = Aozora.reGunoji.sub( u'〴〵', lnbuf )

                """ ダブルクォーテーションの、ノノカギへの置換
                    unicode のカテゴリを調べて、アルファベット以外及び記号以外の
                    何かが出現した場合に日本語とみなして置換する。
                """
                try:
                    for tmp in Aozora.reNonokagi.finditer( lnbuf ):
                        for s in tmp.group('name'):
                            if unicodedata.category(s) == 'Lo':
                                lnbuf = '%s〝%s〟%s' % (
                                     lnbuf[:tmp.start()],
                                    tmp.group('name'),
                                    lnbuf[tmp.end():] )
                                break
                except:
                    pass

                """ 外字(JIS面句点コード指定)
                """
                retline = u''
                priortail = 0
                for tmp in Aozora.reGaiji.finditer(lnbuf):
                    retline += lnbuf[priortail:tmp.start()]
                    k = gaijitest.sconv(tmp.group('number'))
                    if k != None:
                        retline += k
                    else:
                        retline += tmp.group()
                        logging.info( u'未登録の外字を検出：%s' % tmp.group())
                    priortail = tmp.end()
                retline += lnbuf[priortail:]

                """ 外字２(Unicode指定、但し漢字のみ)
                """
                lnbuf = u''
                priortail = 0
                for tmp in Aozora.reGaiji2.finditer(retline):
                    lnbuf += retline[priortail:tmp.start()]
                    try:
                        k = unicodedata.lookup(
                            u'CJK UNIFIED IDEOGRAPH-' + tmp.group('number'))
                    except KeyError:
                        k = tmp.group()
                        logging.info( u'未定義の外字を検出：%s' % k )
                    lnbuf += k
                    priortail = tmp.end()
                lnbuf += retline[priortail:]

                """ ［＃　で始まるタグの処理
                """
                priortail = 0
                retline = u''
                for tmp in Aozora.reCTRL.finditer(lnbuf):
                    if tmp.group() == u'［＃行右小書き］' or \
                            tmp.group() == u'［＃上付き小文字］':
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'<sup>'
                        priortail = tmp.end()
                        continue

                    if tmp.group() == u'［＃行右小書き終わり］' or \
                            tmp.group() == u'［＃上付き小文字終わり］':
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'</sup>'
                        priortail = tmp.end()
                        continue

                    if tmp.group() == u'［＃行左小書き］' or \
                            tmp.group() == u'［＃下付き小文字］':
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'<sub>'
                        priortail = tmp.end()
                        continue

                    if tmp.group() == u'［＃行左小書き終わり］' or \
                            tmp.group() == u'［＃下付き小文字終わり］':
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'</sub>'
                        priortail = tmp.end()
                        continue

                    # キャプションの小文字表示は暫定処理
                    if tmp.group() == u'［＃ここからキャプション］':
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'<span size="smaller">'
                        priortail = tmp.end()
                        continue

                    if tmp.group() == u'［＃ここでキャプション終わり］':
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'</span>'
                        priortail = tmp.end()
                        continue

                    if Aozora.reOmit.match(tmp.group()):
                        #   未実装タグは単純に削除する
                        logging.info( u'削除されたタグ: %s' % tmp.group())
                        self.loggingflag = True
                        retline += lnbuf[priortail:tmp.start()]
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reCaption.match(tmp.group())
                    if tmp2:
                        #   キャプション
                        #   暫定処理：小文字で表示
                        tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                        retline += lnbuf[priortail:tmpStart]
                        retline += u'<span size="smaller">%s</span>' % lnbuf[tmpStart:tmpEnd]
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reKogakiKatakana.match(tmp.group())
                    if tmp2:
                        #
                        #   小書き片仮名
                        #   ヱの小文字など、JISにフォントが無い場合
                        retline += lnbuf[priortail:tmp.start()].rstrip(u'※')
                        retline += u'<span size="smaller">%s</span>' % tmp2.group(u'name')
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reMojisize.match(tmp.group())
                    if tmp2:
                        #   文字の大きさ
                        if tmp2.group(u'name') == u'小さ':
                            if tmp2.group(u'size') == u'１':
                                sSizeTmp = u'small'
                            if tmp2.group(u'size') == u'２':
                                sSizeTmp = u'x-small'
                        elif tmp2.group( u'size' ) == u'１':
                            sSizeTmp = u'large'
                        elif tmp2.group( u'size' ) == u'２':
                            sSizeTmp = u'x-large'
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'<span size="%s">' % sSizeTmp
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reOwari.match(tmp.group())
                    if tmp2:
                        #   </span>生成用共通処理
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'</span>'
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reMama.match(tmp.group())
                    if tmp2 == None:
                        tmp2 = Aozora.reMama2.match(tmp.group())
                    if tmp2:
                        #   ママ注記
                        sNameTmp = tmp2.group(u'name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()])
                        retline += u'｜%s《%s》' % ( sNameTmp, tmp2.group(u'mama') )
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reRubimama.match(tmp.group())
                    if tmp2:
                        #   ルビのママ
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'《%s》' % u'(ルビママ)'
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reBouten.match(tmp.group())
                    if tmp2:
                        #   傍点
                        #   rstrip では必要以上に削除する場合があるので
                        #   reのsubで消す
                        sNameTmp = tmp2.group('name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()])
                        retline += u'｜%s《%s》' % (
                                    sNameTmp,
                                    self.zenstring(
                                        self.boutentype(tmp2.group('type')),
                                                len(sNameTmp)))
                        priortail = tmp.end()
                        continue

                    if tmp.group() == u'［＃傍点］':
                        #   傍点　形式２
                        retline += lnbuf[priortail:tmp.start()]
                        tmp2 = Aozora.reBouten2.search(lnbuf[tmp.end():])
                        if tmp2:
                            sNameTmp = tmp2.group('name')
                            retline += u'｜%s《%s》' % (
                                        sNameTmp,
                                        self.zenstring(
                                            self.boutentype(''),
                                                    len(sNameTmp)))
                            priortail = tmp.end() + tmp2.end()
                        else:
                            priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reBousen.match(tmp.group())
                    if tmp2:
                        #   傍線
                        sNameTmp = tmp2.group(u'name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()] )
                        retline += u'｜%s《%s》' % (
                                    sNameTmp,
                                    self.zenstring(u'━━', len(sNameTmp)))
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reNijuBousen.match(tmp.group())
                    if tmp2:
                        #   二重傍線
                        sNameTmp = tmp2.group(u'name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()] )
                        retline += u'｜%s《%s》' % (
                                    sNameTmp,
                                    self.zenstring(u'〓〓', len(sNameTmp)))
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reGyomigikogaki.match(tmp.group())
                    if tmp2:
                        #   行右小書き
                        #   pango のタグを流用
                        sNameTmp = tmp2.group(u'name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()] )
                        retline += u'<sup>%s</sup>' % tmp2.group(u'name')
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reShitatsukiKomoji.match(tmp.group())
                    if tmp2:
                        #   下付き小文字 -> 行左小書き
                        #   pango のタグを流用
                        sNameTmp = tmp2.group(u'name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()] )
                        retline += u'<sub>%s</sub>' % tmp2.group(u'name')
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reFutoji.match(tmp.group())
                    if tmp2:
                        #   太字
                        #   pango のタグを流用
                        tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                        retline += lnbuf[priortail:tmpStart]
                        retline += u'<span font_desc="Sans bold">%s</span>' % lnbuf[tmpStart:tmpEnd]
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reFutoji2.match(tmp.group())
                    if tmp2:
                        #   太字  形式2
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'<span font_desc="Sans bold">'
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reSyatai.match(tmp.group())
                    if tmp2:
                        #   斜体
                        #   pango のタグを流用
                        tmpStart,tmpEnd = self.honbunsearch(
                                        lnbuf[:tmp.start()],tmp2.group(u'name'))
                        retline += lnbuf[priortail:tmpStart]
                        retline += u'<span style="italic">%s</span>' % lnbuf[tmpStart:tmpEnd]
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reSyatai2.match(tmp.group())
                    if tmp2:
                        #   斜体  形式2
                        retline += lnbuf[priortail:tmp.start()]
                        retline += u'<span style="italic">'
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reKuntenOkuri.match(tmp.group())
                    if tmp2:
                        #   訓点送り仮名
                        #   pango のタグを流用
                        retline += u'%s<sup>%s</sup>' % (
                            lnbuf[priortail:tmp.start()], tmp2.group(u'name'))
                        priortail = tmp.end()
                        continue

                    tmp2 = Aozora.reKaeriten.match(tmp.group())
                    if tmp2:
                        #   返り点
                        #   pango のタグを流用
                        retline += u'%s<sub>%s</sub>' % (
                            lnbuf[priortail:tmp.start()], tmp2.group(u'name'))
                        priortail = tmp.end()
                        continue

                    #   上記以外のタグは後続処理に引き渡す
                    retline += lnbuf[priortail:tmp.end()]
                    priortail = tmp.end()

                retline += lnbuf[priortail:]

                if footerflag:
                    """ フッタにおける年月日を漢数字に置換
                    """
                    ln = u''
                    priortail = 0
                    for tmp in Aozora.reNenGetsuNichi.finditer(retline):
                        ln += retline[priortail:tmp.start()]
                        priortail = tmp.end()
                        for s in tmp.group():
                            try:
                                ln += u'〇一二三四五六七八九'[eval(s)]
                            except:
                                ln += s

                    ln += retline[priortail:]
                    retline = ln

                """ 処理の終わった行を返す
                """
                yield u'%s\n' % retline

    def boutentype(self, t):
        if t == u'白ゴマ':
            rv = u'﹆　' # 1-3-29
        elif t == u'丸':
            rv = u'●　'
        elif t == u'白丸':
            rv = u'○　'
        elif t == u'黒三角':
            rv = u'▲　'
        elif t == u'白三角':
            rv = u'△　'
        elif t == u'二重丸':
            rv = u'◎　'
        elif t == u'蛇の目':
            rv = u'　◉'  # 1-3-27
        elif t == u'ばつ':
            rv = u'　×'
        else:
            rv = u'　﹅'
        return rv

    def honbunsearch(self, honbun, name):
        """ 本文中に出現する name を検索し、
            その出現範囲を返す。
            name との比較に際して
                ルビ、<tag></tag>、［］は無視される。
            比較は行末から行頭に向かって行われることに注意。
        """
        start = -1
        end = -1
        l = len(name)
        pos = len(honbun)
        inRubi = False
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
            elif inRubi:
                pass
            else:
                if name[l-1] == honbun[pos]:
                    if end < 0:
                        end = pos
                    start = pos
                    l -= 1
                    continue
                else:
                    # Missmatch
                    break
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


        with file( self.destfile, 'w' ) as dfile:
            self.linecounter = 0                # 出力した行数
            self.pagecounter = 0                # 出力したページ数
            self.pageposition=[] # フォーマット済ファイルにおける各ページの絶対位置
            self.pageposition.append(dfile.tell())  # 1頁目のファイル位置を保存
            self.midashi = u''
            self.inMidashi = False
            self.inFukusuMidashi = False        # 複数行におよぶ見出し
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

            with file( self.mokujifile, 'w' ) as self.mokuji_f:
                for lnbuf in self.formater_pass1():
                    lnbuf = lnbuf.rstrip('\n')
                    """ 空行の処理
                    """
                    if len(lnbuf) == 0:
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
                                #self.write2file( dfile, '\n' )
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

                            figspan = int(round(float(tmpWidth)/float(self.get_value(u'linewidth'))+0.5,0))
                            if self.linecounter + figspan >= int(self.get_value(u'lines')):
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

                        """ 改ページ
                        """
                        if Aozora.reKaipage.match(tmp.group()) != None:
                            while self.write2file( dfile, '\n' ) != True:
                                pass
                            retline += lnbuf[priortail:tmp.start()]
                            priortail = tmp.end()
                            continue

                        """ 見出し
                            ここでは正確なページ番号が分からないので、
                            見出し出現のフラグだけ立てて、目次作成は後段で行う。
                            複数行見出しはサポートしない
                            <span font_family="Sans" size="larger">
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
                            retline += u'<span font_family="Sans"'
                            if self.sMidashiSize == u'大':
                                retline += u' size="larger"'
                            #elif self.sMidashiSize == u'中':
                            #    retline += u' style="italic"'
                            retline += u'>%s</span>' % lnbuf[tmpStart:tmpEnd]
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
                            retline += u'<span font_family="Sans"'
                            if self.sMidashiSize == u'大':
                                retline += u' size="larger"'
                            retline += u'>'
                            priortail = tmp.end()
                            continue

                        matchMidashi = Aozora.reMidashi2owari.match(tmp.group())
                        if matchMidashi != None:
                            # <見出し終わり>
                            self.inFukusuMidashi = False
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            retline += lnbuf[priortail:tmp.start()]
                            retline += u'</span>'
                            priortail = tmp.end()
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

                        tmp2 = Aozora.reIndentEnd.match(tmp.group())
                        if tmp2:
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
                        tmp2 = Aozora.reJiage.match(tmp.group())
                        if tmp2:
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
                                        if u'仝〆〇ヶ〻々'.find(s) != -1:
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

                    """ 行をバッファ(中間ファイル)へ吐き出す
                    """
                    jisage3 = jisage
                    while lnbuf != '':
                        #   1行の表示桁数の調整
                        currchars = self.charsmax - jiage
                        if jizume > 0:
                            if jisage + jizume > currchars:
                                jizume = currchars - jisage
                            currchars = jisage + jizume

                        #   インデントの挿入
                        if jisage > 0:
                            sIndent = self.zenstring(u'　',jisage)
                            lnbuf = sIndent + lnbuf
                            rubiline = sIndent + sIndent + rubiline

                        #   ブロック地付きあるいは字上げ
                        if inJiage == True:
                            lenN = self.linecount(lnbuf)
                            if lenN <= self.charsmax:
                                sPad = self.zenstring(u'　',self.charsmax -lenN -jiage)
                                lnbuf = sPad + lnbuf
                                rubiline = sPad + sPad + rubiline
                        else:
                            #   地付きあるいは字上げ
                            tmp2 = Aozora.reJiage.match(lnbuf)
                            if tmp2:
                                try:
                                    # 字上げ n
                                    n = self.zentoi(tmp2.group('number'))
                                except:
                                    # 地付き
                                    n = 0
                                sP = u'' if tmp2.group('name2' ) == None else tmp2.group('name2' )
                                lenP = self.linecount(sP)
                                sN = u'' if tmp2.group('name' ) == None else tmp2.group('name' )
                                lenN = self.linecount(sN)
                                if  lenP + lenN <= self.charsmax:
                                    # 表示が1行分に収まる場合は処理する。
                                    sPad = self.zenstring(u'　',self.charsmax -lenP -lenN -n)
                                    lnbuf = sP + sPad + sN
                                    # ルビ表示 地付きタグ分を取り除くこと
                                    rubiline = rubiline[:lenP*2] + sPad + sPad + rubiline[lenP*2+len(tmp2.group('tag'))*2 :]

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

    def linecount(self, sline):
        """ 文字列の長さを数える
            <tag></tag> はカウントしない。
        """
        l = 0
        inTag = False
        for s in sline:
            if s == u'<':
                inTag = True
            elif s == u'>':
                inTag = False
            elif inTag:
                pass
            else:
                l += 1
        return l

    def linesplit(self, sline, rline, smax=0):
        """ 文字列を分割する
            <tag></tag> はカウントしない。
            半角文字は0.5文字として数え、合計時に切り上げる。
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

        """ 前回の呼び出しで引き継がれたタグがあれば付け足す。
        """
        while self.tagstack != []:
            sline = self.tagstack.pop() + sline

        for lsc in sline:
            if inSplit:
                # 本文の分割
                honbun2 += lsc
                continue

            if smax > 0:
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
                        self.tagstack.pop()
                    except:
                        pass
                else:
                    self.tagstack.append(tagname)
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
                # 画面上における全長を計算 (ifの条件式に注意)
                if unicodedata.category(lsc) == 'Lu':
                    # ラテン大文字(A-Z等)
                    lcc += 1
                elif unicodedata.east_asian_width(lsc) == 'Na':
                    # 非全角文字
                    lcc += 0.5
                else:
                    # 全角文字
                    lcc += 1

        """ 行末禁則処理
            次行先頭へ追い出す
            禁則文字が続く場合は全て追い出す
        """
        while Aozora.kinsoku2.find(honbun[-1]) != -1:
            honbun2 = honbun[-1] + honbun2
            honbun = honbun[:-1] + u'　'
            try:
                # ルビも同様に処理
                rubi2 = rubi[-2:]+rubi2
                rubi = rubi[:-2] + u'　　'#u'＊＊'
            except:
                pass

        """ 行頭禁則処理 ver 2
            前行末にぶら下げる。
            但し2文字(以上)続く場合は括弧類ならさらにぶら下げ、
            それ以外は前行の末尾をチェックし、非禁則文字なら
            行頭へ追い込む。
            例）シ　(改行) ャーロック・ホームズ ->
                (改行)シャーロック・ホームズ
        """
        if len(honbun2) > 0:
            if Aozora.kinsoku.find(honbun2[0]) != -1:
                honbun += honbun2[0]
                honbun2 = honbun2[1:]
                try:
                    # ルビも同様に処理
                    rubi = rubi + rubi2[:2]
                    rubi2 = rubi2[2:]
                except:
                    pass

                if len(honbun2) > 0:
                    if Aozora.kinsoku.find(honbun2[0]) != -1:
                        if Aozora.kinsoku4.find(honbun2[0]) != -1:
                            # ２文字目もぶら下げ
                            honbun += honbun2[0]
                            honbun2 = honbun2[1:]
                            try:
                                # ルビも同様に処理
                                rubi = rubi + rubi2[:2]
                                rubi2 = rubi2[2:]
                            except:
                                pass
                        else:
                            # 括弧類以外（もっぱら人名対策）
                            if Aozora.kinsoku.find(honbun[-2]) == -1:
                                honbun2 = honbun[-2:] + honbun2
                                honbun = honbun[:-2] + u'　　'
                                # ルビも同様に処理
                                try:
                                    rubi2 = rubi[-4:]+rubi2
                                    rubi = rubi[:-4] + u'　　　　'
                                except:
                                    pass


        """ くの字記号の分離を阻止する
            行頭禁則と重なるととんでもないことに！
        """
        if len(honbun2) > 0:
            if honbun2[0] == u'〵':
                if u'〳〴'.find(honbun[r-1]) != -1:
                    honbun +=  honbun2[0]
                    honbun2 = honbun2[1:]
                    # ルビも同様に処理
                    try:
                        rubi = rubi + rubi2[0] + rubi2[1]
                        rubi2 = rubi2[2:]
                    except:
                        pass

        """ tag の処理
            閉じていなければ一旦閉じ、次回の呼び出しに備えて
            スタックに積み直す
        """
        substack = []
        while self.tagstack != []:
            s = self.tagstack.pop()
            substack.append(s)
            honbun += u'</%s>' % s.split()[0].rstrip(u'>').lstrip(u'<')
        while substack != []:
            self.tagstack.append(substack.pop())

        return ( honbun,  honbun2, rubi, rubi2 )

    def write2file(self, fd, s, rubiline=u'\n' ):
        """ formater 下請け
            1行出力後、改ページしたらその位置を記録して True を返す。
            目次作成もここで行う。
            出力時の正確なページ数と行数が分かるのはここだけ。
        """
        rv = False
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
            else:
                self.mokuji_f.write( sMokujiForm % (
                    self.midashi.lstrip(u' 　').rstrip('\n'), self.pagecounter +1))
                self.inMidashi = False

        if self.loggingflag:
            logging.debug( u'　位置：%dページ、%d行目' % (
                                    self.pagecounter+1,self.linecounter+1 ))
            self.loggingflag = False

        fd.write(rubiline)  # 右ルビ行
        fd.write(s)         # 本文
        self.linecounter += 1
        if self.linecounter >= self.pagelines:
            # 1頁出力し終えたらその位置を記録する
            self.pagecounter += 1
            self.pageposition.append(fd.tell())
            self.linecounter = 0
            rv = True
        return rv

    def do_format(self, s):
        """ フォーマット処理一式
        """
        self.set_source(s)
        self.formater()

    #
    #   雑関数
    #
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
    def __init__(self):#, resolution = u'XGA'):
        Aozora.__init__(self)
        self.resize()

        self.reFormater = re.compile( ur'<[/a-z0-9A-Z]+?>')
        self.reBold = re.compile(ur'<b>(?P<text>.*)' )
        self.reBoldoff = re.compile(ur'(?P<text>.*)</b>' )

    def resize(self):
        self.canvas_width = int(self.get_value( u'scrnwidth' ))
        self.canvas_height = int(self.get_value( u'scrnheight'))
        self.canvas_topmargin = int(self.get_value( u'topmargin'))
        self.canvas_rightmargin = int(self.get_value( u'rightmargin' ))
        self.canvas_fontsize = int(self.get_value( u'fontsize' ))
        self.canvas_rubisize = int(self.get_value( u'rubifontsize' ))
        self.canvas_linewidth = int(self.get_value(u'linewidth'))
        self.canvas_rubispan = int(self.get_value(u'rubiwidth'))
        self.canvas_fontname = self.get_value(u'fontname')

    def writepage(self, pagenum, buffname=None):
        """ 指定したページを表示する
        """
        reFig = re.compile( ur'^(?P<filename>.+?),(?P<width>[0-9]+?),(?P<height>[0-9]+?),(?P<lines>[0-9]+?),(?P<rasio>[0-9]+?\.[0-9]+?)$' )
        if buffname == None:
            buffname = self.get_outputname()

        xpos = self.canvas_width - self.canvas_rightmargin

        self.pageinit()
        with file(buffname, 'r') as f0:
            try:
                f0.seek(self.pageposition[pagenum])
            except:
                logging.error( u'SeekError Page number %d' % pagenum )
            else:
                for i in xrange(self.pagelines):
                    sRubiline = f0.readline()
                    s0 = f0.readline()
                    matchFig = reFig.search(s0)
                    if matchFig != None:
                        # 挿図処理
                        try:
                            img = cairo.ImageSurface.create_from_png(os.path.join(self.get_value(u'aozoracurrent'), matchFig.group('filename')))
                        except cairo.Error, m:
                            logging.error( u'挿図処理中 %s %s/%s' % (
                                                m,
                                                self.get_value(u'aozoracurrent'),
                                                matchFig.group('filename')  ))

                        context = cairo.Context(self.sf)
                        # 単にscaleで画像を縮小すると座標系全てが影響を受ける
                        context.scale(float(matchFig.group('rasio')), float(matchFig.group('rasio')))
                        context.set_source_surface(img,
                                round((xpos + int(matchFig.group('lines'))/2 - \
                                   ((int(matchFig.group('lines')) * \
                                   self.canvas_linewidth))) /   \
                                   float(matchFig.group('rasio'))+0.5,0),
                                        self.canvas_topmargin)
                        context.paint()
                    else:
                        self.writepageline(
                                xpos,
                                self.canvas_topmargin,
                                '<span font_desc="%s %d">%s</span><span font_desc="%s %d">%s</span>' % (
                                    self.get_value(u'fontname'), self.canvas_rubisize, sRubiline,
                                        self.get_value(u'fontname'), self.canvas_fontsize, s0 )  ,
                                self.canvas_fontsize )
                    xpos -= self.canvas_linewidth
        self.pagefinish()

    def write_a_line(self, s):
        """ 画面中央に1行表示する
            スタートアップ用
        """
        self.pageinit()
        self.writepageline(self.canvas_width / 2, 48, s )
        self.pagefinish()

    def pageinit(self):
        """ ページ初期化
        """
        # キャンバスの確保
        self.sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                        self.canvas_width,
                                        self.canvas_height)

        """ 表示フォントの設定
        """
        self.font = pango.FontDescription(u'%s %s' % (self.get_value( u'fontname' ),
                                                self.get_value(u'fontsize')))
        self.font_rubi = pango.FontDescription(u'%s %s' % (self.get_value( u'fontname' ),
                    str(-1+int(round(int(self.get_value(u'fontsize'))/2-0.5)))))
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

    def writepageline(self, x, y, s='', honbunsize=12):
        """ 指定位置へ1行書き出す
        """
        # cairo コンテキストの作成と初期化
        context = cairo.Context(self.sf)
        context.set_antialias(cairo.ANTIALIAS_GRAY)
        context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        (nR,nG,nB)=self.convcolor(self.get_value(u'fontcolor'))
        context.set_source_rgb(nR,nG,nB) # 描画色

        # pangocairo の コンテキストをcairoコンテキストを元に作成
        pangocairo_context = pangocairo.CairoContext(context)
        pangocairo_context.translate(x, y)         # 描画位置

        """ 縦書き（上から下へ）に変更
            PI/2(90度)右回転、すなわち左->右書きが上->下書きへ
        """
        pangocairo_context.rotate(3.1415/2)

        """ レイアウトの作成
        """
        layout = pangocairo_context.create_layout()

        """ 表示フォントの設定
        """
        self.font.set_size(pango.SCALE*honbunsize)
        layout.set_font_description(self.font)
        """ フォントの回転
            これをやらないとROTATEの効果で横倒しのままになる。
            フォントによっては句読点の位置はおかしいまま。
            pango 1.30.0 にバグ
                rotate, gravity の効果を勘案し、日本語縦書きの場合は「」を
                回転しないで表示する。が、rotate, gravityの効果が横書きと
                変わらない場合、「」を回転してしまう。
        """
        ctx = layout.get_context() # Pango を得る
        ctx.set_base_gravity( 'east' )

        layout.set_markup(
                s if s.find( u'&' ) == -1 else Aozora.reAmp.sub(u'&amp;', s) )
        pangocairo_context.update_layout(layout)
        pangocairo_context.show_layout(layout)

    def pagefinish(self):
        self.sf.write_to_png( self.get_value(u'workingdir') + '/thisistest.png' )
        self.sf.finish()



