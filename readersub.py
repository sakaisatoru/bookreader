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


""" 青空文庫リーダー
"""
from collections import deque
import sys, codecs, re, os.path, datetime, unicodedata, urllib, zipfile
import logging
import gtk, cairo, pango, pangocairo, gobject

class Download():
    """ 作品ファイルダウンロード下請け

            テキストファイルへのリンクURLが . で始まる場合は青空文庫URL内とみなして
            URLを合成、httpで始まる場合は外部サイトへのリンクとしてそのままURLを
            用いる。
    """
    def __init__(self):
        pass

    def selected_book(self, url):
        """ 指定したURLにアクセスしてダウンロードを試みる。
            (True,最後に展開したファイル名) を返す。
            エラーの場合は (False, エラーメッセージ)を返す。
        """
        readcodecs = 'UTF-8'
        reTarget = re.compile( ur'.+?<td><a href="(?P<TARGETFILE>.+?.zip)">.+?.zip</a></td>' )
        flag = False
        lastselectfile = u''

        sTmpfile = ( u'%s/a.html' % self.get_value( u'workingdir' ))
        try:
            urllib.urlretrieve(url, sTmpfile)
        except IOError:
            return (False, u'ダウンロードできません。ネットワークへの接続状況を確認してください。')

        with codecs.open( sTmpfile, 'r', readcodecs ) as f0:
            for line in f0:
                mTmp = reTarget.search(line)
                if mTmp != None:
                    flag = True
                    sTarget = mTmp.group( u'TARGETFILE' )
                    sLocalfilename = u'%s/%s' % (self.get_value(u'aozoradir'),os.path.basename(sTarget))
                    if sTarget.split(u':')[0].lower() == u'http':
                        sTargetURL = sTarget
                    else:
                        sTargetURL = u'%s/%s' % (os.path.dirname(url),sTarget)

                    try:
                        urllib.urlretrieve( sTargetURL, sLocalfilename)
                    except IOError:
                        return (False, u'ダウンロードできません。ネットワークへの接続状況を確認してください。' )

                    try:
                        a = zipfile.ZipFile( sLocalfilename, u'r' )
                        b = a.namelist()
                        a.extractall( self.get_value(u'aozoradir'))
                        lastselectfile = u'%s/%s' % (self.get_value(u'aozoradir'), b[0] )
                    except:
                        return (False, u'ファイルの展開時にエラーが発生しました。ディスク容量等を確認してください。')

        if flag != True:
            return (False, u'ダウンロードできません。この作品はルビありテキストファイルで登録されていません。' )

        return (True, lastselectfile)


class AozoraDialog():
    """ 各種ダイアログ
    """
    def __init__(self):
        pass

    def msgerrinfo( self, s ):
        """ エラーダイアログ
        """
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, s )
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.run()
        dlg.destroy()

    def msginfo( self, s ):
        """ メッセージダイアログ
        """
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                gtk.MESSAGE_INFO, gtk.BUTTONS_OK, s )
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.run()
        dlg.destroy()


class ReaderSetting():
    """ 設定等
            参照及び作業ディレクトリ
                $HOME/.cahce/           一時ファイル、キャッシュ
                $HOME/.config/aozora    各種設定
                $HOME/aozora            青空文庫ディレクトリ

        テキスト表示領域の解像度等のデータベース
            XGA(1024x768)
                width=880, height=616, topmargin = 8, rightmargin = 12, linestep = 30, colum = 37, lines = 29
            WXGA(1280x800)
                width=1240, height=664, topmargin = 8, rightmargin = 12, linestep = 30, colum = 40, lines = 41
            WSVGA(1024x600)
                width=880, height=448, topmargin = 8, rightmargin = 12, linestep = 30, colum = 26, lines = 29
            SVGA(800x600)
                width=740, height=448, topmargin = 8, rightmargin = 12, linestep = 30, colum = 26, lines = 24

        ルビサイズ
            本文の半分
    """

    def __init__(self, name = u'aozora'):
        """ 設定の初期化
            設定情報が既存であれば読み込み、なければ初期化する。
        """
        #             SVGA       WSVGA       WXGA         XGA
        screendata = [448, 740,  448, 880,   736, 1240,   616, 880]
        self.dicScreen = {}
        for i in (u'XGA', u'WXGA', u'WSVGA', u'SVGA'):
            for j in (u'width', u'height'):
                self.dicScreen[u'%s_%s' % (i,j)] = screendata.pop()
        homedir = self.get_homedir()
        self.dicSetting = { u'settingdir':os.path.join( homedir, u'.config/aozora'),
                                u'aozoracurrent':u'',
                                u'aozoradir':u'',
                                u'backcolor':u'#fffffdade03d',
                                u'bottommargin':u'8',
                                u'column':u'26',
                                u'fontcolor':u'#514050800000',
                                u'fontname':u'Serif',
                                u'fontsize':u'12',
                                u'leftmargin':u'10',
                                u'lines':u'24',
                                u'linestep':u'1.5',
                                u'linewidth':u'32',
                                u'resolution':u'SVGA',
                                u'rightmargin':u'12',
                                u'rubifontsize':u'6',
                                u'rubiwidth':u'7',
                                u'scrnheight':u'448',
                                u'scrnwidth':u'740',
                                u'topmargin':u'8',
                                u'workingdir':u''
                            }
        self.settingfile = os.path.join(self.dicSetting[u'settingdir'], 'aozora.conf')
        self.checkdir(self.dicSetting[u'settingdir'])
        try:
            # 既存設定ファイルの読み込み
            with file( self.settingfile, 'r' ) as f0:
                for line in f0:
                    ln = line.split('=')
                    if len(ln) > 1:
                        self.dicSetting[ln[0]] = ln[1].rstrip('\n')
        except:
            # 設定ファイルの新規作成
            self.dicSetting[u'workingdir'] = os.path.join(homedir, u'.cache/aozora')
            self.checkdir(self.dicSetting[u'workingdir'])
            self.set_aozorabunkodir(name)
            self.update()


    def get_linedata(self, fsize, linestep):
        """ フォントサイズから行幅(ピクセル)を得る
                引数
                    fsize           フォントサイズ
                    linestep        行間
                返値
                    honbunwidth     本文行幅（ピクセル）
                    rubiwidth       ルビ幅（ピクセル）
                    linewidth       1行幅（ピクセル）
        """
        honbunwidth = int(round(fsize *1.24+0.5))
        rubiwidth = int(round( honbunwidth / 2 + 0.5))
        linewidth = int(round(( honbunwidth + rubiwidth ) * (1 + linestep ) + 0.5))
        return (honbunwidth, rubiwidth, linewidth)

    def update(self):
        """ 設定ファイルを更新する
        """
        (honbun, rubiwidth, linewidth) = self.get_linedata(int(self.dicSetting[u'fontsize']), float(self.dicSetting[u'linestep']))
        self.dicSetting[u'rubiwidth'] = str(rubiwidth)
        self.dicSetting[u'linewidth'] = str(linewidth)
        self.dicSetting[u'scrnwidth'] = self.dicScreen[u'%s_width' % self.dicSetting[u'resolution']]
        self.dicSetting[u'scrnheight'] = self.dicScreen[u'%s_height' % self.dicSetting[u'resolution']]
        self.dicSetting[u'column'] = str(int(-2 + round(((int(self.dicSetting[u'scrnheight']) - int(self.dicSetting[u'topmargin']) - int(self.dicSetting[u'bottommargin']))/ honbun) - 0.5)))
        self.dicSetting[u'lines'] = str(int(round(((int(self.dicSetting[u'scrnwidth']) - int(self.dicSetting[u'leftmargin']) - int(self.dicSetting[u'rightmargin']))/ linewidth) - 0.5)))

        with file( self.settingfile, 'w') as f0:
            for s in self.dicSetting:
                f0.write( u'%s=%s\n' % (s, self.dicSetting[s]) )

    def checkdir(self, dirname):
        """ ディレクトリの有無を調べて存在しなければ新規に作成する
        """
        sTmpdir = dirname.split('/')
        sCurrdir = sTmpdir[0]
        if sCurrdir == '':
            sCurrdir = '/'
        os.chdir(sCurrdir)

        for s in sTmpdir[1:]:
            sCurrdir = os.path.join(sCurrdir,s)
            try:
                os.chdir(sCurrdir)
            except OSError:
                os.mkdir(sCurrdir)

    def get_homedir(self):
        """ ホームディレクトリを返す。存在しない場合はカレントディレクトリを返す。
        """
        homedir = os.getenv('HOME')
        if homedir == None:
            homedir = u'.'
        return homedir

    def set_aozorabunkocurrent(self, name):
        """ オープンした青空文庫の格納先ディレクトリを得る
            同梱の画像ファイル等を探す際、参照される。
        """
        self.dicSetting[u'aozoracurrent'] = os.path.dirname(name)

    def set_aozorabunkodir(self, name):
        """ 青空文庫の格納先をセットする
            ディレクトリが無ければ作成する
        """
        if name[0] == '/':
            self.dicSetting[u'aozoradir'] = name
        else:
            homedir = self.get_homedir()
            self.dicSetting[u'aozoradir'] = os.path.join(homedir,name)

        self.checkdir(self.dicSetting[u'aozoradir'])

    def set_value(self, key, value):
        """ 項目値の変更
        """
        self.dicSetting[key] = value

    def get_value(self, key):
        """ 項目値の参照
        """
        return self.dicSetting[key]


class History():
    """ 読書履歴
        history.txt に格納されている読書履歴を操作する。
        書籍名, ページ数, フルパス

        使い方
            プログラム開始時にインスタンスを生成することで、
            ファイルを読み出して保持する。
            プログラム終了時に update, save の順に呼び出す。
    """
    def __init__(self, filename=u'', items=5 ):
        self.hislist = deque()
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
                            self.hislist.appendleft(ln)
                            self.items += 1
            except:
                with open(self.hisfile, 'w') as f0:
                    f0.write('')

    def iter(self):
        """ イテレータ
        """
        for i in self.hislist:
            yield i

    def save(self):
        """ ファイルに保存する。
        """
        if self.hisfile != u'':
            with open(self.hisfile, 'w') as f0:
                self.hislist.reverse()
                for ln in self.hislist:
                    f0.write(u'%s\n' % ln)

    def update(self, item):
        """ 直前に参照した要素を削除し、新規にitemを追加する。
        """
        try:
            self.hislist.remove(self.currentitem)
        except ValueError:
            pass
        self.append(item)

    def clear(self):
        """ 全てを消去する。
        """
        self.hislist.clear()
        if self.hisfile != u'':
            with open(self.hisfile, 'w') as f0:
                f0.write('')

    def append(self, item):
        """ 要素を追加する。オーバーフローした分は失われる。
        """
        if self.items >= self.maxitems:
            self.hislist.pop()
            self.items -= 1
        self.hislist.appendleft(item)
        self.items += 1

    def get_item(self, n):
        """ 指定要素を得る。要素がない場合はNoneを返す。
        """
        r = len(self.hislist) -1
        if n < 0:
            n = r + 1 - n
        self.currentitem = self.hislist[n] if n >=0 and r >= n else None
        return self.currentitem
