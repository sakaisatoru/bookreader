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

""" ログビューワ
"""
from readersub_nogui import ReaderSetting
import aozoradialog

import os.path
import os
import stat
import logging

import gtk
import gobject

class Logviewer(aozoradialog.ao_dialog, ReaderSetting):
    """ ログファイルを表示する
    """
    def __init__(self, *args, **kwargs):
        aozoradialog.ao_dialog.__init__(self, *args, **kwargs)
        ReaderSetting.__init__(self)

        self.logfilename = os.path.join(self.get_value(u'workingdir'),
                                                                u'aozora.log' )

        self.textbuffer_logfile = gtk.TextBuffer()
        self.textview_logfile = gtk.TextView(self.textbuffer_logfile)
        self.textview_logfile.set_wrap_mode(gtk.WRAP_CHAR)
        self.textview_logfile.set_editable(False)

        self.sw3 = gtk.ScrolledWindow()
        self.sw3.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw3.add(self.textview_logfile)

        # ビルド
        self.sw3.set_size_request(600,344)
        self.vbox.pack_start(self.sw3, expand=True)
        self.vbox.show_all()
        self.set_title(u'青空文庫ビューア　デバッグメッセージ')
        self.readlogfile()
        self.lastupdatetime = os.stat(self.logfilename)[stat.ST_MTIME]
        gobject.timeout_add(1000, self.refresh_logview) # 定時割込駆動をセット

    def refresh_logview(self):
        """ 表示の更新
            ログファイルが変更されていたら更新する
        """
        if self.lastupdatetime != os.stat(self.logfilename)[stat.ST_MTIME]:
            self.textbuffer_logfile.set_text(u'')
            self.readlogfile()
            self.lastupdatetime = os.stat(self.logfilename)[stat.ST_MTIME]
        # True を返すまで次のイベントは生じない
        return True

    def readlogfile(self):
        """ ログファイルの内容をUIに得る
        """
        itre = self.textview_logfile.get_buffer().get_iter_at_offset(0)
        with open( self.logfilename, 'r') as f0:
            ln = 0
            for line in f0:
                self.textview_logfile.get_buffer().insert(itre,line)
                ln += 1

            # カーソルを文末行へ遷移
            lineitre = self.textview_logfile.get_buffer().get_iter_at_line(ln)
            self.textview_logfile.get_buffer().place_cursor(lineitre)
            self.textview_logfile.scroll_to_iter(lineitre, 0.2)
