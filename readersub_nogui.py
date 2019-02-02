#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  readersub_nogui.py
#
#  Copyright 2015 sakaisatoru <endeavor2wako@gmail.com>
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

import os.path
import re
import logging
import math
import errno
import unicodedata
import subprocess

from contextlib import contextmanager

import cairo
import pango
import pangocairo



@contextmanager
def pangocairocontext(surface):
    try:
        context = cairo.Context(surface)
        pangoctx = pangocairo.CairoContext(context)
        yield pangoctx
    finally:
        del pangoctx
        del context


class AozoraScale(object):
    """ 描画時のピクセル長の計算等
    """

    # 禁則文字
    # 本来ここに含めるべきものでないが、独立させるほどのものでもないので、とりあえず居候。
    kinsoku = u'\r,)]｝）］｝〕〉》」』】〙〗〟’”｠»ヽヾ。、．，ーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻‐゠–〜?!‼⁇⁈⁉・:;！？'
    kinsoku2 = u'([{（［｛〔〈《「『【〘〖〝‘“｟«〳〴'
    kinsoku4 = u'\r,)]｝）］｝〕〉》」』】〙〗〟’”｠»。、．，'
    kinsoku5 = u'\r,)]｝）］｝〕〉》」』】〙〗〟、，'

    # Serif(TakaoEx明朝)における、対全角文字比
    charwidth_serif = {
            u' ':0.312500,  u'!':0.312500,  u'"':0.375000,  u'#':0.625000,
            u'$':0.625000,  u'&':0.750000,  u'%':0.812500,  u"'":0.200000,
            u'(':0.375000,  u')':0.375000,  u'*':0.250000,  u'+':0.687500,
            u',':0.250000,  u'-':0.315000,  u'.':0.250000,  u'/':0.500000,
            u'0':0.647058,  u'1':0.647058,  u'2':0.647058,  u'3':0.647058,
            u'4':0.647058,  u'5':0.647058,  u'6':0.647058,  u'7':0.647058,
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
            u'|':0.187500,  u'}':0.312500,  u'~':0.500000,

            u'¡':0.312500,  u'¿':0.500000,
            u'À':0.733333,  u'Á':0.733333,  u'Â':0.733333,  u'Ã':0.733333,
            u'Ä':0.733333,  u'Å':0.733333,  u'Ā':0.733333,
            u'Æ':1.000000,
            u'Ç':0.733333,
            u'È':0.666667,  u'É':0.666667,  u'Ê':0.666667,  u'Ë':0.666667,
            u'Ē':0.666667,
            u'Ì':0.400000,  u'Í':0.400000,  u'Î':0.400000,  u'Ï':0.400000,
            u'Ī':0.400000,
            u'Ñ':0.800000,
            u'Ò':0.800000,  u'Ó':0.800000,  u'Ô':0.800000,  u'Õ':0.800000,
            u'Ö':0.800000,  u'Ø':0.800000,  u'Ō':0.800000,
            u'Ù':0.800000,  u'Ú':0.800000,  u'Û':0.800000,  u'Ü':0.800000,
            u'Ū':0.800000,
            u'Ý':0.666667,
            u'ß':0.733333,
            u'à':0.562500,  u'á':0.562500,  u'â':0.562500,  u'ã':0.562500,
            u'ä':0.562500,  u'å':0.562500,  u'ā':0.562500,
            u'æ':0.875000,
            u'ç':0.562500,
            u'è':0.562500,  u'é':0.562500,  u'ê':0.562500,  u'ë':0.562500,
            u'ē':0.562500,
            u'ì':0.312500,  u'í':0.312500,  u'î':0.312500,  u'ï':0.312500,
            u'ī':0.312500,
            u'ñ':0.625000,
            u'ò':0.562500,  u'ó':0.562500,  u'ô':0.562500,  u'õ':0.562500,
            u'ö':0.562500,  u'ø':0.562500,  u'ō':0.562500,
            u'ù':0.625000,  u'ú':0.625000,  u'û':0.625000,  u'ü':0.625000,
            u'ū':0.625000,
            u'ý':0.562500,  u'ÿ':0.562500,
            u'Œ':1.050000,
            u'œ':0.875000 }

    # 文字サイズ変更への暫定対応(公比1.2、端数切り上げ、一部調整)
    fontsizefactor = {
            u'normal':1.0,
            u'size="smaller"':0.82,                 u'size="larger"':1.2000,
            u'size="small"':0.82,                   u'size="large"':1.2000,
            u'size="x-small"':0.6944444444444445,   u'size="x-large"':1.4400,
            u'size="xx-small"':0.578703703703703,   u'size="xx-large"':1.7280,
            u'<sup>':0.82,                          u'<sub>':0.82 }

    reFontsizefactor = re.compile( ur'(?P<name>size=".+?")' )
    reImgtag = re.compile( ur'<aozora img="(?P<name>.+?)" width="(?P<width>.+?)" height="(?P<height>.+?)">' )
    reAozoraHalf = re.compile(ur'<aozora half="(?P<name>.+?)">')



    def __init__(self):
        self.font_description = None
        self.fontheight = 0             # 縦書き時の１文字の高さ
        self.fontwidth = 0              # 縦書き時の１文字の幅
        pass

    def update_charwidth_2(self, font, size):
        self.update_charwidth(pango.FontDescription(u'%s %f' % (font,size)))

    def update_charwidth(self, font_des):
        """ 実際の表示幅から、英数字及び記号（latin）の対全角文字幅比を求める
        """
        if font_des != self.font_description:
            self.font_description = font_des
            canvas_width = 800
            canvas_height = 80
            sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                    canvas_width, canvas_height)

            with pangocairocontext(sf) as pangoctx:
                layout = pangoctx.create_layout()
                pc = layout.get_context() # Pango を得る
                pc.set_base_gravity('east')
                pc.set_gravity_hint('natural')
                layout.set_font_description(font_des)
                layout.set_text( u'国' )
                self.fontheight, self.fontwidth = layout.get_pixel_size()

                pc.set_base_gravity('south')
                pc.set_gravity_hint('natural')
                #layout.set_font_description(font_des)
                layout.set_text( u'国'*40 )
                span, length = layout.get_pixel_size()
                f_span = float(span)

                for s in self.charwidth_serif.iterkeys():
                    layout.set_text(s*40)
                    x, y = layout.get_pixel_size()
                    self.charwidth_serif[s] = x / f_span
                del layout
            del sf

    def linelengthcount(self, sline):
        """ 文字列の長さを数える
            文字の大きさ変更等に対応
            <tag></tag> はカウントしない。
        """
        l = 0.0
        inTag = False
        inTatenakayoko = False
        tagname = u''
        tagstack = []
        fontsizename = u'normal'
        adj = 1.0

        for s in sline:
            if inTag:
                tagname += s
                if s == u'>':
                    inTag = False
                    # tagスタックの操作
                    if tagname[:2] == u'</':
                        # </tag>の出現とみなしてスタックから取り除く
                        # ペアマッチの処理は行わない
                        if tagstack != []:
                            tmp = self.reFontsizefactor.search(tagstack[-1])
                            if tmp:
                                if tmp.group('name') in self.fontsizefactor:
                                    fontsizename = u'normal' # 文字サイズの復旧

                            elif u'aozora tatenakayoko' in tagstack[-1]:
                                    inTatenakayoko = False

                            elif self.reAozoraHalf.search(tagstack[-1]):
                                adj = 1.0 # 送り量の復旧

                            tagstack.pop()
                    else:
                        tmp = self.reFontsizefactor.search(tagname)
                        if tmp:
                            if tmp.group('name') in self.fontsizefactor:
                                fontsizename = tmp.group('name') # 文字サイズ変更
                        elif u'tatenakayoko' in tagname:
                            inTatenakayoko = True
                            l += 1.0 # 縦中横の高さは常に１、ここで加算する
                        else:
                            # 連続して出現する括弧
                            tmp = self.reAozoraHalf.search(tagname)
                            if tmp:
                                adj = float(tmp.group('name')) # 送り量調整

                        tagstack.append(tagname)
                        tagname = u''
            elif s == u'<':
                inTag = True
                tagname = s

            elif inTatenakayoko:
                # 縦中横の中身の高さは常に１なので、ここでは計算しない
                pass

            else:
                # 画面上における全長を計算
                l += self.charwidth(s) * self.fontsizefactor[fontsizename] * adj
        return int(math.ceil(l))

    def charwidth(self, lsc):
        """ 文字の幅を返す
            全角 を１とする
        """
        if lsc in self.charwidth_serif:
            lcc = self.charwidth_serif[lsc]
        elif unicodedata.east_asian_width(lsc) == 'H':
            # 半角カナ(青空文庫では未使用)
            lcc = 0.5
        else:
            # 全角文字扱い
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
                n = n * 10 + j
            else:
                break
        return n


class History(object):
    """ 読書履歴
        history.txt に格納されている読書履歴を操作する。
        書籍名, ページ数, フルパス, zipファイル名, 作品ID

        使い方
            プログラム開始時にインスタンスを生成することで、
            ファイルを読み出して保持する。
            プログラム終了時に update, save の順に呼び出す。
    """
    def __init__(self, filename=u'', items=9 ):
        self.hislist = []
        self.hisfile = filename
        self.maxitems = items
        self.items = 0
        self.currentitem = None

        if self.hisfile != u'':
            try:
                with open(self.hisfile, 'r') as f0:
                    for ln in f0:
                        ln = ln.strip('\n')
                        if ln != u'':
                            self.hislist.append(ln)
                        items -= 1
                        if items <= 0:
                            break
            except:
                with open(self.hisfile, 'w') as f0:
                    f0.write('')

    def iter(self):
        for i in self.hislist:
            yield i

    def save(self):
        """ 記録された最新 maxitems 件を ファイルに保存する。
        """
        if self.hisfile != u'':
            with open(self.hisfile, 'w') as f0:
                try:
                    for i in xrange(self.maxitems):
                        f0.write(u'%s\n' % self.hislist[i])
                except IndexError:
                    pass

    def update(self, item):
        """ 作品IDをキーにして既存レコードを更新する。
        　　無ければ新規追加する。
        """
        k = item.split(',')[-1]
        for s in self.hislist:
            if k == s.split(',')[-1]:
                # found
                self.hislist.remove(s)
                break

        self.hislist.insert(0,item)

    def clear(self):
        """ 全てを消去する。
        """
        self.hislist = []
        if self.hisfile != u'':
            with open(self.hisfile, 'w') as f0:
                f0.truncate(0)

    def get_item(self, n):
        """ 指定要素を得る。要素がない場合はNoneを返す。
        """
        return self.hislist[n] if n < len(self.hislist) else None


class ReaderSetting(object):
    """ 設定等
            参照及び作業ディレクトリ
                $HOME/.cahce/aozora         一時ファイル、キャッシュ
                $HOME/.cahce/aozora/text    展開されたテキストファイル
                $HOME/.config/aozora        各種設定
                $HOME/aozora                青空文庫ディレクトリ
    """
    def __init__(self, name=u'aozora'):
        """ 設定の初期化
            設定情報が既存であれば読み込み、なければ初期化する。
        """
        self.currentversion = u'0.36' # 設定ファイルのバージョン
        self.dicScreen = {}
        #   スクリーンサイズ
        for k,x,y in [(u'XGA', 996 , 672) , (u'WXGA', 1240 , 752) ,
                            (u'WSVGA', 996 , 560) , (u'SVGA', 740 , 460)]:
            self.dicScreen[k] = (x,y)

        #   参照及び作業ディレクトリ
        homedir = os.getenv('HOME')
        if not homedir:
            homedir = os.getcwd()
        cachedir = os.getenv('XDG_RUNTIME_DIR')
        if cachedir:
            cachedir = os.path.join(cachedir, u'aozora')
        else:
            cachedir = os.path.join(homedir, u'.cache', u'aozora')
        configdir = os.path.join(homedir, u'.config', u'aozora')
        aozoracurrent = os.path.join(cachedir, u'text')
        aozoradir = os.path.join(homedir, name)

        try:
            os.makedirs(cachedir)       # キャッシュディレクトリ
            os.makedirs(aozoracurrent)  # 展開されたテキスト
            os.makedirs(configdir)      # 設定ディレクトリ
            os.makedirs(aozoradir)      # 文庫ディレクトリ
        except OSError, info:
            if info.errno == errno.EEXIST:
                # file exists
                pass
            else:
                logging.error(u'ディレクトリの作成に失敗しました。%s' % info)

        #   設定ファイル
        self.settingfile = os.path.join(configdir,u'aozora.conf')
        self.dicSetting = {}
        self.dicSetting[u'version'] = u''

        if os.path.isfile(self.settingfile):
            # 既存設定ファイルの読み込み
            with file( self.settingfile, 'r' ) as f0:
                for line in f0:
                    ln = line.split('=')
                    if len(ln) > 1:
                        self.dicSetting[ln[0]] = ln[1].rstrip('\n')

        if self.dicSetting[u'version'] != self.currentversion:
            # 設定ファイルの書き換え
            self.dicSetting = {
                u'version':self.currentversion,
                u'settingdir':configdir,
                u'aozoracurrent':aozoracurrent,
                u'aozoradir':aozoradir,
                u'backcolor':u'#fffffec4ef28',
                u'bottommargin':u'8',
                u'column':u'26',
                u'fontcolor':u'#1cae1c5e0000',
                u'fontname':u'Serif',
                u'fontsize':u'12',
                u'boldfontname':u'Sans',
                u'boldfontsize':u'12',
                u'fontheight':u'',
                u'leftmargin':u'10',
                u'lines':u'24',
                u'linestep':u'1.0',
                u'linewidth':u'32',
                u'resolution':u'SVGA',
                u'rightmargin':u'12',
                u'rubifontsize':u'6',
                u'rubiwidth':u'7',
                u'scrnheight':u'448',
                u'scrnwidth':u'740',
                u'topmargin':u'32',
                u'workingdir':cachedir,
                u'idxfileURL':u'http://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip',
                u'idxfile':u'list_person_all_extended_utf8.csv',
                u'aozoraurl':u'http://www.aozora.gr.jp/index_pages', # whatsnew1.html 0.34で追加
                u'rubioffset':u'1.0' # ルビ表示位置のオフセット（本文業幅調整比） 0.35で追加
                }
            self.update()

        # 各種ファイル名の設定
        self.destfile = os.path.join(self.get_value(u'workingdir'), u'view.txt')
        self.mokujifile = os.path.join(self.get_value(u'workingdir'),u'mokuji.txt')
        self.shiorifile = os.path.join(self.get_value(u'settingdir'),
                                                                u'shiori.txt')
        # 各種設定値の取り出し
        self.aozoradir          = self.get_value(u'aozoradir')
        self.aozoratextdir      = self.get_value(u'aozoracurrent')
        self.pagelines          = int(self.get_value(u'lines'))  # 1頁の行数
        self.chars              = int(self.get_value(u'column')) # 1行の最大文字数
        self.canvas_width       = int(self.get_value(u'scrnwidth'))
        self.canvas_height      = int(self.get_value(u'scrnheight'))
        self.canvas_topmargin   = int(self.get_value(u'topmargin'))
        self.canvas_bottommargin= int(self.get_value(u'bottommargin'))
        self.canvas_rightmargin = int(self.get_value(u'rightmargin'))
        self.canvas_fontsize    = float(self.get_value( u'fontsize'))
        self.canvas_fontheight  = float(self.get_value(u'fontheight'))
        self.canvas_rubifontsize= float(self.get_value( u'rubifontsize'))
        self.canvas_linewidth   = int(self.get_value(u'linewidth'))
        self.canvas_rubispan    = int(self.get_value(u'rubiwidth'))#
        self.canvas_fontname    = self.get_value(u'fontname')#
        self.AOZORA_URL         = self.get_value(u'aozoraurl') # whatnew.WhatsNewUIより移動
        self.canvas_rubioffset  = float(self.get_value(u'rubioffset'))

    def get_linedata(self, font, fsize, linestep):
        """ フォントサイズから行幅(ピクセル)を得る
                引数
                    font            フォント名
                    fsize           フォントサイズ
                    linestep        行間
                返値
                    honbunwidth     本文行幅（ピクセル）
                    honbunheight    本文における１文字の高さ(ピクセル)
                    rubiwidth       ルビ幅（ピクセル）
                    linewidth       1行幅（ピクセル）
        """
        font_des = pango.FontDescription(u'%s %f' % (font,fsize))
        canvas_width = 800
        canvas_height = 80
        sf = cairo.ImageSurface(cairo.FORMAT_ARGB32, canvas_width, canvas_height)

        with pangocairocontext(sf) as pangoctx:
            layout = pangoctx.create_layout()
            pc = layout.get_context() # Pango を得る
            pc.set_base_gravity('east')
            pc.set_gravity_hint('natural')
            layout.set_font_description(font_des)
            layout.set_text( u'国' )
            honbunheight, honbunwidth = layout.get_pixel_size()
            del layout

        rubiwidth = int(math.ceil(honbunwidth/2.))
        linewidth = int(math.ceil((honbunwidth+rubiwidth)*linestep))
        return (honbunwidth, honbunheight, rubiwidth, linewidth)

    def update(self):
        """ 設定ファイルを更新する
        """
        (honbunwidth, honbunheight, rubiwidth, linewidth) = self.get_linedata(
                                        self.dicSetting[u'fontname'],
                                        float(self.dicSetting[u'fontsize']),
                                        float(self.dicSetting[u'linestep']))
        self.dicSetting[u'fontheight'] = str(honbunheight)
        self.dicSetting[u'rubiwidth'] = str(rubiwidth)
        self.dicSetting[u'linewidth'] = str(linewidth)
        (self.dicSetting[u'scrnwidth'],
        self.dicSetting[u'scrnheight']) = self.dicScreen[self.dicSetting[u'resolution']]
        self.dicSetting[u'column'] = str(int(
                            (float(int(self.dicSetting[u'scrnheight']) -
                                    int(self.dicSetting[u'topmargin']) -
                                    int(self.dicSetting[u'bottommargin'])) //
                                                        float(honbunheight)) ))
        self.dicSetting[u'lines'] = str(int(
                                (float(int(self.dicSetting[u'scrnwidth']) -
                                    int(self.dicSetting[u'leftmargin']) -
                                    int(self.dicSetting[u'rightmargin'])) //
                                                    float(linewidth)) ))

        with file( self.settingfile, 'w') as f0:
            for s in self.dicSetting:
                f0.write( u'%s=%s\n' % (s, self.dicSetting[s]) )

    def set_value(self, key, value):
        """ 項目値の変更
        """
        self.dicSetting[key] = value

    def get_value(self, key):
        """ 項目値の参照
        """
        return self.dicSetting[key]

    def convcolor(self, s):
        """ カラーコードの変換
            16進文字列 (#xxxxxx or #xxxxxxxxxxxx)をRGB(0..1)に変換して返す
        """
        p = (len(s)-1)/3
        f = 65535. if p > 2 else 255.
        return(
            float(int(s[1:1+p],16)/f),
            float(int(s[1+p:1+p+p],16)/f),
            float(int(s[1+p+p:1+p+p+p],16)/f) )

""" 雑関数
"""
def linux_get_active_interfaces():
    """ 外部コマンド 'ip link'　を使ってネットワークインターフェースを検出する。
        ループバックは含まない。
        ip コマンドがシステムに用意されているかどうかはチェックしない。
    """
    process = subprocess.Popen(['ip', 'link'], stdout=subprocess.PIPE)
    data, _ = process.communicate()
    for interface, _ in re.findall(r'\d+: ([^:]+):.*state (UP|UNKNOWN)', data):
        if interface != 'lo':
            yield interface

def interface_is_active():
    a = [i for i in linux_get_active_interfaces()]
    return True if a != [] else False

