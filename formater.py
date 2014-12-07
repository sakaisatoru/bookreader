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


    サポートされる青空文庫の制御文字列
        ［＃改ページ］
        ［＃大見出し］［＃中見出し］［＃小見出し］
        ［＃改段］ 　　　［＃改ページ］ 　　　［＃改丁］（次の左ページからはじめる)
        ［＃ここから○字下げ］［＃ここで字下げ終わり］
        ［＃ここから○字下げ、折り返して●字下げ］
        ［＃ここから改行天付き、折り返して○字下げ］
        ［＃地付き］
        ［＃ここから地付き］［＃ここで地付き終わり］
        ［＃地から○字上げ］
        ［＃ここから地から○字上げ］［＃ここで字上げ終わり］
        挿図

    サポートされないもの
        ［＃ページの左右中央］

"""

from __future__ import with_statement

from jis3 import gaiji
from readersub import ReaderSetting, AozoraDialog
from aozoracard import AuthorList
import sys, codecs, re, os.path, datetime, unicodedata
from threading import Thread
import gtk, cairo, pango, pangocairo, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)


class Aozora(ReaderSetting):
    """
    """
    reHeader = re.compile( ur'^-------------------------------------------------------' )
    reFooter = re.compile( ur'^底本：' )
#        reGaiji = re.compile( ur'(※.*?［＃.*?\d+?\-\d+?\-\d+\d*.*?］)' )
#        reGaijiNumber = re.compile( ur'(※.*?［＃.*?(?P<number>\d+\-\d+\-\d+\d*))' )

    reGaiji = re.compile( ur'(※.*?［＃.*?\d+?\-\d+?\-\d+\d*.*?］)' )
    reGaijiNumber = re.compile( ur'(※.*?［＃.*?(?P<number>\d+\-\d+\-\d+\d*).*?］)' )

    reKunoji = re.compile( ur'(／＼)' )
    reGunoji = re.compile( ur'(／″＼)' )
    reCTRL = re.compile( ur'(?P<aozoratag>［＃.*?］)' )
    reHansoku = re.compile( ur'(【＃(?P<name>.+?)】)' )
    reNonokagi = re.compile( ur'(“(?P<name>.+?)”)' )

    reBouten = re.compile( ur'(［＃「(?P<name>.+?)」に(?P<type>.*?)傍点］)' )
    reBouten2 = re.compile( ur'((?P<name>.*?)［＃傍点終わり］)' )
    reBousen = re.compile( ur'(［＃「(?P<name>.+?)」に傍線］)' )
    reNijuBousen = re.compile( ur'(［＃「(?P<name>.+?)」に二重傍線］)' )
    reGyomigikogaki = re.compile( ur'(［＃「(?P<name>.+?)」は行右小書き］)' )

    reOmit = re.compile(
                ur'(［＃ここからキャプション］)|' +
                ur'(［＃ここでキャプション終わり］)|'+
                ur'(［＃「.*?」はキャプション］)|' +
                ur'(［＃ここから横組み］)|'+
                ur'(［＃ここで横組み終わり］)|' +
                ur'(［＃「.+?」は縦中横］)|' +
                ur'(［＃.+?段階.+?な文字］)|' +
                ur'(［＃.+?な文字終わり］)|' +
                ur'(［＃行右小書き.*?］)|' +
                ur'(［＃割り注.*?］)')

    reSokobon = re.compile( ur'(［＃「.+?」は底本では「.+?」］)' )

    reRubi = re.compile( ur'《.*?》' )
    reRubiclr = re.compile( ur'＃' )
    reIndent = re.compile( ur'［＃(?P<number>[０-９]+?)字下げ］' )
    reIndentStart = re.compile( ur'［＃.+?(?P<number>[０-９]+?)字下げ］' )
    reIndentEnd = re.compile( ur'［＃ここで字下げ終わり］|［＃字下げおわり］')
    reJiage = re.compile( ur'［＃地から(?P<number>[０-９]+?)字上げ］' )
    reJitsuki = re.compile( ur'［＃地付き］' )
    reMidashi = re.compile( ur'［＃「(?P<midashi>.+?)」は(?P<dougyou>.*?)(?P<midashisize>大|中|小)見出し］' )
    reKaipage = re.compile( ur'［＃改ページ］|［＃改丁］' )
    reFig = re.compile( ur'［＃.*?（(?P<filename>fig.+?)、横(?P<width>[0-9]+?)×縦(?P<height>[0-9]+?)）入る］' )
    reSayuuchuou = re.compile( ur'［＃ページの左右中央］' )
    reMidashi2 = re.compile( ur'(［＃(?P<midashisize>大|中|小)見出し］)' )
    reMidashi2owari = re.compile( ur'(［＃(?P<midashisize>大|中|小)見出し終わり］)' )

    kinsoku = u'\r,)]｝、）］｝〕〉》」』】〙〗〟’”｠»ヽヾーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻‐゠–〜?!‼⁇⁈⁉・:;。、！？'
    kinsoku2 = u'([{（［｛〔〈《「『【〘〖〝‘“｟«'
    kinsoku3 = u'〳〴〵' # —…‥


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
                if lnbuf == '-------------------------------------------------------' or len(lnbuf) == 0:
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
            formater より呼び出されるジェネレータ。1行読み込んでもっぱら置換処理を
            行い、出力する。

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

                未実装なタグ（単純に削除される）
                    底本注記、キャプション、横組み、縦中横、文字の大きさ、
                    行右小書き、割注

                その他のものは、そのまま本文に埋め込んで後続処理に引き渡される。
        """
        if sourcefile == None:
            sourcefile = self.sourcefile

        headerflag = False      # 書名以降の注釈部分を示す
        footerflag = False
        gaijitest = gaiji()

        with codecs.open( sourcefile, 'r', self.readcodecs ) as f0:
            for lnbuf in f0:
                lnbuf = lnbuf.rstrip('\r\n')
                #
                #   空行の処理
                #
                if len(lnbuf) == 0:
                    yield u'\n'
                    continue

                #
                #   ヘッダ【テキスト中に現れる記号について】の処理
                #   とりあえずばっさりと削除する
                #
                if Aozora.reHeader.search(lnbuf) != None:
                    if headerflag == False:
                        headerflag = True
                    else:
                        headerflag = False
                    continue
                if headerflag == True:
                    continue

                #
                #   フッタ
                #
                if Aozora.reFooter.search(lnbuf) != None:
                    footerflag = True

                #
                #   単純置換処理各種
                #

                if footerflag == True:
                    #
                    #   フッタにおける年月日を漢数字に置換
                    #
                    ln = u''
                    for s in lnbuf:
                        if unicodedata.name(s).split()[0] == 'DIGIT':
                            try:
                                ln += u'〇一二三四五六七八九'[eval(s)]
                            except:
                                ln += s
                        else:
                            ln += s
                    lnbuf = ln

                #
                #   青空文庫の制御文字列である　［＃］を【＃】と表記する
                #   テキストへの対応
                #   ex. 絶対矛盾的自己同一　西田幾多郎
                #
                try:
                    for mTmp in Aozora.reHansoku.finditer( lnbuf ):
                        lnbuf ='%s［＃%s］%s' % (
                             lnbuf[:mTmp.start()],
                            mTmp.group('name'),
                            lnbuf[mTmp.end():] )
                except:
                    pass

                #
                #   くの字の置換
                #
                lnbuf = Aozora.reKunoji.sub( u'〳〵', lnbuf )
                lnbuf = Aozora.reGunoji.sub( u'〴〵', lnbuf )

                #
                #   ダブルクォーテーションの、ノノカギへの置換
                #   unicode のカテゴリを調べて、アルファベット以外及び記号以外の
                #   何かが出現した場合に日本語とみなして置換する。
                #
                try:
                    for mTmp in Aozora.reNonokagi.finditer( lnbuf ):
                        for s in mTmp.group('name'):
                            if unicodedata.category(s) == 'Lo':
                                lnbuf = '%s〝%s〟%s' % (
                                     lnbuf[:mTmp.start()],
                                    mTmp.group('name'),
                                    lnbuf[mTmp.end():] )
                                break
                except:
                    pass

                #
                #   外字
                #
                ln = ''
                for s in Aozora.reGaiji.split(lnbuf):
                    gaijim = Aozora.reGaijiNumber.search(s)
                    if gaijim != None:
                        k = gaijitest.sconv(gaijim.group('number'))
                        if k != None:
                            s = k
                    ln += s
                lnbuf = ln


                #
                #   ［＃　で始まるタグの処理
                #


                priortail = 0
                retline = u''
                for tmp in Aozora.reCTRL.finditer(lnbuf):
                    tmp2 = Aozora.reBouten.match(tmp.group())
                    if tmp2:
                        #
                        #   傍点
                        #   rstrip では必要以上に削除する場合があるので
                        #   reのsubで消す
                        #
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
                        #
                        #   傍点　形式２
                        #
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
                        #
                        #   傍線
                        #
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
                        #
                        #   二重傍線
                        #
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
                        #
                        #   行右小書き
                        #   ルビとして掃きだす
                        #
                        sNameTmp = tmp2.group(u'name')
                        reTmp = re.compile( ur'%s$' % sNameTmp )
                        retline += reTmp.sub( u'', lnbuf[priortail:tmp.start()] )
                        l = int(round(len(sNameTmp) / 2 - 0.5))
                        retline = u'%s｜%s《%s》' % (
                                retline[:-l],retline[-l:len(retline)], sNameTmp)
                        priortail = tmp.end()
                        continue

                    if Aozora.reSokobon.match(tmp.group()):
                        #
                        #   底本標記に関する付記　とりあえず削除
                        #
                        print u'削除されたタグ: ', tmp.group()
                        retline += lnbuf[priortail:tmp.start()]
                        priortail = tmp.end()
                        continue

                    if Aozora.reOmit.match(tmp.group()):
                        #
                        #   未実装タグは単純に削除する
                        #
                        print u'削除されたタグ: ', tmp.group()
                        retline += lnbuf[priortail:tmp.start()]
                        priortail = tmp.end()
                        continue

                    #
                    #   上記以外のタグは後続処理に引き渡す
                    #
                    retline += lnbuf[priortail:tmp.end()]
                    priortail = tmp.end()

                retline += lnbuf[priortail:]

                #
                #   処理の終わった行を返す
                #
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

    def formater( self, output_file=None, mokuji_file=None ):
        """ フォーマッタ
        """
        if output_file != None:
            self.destfile = output_file
        if mokuji_file != None:
            self.mokujifile = mokuji_file

        (self.BookTitle, self.BookAuthor) = self.get_booktitle_sub()

        with file( self.destfile, 'w' ) as dfile:
            self.linecounter = 0                        # 出力した行数
            self.pagecounter = 0                        # 出力したページ数
            self.pageposition=[]                        # フォーマット済ファイルにおける各ページの絶対位置
            self.pageposition.append(dfile.tell())      # 1頁目のファイル位置を保存
            self.iCurrentReadline = 0
            self.sIndent = u''
            self.onetime_indent = True
            self.sJiage = u''
            self.onetime_jiage = False
            self.midashi = False

            with file( self.mokujifile, 'w' ) as self.mokuji_f:

                for self.lnbuf in self.formater_pass1():
                    self.rubibuf = u''
                    self.lnbuf = self.lnbuf.rstrip('\n')
                    self.iCurrentReadline += 1
                    """ 空行の処理
                    """
                    if len(self.lnbuf) == 0:
                        self.write2file( dfile, '\n' )
                        continue

                    """ 制御文字列の処理
                        読み込んだ行に含まれる［＃.*?］を全てチェックする。
                    """
                    self.ln2 = ''
                    IndentJitsuki = False
                    for s in Aozora.reCTRL.split(self.lnbuf):
                        """ 挿図
                            キャンバスの大きさに合わせて画像を縮小する。
                            ページからはみ出るようであれば改ページを挿入する。

                            キャンバス　880px x 616px, 行29 の場合、1行あたり30px
                            tmpRatio : 縮小倍率
                            tmpWidth : 画像横幅
                            figspan  : 画像幅の行数換算値
                        """
                        matchFig = Aozora.reFig.search(s)
                        if matchFig != None:
                            tmpH = float(self.get_value(u'scrnheight')) - float(self.get_value(u'bottommargin')) - float(self.get_value(u'topmargin'))
                            tmpW = float(self.get_value(u'scrnwidth')) - float(self.get_value(u'rightmargin')) - float(self.get_value(u'leftmargin'))
                            try:
                                tmpRasio = round(tmpH / float(matchFig.group('height')),2)
                                tmpRasioW = round(tmpW / float(matchFig.group('width')),2)
                            except ZeroDivisionError:
                                # 挿図指定に大きさがない場合への対処、とりあえず原寸
                                tmpRasio = 1.0
                                tmpRasioW = 1.0
                                tmpWidth = 100
                            else:
                                if tmpRasioW < tmpRasio:
                                    tmpRasio = tmpRasioW

                                if tmpRasio < 1:
                                    tmpWidth = int(round(float(matchFig.group('width')) * tmpRasio,0))
                                else:
                                    tmpWidth = int(matchFig.group('width'))

                            figspan = int(round(float(tmpWidth)/float(self.get_value(u'linewidth'))+0.5,0))
                            if self.linecounter + figspan >= int(self.get_value(u'lines')):
                                # 改ページ
                                while self.write2file( dfile, '\n' ) != True:
                                    pass
                            self.write2file( dfile, '%s,%s,%s,%d,%f\n' % (matchFig.group('filename'),
                                tmpWidth, matchFig.group('height'), figspan, tmpRasio ) )
                            figspan -= 1
                            while figspan > 0:
                                self.write2file( dfile, '\n' )
                                figspan -= 1
                            continue

                        """ ページの左右中央
                            後続の行数を知る術がないので割愛
                        """
                        if Aozora.reSayuuchuou.search(s) != None:
                            self.write2file( dfile, '\n' )
                            continue

                        """ 改ページ
                        """
                        if Aozora.reKaipage.search(s) != None:
                            while self.write2file( dfile, '\n' ) != True:
                                pass
                            continue

                        """ 見出し
                            複数行に渡る処理は行わない
                        """
                        matchMidashi = Aozora.reMidashi.search(s)
                        if matchMidashi != None:
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            s = ''
                            self.midashi = True

                        matchMidashi = Aozora.reMidashi2.search(s)
                        if matchMidashi != None:
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            s = ''
                            self.midashi = False

                        matchMidashi = Aozora.reMidashi2owari.search(s)
                        if matchMidashi != None:
                            self.sMidashiSize = matchMidashi.group('midashisize')
                            s = ''
                            self.midashi = True

                        """ ワンタイムインデント
                            sIndent に 桁数分の空白を得る
                        """
                        maIndent = Aozora.reIndent.match(s)
                        if maIndent != None:
                            self.sIndent = self.zenstring( u'　',
                                        self.zentoi(maIndent.group('number')))
                            s = ''
                            self.onetime_indent = True
                        #
                        #   地付き
                        #   ワンタイムインデントのバリエーションとして処理
                        #   sIndent に 桁数分の空白を得る
                        #   プログラムの都合上、タグの直後の要素が地付きとなる。
                        #   例）
                        #   ［＃地付き］ここが地付き［＃ダミー］←これはタグなので
                        #                                           地付きされない
                        #
                        if IndentJitsuki == True:
                            # ［＃地付き］の直後の要素の長さから必要な空白を得る
                            self.sIndent = self.zenstring( u'　',
                                self.charsmax - len(Aozora.reRubi.sub( u'',s)))
                            #self.sIndent = self.zenstring( u'　', self.chars - len(s))
                            self.onetime_indent = True
                            IndentJitsuki = False
                        maIndent = Aozora.reJitsuki.match(s)
                        if maIndent != None:
                            print u'Indent:',s
                            s = ''
                            IndentJitsuki = True
                            continue
                        #
                        #   ブロックインデント
                        #   sIndent に 桁数分の空白を得る
                        #
                        maIndent = Aozora.reIndentStart.match(s)
                        if maIndent != None:
                            self.sIndent = u''
                            self.onetime_indent = False
                            self.sIndent = self.zenstring( u'　',
                                        self.zentoi(maIndent.group('number')))
                            s = ''
                        #
                        #   ブロックインデント終わり
                        #
                        if Aozora.reIndentEnd.match(s) != None:
                            s = ''
                            self.sIndent = u''

                        #
                        #   ワンタイム字上げ
                        #
                        if self.onetime_jiage == True:
                            # ［＃地付き］の直後の要素の長さから必要な空白を得る
                            self.sIndent = self.zenstring( u'　',
                                self.charsmax - len(Aozora.reRubi.sub( u'', s )) - len(self.sJiage))
                            self.onetime_indent = True
                            self.onetime_jiage = False

                        maIndent = Aozora.reJiage.match(s)
                        if maIndent != None:
                            self.sJiage = self.zenstring( u'　',
                                        self.zentoi(maIndent.group('number')))
                            s = ''
                            self.onetime_jiage = True

                        #
                        #   未定義の ［＃］を捨てる
                        #
                        """
                        if Aozora.reCTRL.search(s) != None:
                            print u'DROP :', s
                            s = ''
                        """
                        self.ln2 += s

                    self.lnbuf = self.ln2
                    #
                    #   ルビの処理
                    #   本文に合わせてサイドライン(rubiline)に全角空白をセットする。
                    #   文字種が変わる毎にルビ掛かり始めとみなして、＃をセットする。
                    #   ルビが出現したら直前の ＃までバックしてルビをセットする。
                    #
                    rubiline = u''
                    self.ln2 = u''
                    inRubi = False
                    tplast = 0
                    tp = 0
                    rubispan = 0
                    isAnchor = False
                    for s in self.lnbuf:
                        if s == u'《':
                            isAnchor = False
                            inRubi = True
                            # 直前のルビ打ち込み位置までバック
                            r2 = rubiline.rstrip( u'　' )
                            r2 = r2.rstrip( u'＃' )
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
                        #if unicodedata.east_asian_width(s) != 'Na':
                        # 本文が全角文字であれば幅調整する
                        if rubispan < 0:
                            # ルビが本文より長い場合の調整
                            rubispan += 1
                        else:
                            rubiline += u'　' #u'／'

                        self.ln2 += s

                    rubiline = Aozora.reRubiclr.sub(u'　', rubiline)
                    self.lnbuf = self.ln2
                    rubi2 = u''
                    #
                    #   行をバッファ(中間ファイル)へ吐き出す
                    #
                    #   インデント幅分のスペース u'　' を行頭に付加されたソース
                    #   self.lnbuf を、
                    #   1行あたりの文字数 self.charsmax を 境にして分割、
                    #   行末禁則、行頭禁則を行った後、中間ファイルへ書き出す。
                    #
                    while self.lnbuf != '':
                        #
                        #   インデントの挿入
                        #
                        self.lnbuf = self.sIndent + self.lnbuf
                        rubiline = self.sIndent + self.sIndent + rubiline
                        if self.onetime_indent == True:
                            self.sIndent = u''

                        r, c, self.ls = self.sizeofline(self.lnbuf, self.charsmax)
                        #
                        #   画面上の1行で収まらなければ分割して次行を得る
                        #
                        if c >= self.charsmax:
                            self.lnbuf = self.lnbuf[r:]
                            # ルビの長さをチェックして必要であれば分割する
                            if len(rubiline) >= r * 2:
                                rubi2 = rubiline[:r*2]
                                rubiline = rubiline[r*2:]
                        else:
                            self.lnbuf = ''
                            rubi2 = rubiline
                            rubiline = u''
                        #
                        #   行末禁則処理
                        #   次行先頭へ追い出す
                        #   禁則文字が続く場合は全て追い出す
                        #
                        while True:
                            r = len(self.ls)
                            if Aozora.kinsoku2.find(self.ls[r-1]) != -1:
                                self.lnbuf = self.ls[r-1] + self.lnbuf
                                self.ls = self.ls[:r-1] + u'　'
                                # ルビも同様に処理
                                rubiline = rubi2[r*2-2]+rubi2[r*2-1]+rubiline
                                rubi2 = rubi2[:r*2-2] + u'　　'#u'＊＊'
                            else:
                                break

                        #
                        #   行頭禁則処理
                        #   前行末にぶら下げる。
                        #   2重処理まで。それ以上はそのまま。
                        #   例）。」　は2文字ともぶら下げる。
                        #
                        self.last = ''
                        if len(self.lnbuf) > 0:
                            if Aozora.kinsoku.find(self.lnbuf[0]) != -1:
                                self.last = self.lnbuf[0]
                                self.lnbuf = self.lnbuf[1:]
                                # ルビも同様に処理
                                try:
                                    rubi2 = rubi2 + rubiline[:2]
                                    rubiline = rubiline[2:]
                                except:
                                    pass
                                if len(self.lnbuf) >= 1:
                                    if Aozora.kinsoku.find(self.lnbuf[0]) != -1:
                                        self.last += self.lnbuf[0]
                                        self.lnbuf = self.lnbuf[1:]
                                        # ルビも同様に処理
                                        try:
                                            rubi2 = rubi2 + rubiline[:2]
                                            rubiline = rubiline[2:]
                                        except:
                                            pass
                        #
                        #   くの字記号の分離を阻止する
                        #   行頭禁則と重なるととんでもないことに！
                        #
                        if len(self.lnbuf) > 0:
                            if self.lnbuf[0] == u'〵':
                                if u'〳〴'.find(self.ls[r-1]) != -1:
                                    self.last +=  self.lnbuf[0]
                                    self.lnbuf = self.lnbuf[1:]
                                    # ルビも同様に処理
                                    try:
                                        rubi2 = rubi2 + rubiline[0] + rubiline[1]
                                        rubiline = rubiline[2:]
                                    except:
                                        pass
                        self.write2file( dfile, "%s%s\n" % (self.ls,self.last), "%s\n" % rubi2)

    def sizeofline(self, sline, smax=0 ):
        """ 文字列の長さを返す。
            但し半角文字は0.5文字として数え、合計時に切り捨てる。
            smax に達しても抜ける。
            戻りは実際の文字数と換算文字数を返す。
        """

        rv2 = 0     # 実際の文字数
        lcc = 0.0
        honbun = u''
        for lsc in sline:
            if smax > 0:
                if int(round(lcc-0.5)) >= smax:
                    break

            rv2 += 1
            honbun += lsc
            # 画面上における全長を計算
            if unicodedata.east_asian_width(lsc) == 'Na':
                # いわゆる半角文字
                lcc += 0.5
            else:
                # いわゆる全角文字
                lcc += 1
        return ( rv2, int(round(lcc-0.5)), honbun )

    def write2file(self, fd, s, rubiline=u'\n' ):
        """ formater 下請け
            1行出力後、改ページしたらその位置を記録して True を返す。
            目次作成もここで行う。
        """
        rv = False
        if self.midashi == True:
            #
            #   見出し処理
            #   とりあえず、書式固定
            #
            #print s
            if self.sMidashiSize == u'大':
                sMokujiForm = u'%-s  % 4d\n'
            elif self.sMidashiSize == u'中':
                sMokujiForm = u'  %-s  % 4d\n'
            elif self.sMidashiSize == u'小':
                sMokujiForm = u'    %-s  % 4d\n'
            self.mokuji_f.write( sMokujiForm % (s.lstrip(u' 　').rstrip('\n'),
                                    self.pagecounter +1))
            self.midashi = False

        fd.write(rubiline)  # ルビ等の修飾情報
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
        """
        r = ''
        while n > 0:
            r += s
            n -= 1
        return r


class CairoCanvas(Aozora):
    """ cairo / pangocairo を使って文面を縦書きする

        topmargin = 8
        rightmargin = 12
        linestep = 30 ( fontsize = u'小' )
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
                print u'SeekError Page number %d\n' % (pagenum,)
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
                            print m
                            print os.path.join(self.get_value(u'aozoracurrent'), matchFig.group('filename'))

                        context = cairo.Context(self.sf)
                        # 単にscaleで画像を縮小すると座標系全てが影響を受ける
                        context.scale(float(matchFig.group('rasio')), float(matchFig.group('rasio')))
                        context.set_source_surface(img,
                                round((xpos - ((int(matchFig.group('lines')) * self.canvas_linewidth))) / float(matchFig.group('rasio'))+0.5,0),
                                        self.canvas_topmargin)
                        context.paint()
                    else:
                        self.writepageline(xpos,
                                            self.canvas_topmargin,
                                            s0,
                                            self.canvas_fontsize)
                        self.writepageline(xpos+self.canvas_rubispan,
                                            self.canvas_topmargin,
                                            sRubiline,
                                            self.canvas_rubisize)
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
        #self.font.set_style(pango.STYLE_ITALIC)
        #self.font.set_weight(pango.WEIGHT_BOLD)
        #self.font.set_size(pango.SCALE*12) # pango.SCALE = 1024
        #self.font.set_stretch(pango.STRETCH_ULTRA_EXPANDED)
        self.font_rubi = pango.FontDescription(u'%s %s' % (self.get_value( u'fontname' ),
                    str(-1+int(round(int(self.get_value(u'fontsize'))/2-0.5)))))
        #self.font_rubi.set_weight(pango.WEIGHT_BOLD)
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

    def writepageline(self, x, y, s, fontsize=12):
        """ 指定位置へ1行書き出す
        """

        # cairo コンテキストの作成と初期化
        context = cairo.Context(self.sf)
        context.set_antialias(cairo.ANTIALIAS_GRAY)
        #context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        context.translate(x, y)         # 描画位置
        (nR,nG,nB)=self.convcolor(self.get_value(u'fontcolor'))
        context.set_source_rgb(nR,nG,nB) # 描画色
        # pangocairo の コンテキストをcairoコンテキストを元に作成
        pangocairo_context = pangocairo.CairoContext(context)

        """ 縦書き（上から下へ）に変更
            PI/2(90度)右回転、すなわち右->左書きが上->下書きへ
        """
        pangocairo_context.rotate(3.1415/2)

        """ レイアウトの作成
        """
        layout = pangocairo_context.create_layout()

        """ 表示フォントの設定
        """
        self.font.set_size(pango.SCALE*fontsize)
        layout.set_font_description(self.font)

        """ フォントの回転
            これをやらないとROTATEの効果で横倒しのままになる。
            フォントによっては句読点の位置はおかしいまま。
            pango 1.30.0 にバグ
                rotate, gravity の効果を勘案し、日本語縦書きの場合は「」を回転しないで
                表示する。が、rotate, gravityの効果が横書きと変わらない場合、「」を
                回転してしまう。
        """
        ctx = layout.get_context()
        ctx.set_base_gravity( 'east' )
        #
        #   太字タグの処理
        #
        mtmp = self.reBold.search(s)
        if mtmp != None:
            self.font.set_weight(pango.WEIGHT_BOLD)
            layout.set_font_description(self.font)
            s = mtmp.group('text')
        mtmp = self.reBoldoff.search(s)
        if mtmp != None:
            self.font.set_weight(pango.WEIGHT_NORMAL)
            layout.set_font_description(self.font)
            s = mtmp.group('text')

        layout.set_text( s )
        pangocairo_context.update_layout(layout)
        pangocairo_context.show_layout(layout)


    def pagefinish(self):
        self.sf.write_to_png( self.get_value(u'workingdir') + '/thisistest.png' )
        self.sf.finish()



