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
import sys
import codecs
import re
import os.path
import datetime
import unicodedata
import urllib
import zipfile
import logging
import math
import errno

import gtk
import cairo
import pango
import pangocairo
import gobject

class Download():
    """ 作品ファイルダウンロード下請け

            テキストファイルへのリンクURLが . で始まる場合は
            青空文庫URL内とみなしてURLを合成、httpで始まる場合は
            外部サイトへのリンクとしてそのままURLを用いる。
    """
    def __init__(self):
        pass

    def selected_book(self, url, chklocal=True):
        """ 指定したURLにアクセスしてダウンロードを試みる。
            (True,最後に展開したファイル名) を返す。
            エラーの場合は (False, エラーメッセージ)を返す。

            2014/01/20
                chklocal 追加
                Trueであれば、ローカルの青空ディレクトリに同名ファイルが
                存在しないかチェックし、ダウンロードの是非を問う。

                ファイルの展開先を /tmp へ変更。
        """
        readcodecs = 'UTF-8'
        reTarget = re.compile( ur'.+?<td><a href="(?P<TARGETFILE>.+?.zip)">.+?.zip</a></td>' )
        flag = False
        lastselectfile = u''

        sTmpfile = os.path.join(self.get_value(u'workingdir'), u'a.html')
        try:
            urllib.urlretrieve(url, sTmpfile)
        except IOError:
            return (False, u'ダウンロードできません。' + \
                            u'ネットワークへの接続状況を確認してください。')

        with codecs.open( sTmpfile, 'r', readcodecs ) as f0:
            for line in f0:
                mTmp = reTarget.search(line)
                if mTmp:
                    flag = True
                    sTarget = mTmp.group( u'TARGETFILE' )
                    if sTarget.split(u':')[0].lower() == u'http':
                        sTargetURL = sTarget
                    else:
                        sTargetURL = os.path.join(os.path.dirname(url),sTarget)

                    sLocalfilename = os.path.join(
                        self.get_value(u'aozoradir'),os.path.basename(sTarget))

                    isDownload = gtk.RESPONSE_YES
                    if chklocal and os.path.isfile(sLocalfilename):
                        """ ローカルにアーカイブが既存する場合は、
                            問い合わせる。
                        """
                        tmpdlg = AozoraDialog()
                        isDownload = tmpdlg.msgyesno( u'既にダウンロード' + \
                                        u'されています。上書きしますか？')
                    try:
                        if isDownload == gtk.RESPONSE_YES:
                            urllib.urlretrieve( sTargetURL, sLocalfilename)
                    except IOError:
                        return (False, u'ダウンロードできません。' + \
                            u'ネットワークへの接続状況を確認してください。' )

                    try:
                        a = zipfile.ZipFile( sLocalfilename, u'r' )
                        a.extractall( self.get_value(u'aozoracurrent'))
                        for b in a.namelist():
                            print b
                            if os.path.split(b)[1][-4:] == '.txt':
                                lastselectfile = os.path.join(
                                    self.get_value(u'aozoracurrent'), b )
                                break
                        else:
                            return (False, u'アーカイブを' + \
                                            u'展開しましたがテキスト' + \
                                            u'ファイルが含まれていません。')
                    except RuntimeError:
                        return (False, u'ファイルの展開時にエラーが発生' + \
                                        u'しました。ディスク容量等を確認' + \
                                        u'してください。')

        if not flag:
            return (False, u'ダウンロードできません。この作品はルビあり' + \
                            u'テキストファイルで登録されていません。' )
        print sLocalfilename
        return (True, lastselectfile, sLocalfilename)


class AozoraDialog():
    """ 各種ダイアログ
    """
    def __init__(self):
        pass

    def msgerrinfo(self, s):
        """ エラーダイアログ
        """
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, s )
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.run()
        dlg.destroy()

    def msginfo(self, s):
        """ メッセージダイアログ
        """
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                gtk.MESSAGE_INFO, gtk.BUTTONS_OK, s )
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.run()
        dlg.destroy()

    def msgyesno(self, s):
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, s )
        dlg.set_position(gtk.WIN_POS_CENTER)
        rv = dlg.run()
        dlg.destroy()
        return rv


class ReaderSetting():
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
        #   スクリーンサイズ
        #             XGA   WXGA    WSVGA   SVGA
        screendata = [(996 , 656) , (1240 , 736) , (880 , 448) , (740 , 448)]
        self.currentversion = u'0.3' # 設定ファイルのバージョン
        self.dicScreen = {}
        for k in (u'SVGA', u'WSVGA', u'WXGA', u'XGA'):
            self.dicScreen[k] = screendata.pop()

        #   参照及び作業ディレクトリ
        homedir = os.getenv('HOME')
        if not homedir:
            homedir = os.getcwd()
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
                u'backcolor':u'#fffffdade03d',
                u'bottommargin':u'8',
                u'column':u'26',
                u'fontcolor':u'#514050800000',
                u'fontname':u'Serif',
                u'fontsize':u'12',
                u'fontheight':u'',
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
                u'workingdir':cachedir
                }
            self.update()

        # 各種ファイル名の設定
        self.destfile = os.path.join(self.get_value(u'workingdir'), u'view.txt')
        self.mokujifile = os.path.join(self.get_value(u'workingdir'),u'mokuji.txt')

        # 各種設定値の取り出し
        self.aozoradir          = self.get_value(u'aozoradir')
        self.aozoratextdir      = self.get_value(u'aozoracurrent')
        self.pagelines          = int(self.get_value(u'lines'))  # 1頁の行数
        self.chars              = int(self.get_value(u'column')) # 1行の最大文字数
        self.canvas_width       = int(self.get_value(u'scrnwidth'))
        self.canvas_height      = int(self.get_value(u'scrnheight'))
        self.canvas_topmargin   = int(self.get_value(u'topmargin'))
        self.canvas_rightmargin = int(self.get_value(u'rightmargin'))
        self.canvas_fontsize    = float(self.get_value( u'fontsize'))
        self.canvas_rubifontsize= float(self.get_value( u'rubifontsize'))
        self.canvas_linewidth   = int(self.get_value(u'linewidth'))
        self.canvas_rubispan    = int(self.get_value(u'rubiwidth'))#
        self.canvas_fontname    = self.get_value(u'fontname')#

    def get_linedata(self, fsize, linestep):
        """ フォントサイズから行幅(ピクセル)を得る
                12pt = 16px で計算
                引数
                    fsize           フォントサイズ
                    linestep        行間
                返値
                    honbunwidth     本文行幅（ピクセル）
                    rubiwidth       ルビ幅（ピクセル）
                    linewidth       1行幅（ピクセル）
        """
        honbunwidth = int(round(fsize*(16./12.)))
        rubiwidth = int(math.ceil(honbunwidth/2))
        linewidth = int(math.ceil((honbunwidth+rubiwidth)*linestep))
        return (honbunwidth, rubiwidth, linewidth)

    def update(self):
        """ 設定ファイルを更新する
        """
        (honbun, rubiwidth, linewidth) = self.get_linedata(
                                        float(self.dicSetting[u'fontsize']),
                                        float(self.dicSetting[u'linestep']))
        self.dicSetting[u'fontheight'] = str(honbun)
        self.dicSetting[u'rubiwidth'] = str(rubiwidth)
        self.dicSetting[u'linewidth'] = str(linewidth)
        (self.dicSetting[u'scrnwidth'],
        self.dicSetting[u'scrnheight']) = self.dicScreen[self.dicSetting[u'resolution']]
        self.dicSetting[u'column'] = str(int(
                            (float(int(self.dicSetting[u'scrnheight']) -
                                    int(self.dicSetting[u'topmargin']) -
                                    int(self.dicSetting[u'bottommargin'])) //
                                                        float(honbun)) ))
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
