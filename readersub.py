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
import codecs
import re
import os.path
import datetime
import urllib
import urllib2
import zipfile
import logging
import math
import errno

import gtk
import gobject

from readersub_nogui import ReaderSetting
import aozoradialog


class Download(object):
    """ 作品ファイルダウンロード下請け

            テキストファイルへのリンクURLが . で始まる場合は
            青空文庫URL内とみなしてURLを合成、httpで始まる場合は
            外部サイトへのリンクとしてそのままURLを用いる。
    """
    def __init__(self):
        pass

    def selected_book(self, url, chklocal=True):
        """ 指定したURLにアクセスしてダウンロードを試みる。
            (True,最後に展開したファイル名,ローカルファイル名) を返す。
            エラーの場合は (False, エラーメッセージ,'')を返す。
        """
        readcodecs = 'UTF-8'
        reTarget = re.compile( ur'.+?<td><a href="(?P<TARGETFILE>.+?.zip)">.+?.zip</a></td>' )
        flag = False
        lastselectfile = u''

        sTmpfile = os.path.join(self.get_value(u'workingdir'), u'a.html')
        #print url, sTmpfile
        try:
            urllib.urlretrieve(url, sTmpfile)
        except IOError:
            return (False, u'ダウンロードできません。' + \
                            u'ネットワークへの接続状況を確認してください。','')

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
                        isDownload = aozoradialog.msgyesnocancel(
                            u'既にダウンロードされています。上書きしますか？',
                            self)
                    if isDownload == gtk.RESPONSE_CANCEL:
                        # ひとつのダウンロードをキャンセルする
                        continue
                    try:
                        if isDownload == gtk.RESPONSE_YES:
                            urllib.urlretrieve( sTargetURL, sLocalfilename)
                    except IOError:
                        return (False, u'ダウンロードできません。' + \
                            u'ネットワークへの接続状況を確認してください。','' )

                    try:
                        a = zipfile.ZipFile( sLocalfilename, u'r' )
                        a.extractall( self.get_value(u'aozoracurrent'))
                        for b in a.namelist():
                            if os.path.split(b)[1][-4:] == '.txt':
                                lastselectfile = os.path.join(
                                    self.get_value(u'aozoracurrent'), b )
                                break
                        else:
                            return (False, u'アーカイブを' + \
                                            u'展開しましたがテキスト' + \
                                            u'ファイルが含まれていません。','')
                    except RuntimeError:
                        return (False, u'ファイルの展開時にエラーが発生' + \
                                        u'しました。ディスク容量等を確認' + \
                                        u'してください。','')

        if not flag:
            return (False, u'ダウンロードできません。この作品はルビあり' + \
                            u'テキストファイルで登録されていません。','' )
        return (True, lastselectfile, sLocalfilename)


class DownloadUI(aozoradialog.ao_dialog, ReaderSetting):
    """ ダウンロードダイアログ
    　　プログレスバーを表示しながらファイルをダウンロードする
    """
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        ReaderSetting.__init__(self)
        self.set_title(u'ダウンロード')
        self.pb = gtk.ProgressBar()
        self.pb.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
        self.vbox.pack_start(self.pb)
        self.vbox.show_all()
        self.set_position(gtk.WIN_POS_CENTER)
        self.lasturl = u''
        self.lastlocal = u''

    def set_download_url(self, fileurl, ow):
        """ このルーチンを呼んだらすかさずrunすること
            fileurl : url
            ow : True で上書き
            接続に失敗した場合は False を返す
        """
        self.target = fileurl
        try:
            self.targetlocal = os.path.join(self.aozoradir,
                                            os.path.basename(self.target))
        except:
            # 無効なURLの場合、basename が失敗する
            self.targetlocal = ''
            return False

        if not ow:
            ow = not os.path.isfile(self.targetlocal)

        if ow:
            try:
                self.targethandle = urllib2.urlopen(self.target)
                self.targetsize = long(
                    self.targethandle.info().__dict__['dict']['content-length'])
                if self.targetsize == 0L:
                    raise ValueError
            except:
                return False

            self.itreobj = self.__download_itre()
            gobject.timeout_add(200, self.__progressbar_update) # プログレスバー
            gobject.idle_add(self.__download_do_itre)           #

        else:
            gobject.idle_add(self.__download_pass_itre)           #
        return True

    def __download_pass_itre(self):
        # ファイルが既存なので何もしないで終了するための捨てルーチン
        self.responsed = True
        self.resid = None
        return False # タスクを抜去して終わる

    def __download_itre(self):
        bufsize = self.targetsize // 10
        if bufsize < 1:
            bufsize = self.targetsize
        self.readsize = 0L
        with file(self.targetlocal, 'wb') as f0:
            while self.readsize < self.targetsize:
                a = self.targethandle.read(bufsize)
                if a == '':
                    break # eof
                f0.write(a)
                self.readsize += bufsize
                yield
            else:
                pass
        self.targethandle.close()

    def get_localfilename(self):
        return self.targetlocal

    def __download_do_itre(self):
        try:
            next(self.itreobj)
        except StopIteration:
            self.responsed = True
            self.resid = None
            return False # タスクを抜去して終わる
        return True

    def __progressbar_update(self):
        """ プログレスバーを間欠的に更新する
        """
        n = float(self.readsize)/float(self.targetsize)
        if n > 1.0:
            n = 1.0
        self.pb.set_fraction(n)
        return True

