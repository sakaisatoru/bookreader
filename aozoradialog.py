#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  aozoradialog.py
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

""" 各種ダイアログ
    呼び出し側を閉じた時に同時に閉じる
"""
import gtk
import gobject

class ao_dialog(gtk.Dialog):
    def __init__(self, *args, **kwargs):
        gtk.Dialog.__init__(self, *args, **kwargs)
        self.connect('response', self.response_cb)

    def response_cb(self, widget, resid):
        """ レスポンスがあればフラグで保存
        """
        self.responsed = True
        self.resid = resid

    def beforerun(self):
        """ run で入力待ちになる前に呼ばれる
        """
        pass

    def run(self):
        """
        """
        self.beforerun()
        self.responsed = False
        self.resid = None
        self.show_all()
        # 入力待ち gtk.mainで新規にループを起こすと先に進まないので
        # 既存ループのイテレータを回しながらレスポンスを待つ。
        while not self.responsed and not gtk.main_iteration():
            pass
        return self.resid


class ao_messagedialog(gtk.MessageDialog):
    def __init__(self, *args, **kwargs):
        gtk.MessageDialog.__init__(self, *args, **kwargs)
        self.connect('response', self.response_cb)

    def response_cb(self, widget, resid):
        """ レスポンスがあればフラグで保存
        """
        self.responsed = True
        self.resid = resid

    def run(self):
        """
        """
        self.responsed = False
        self.resid = None
        self.show_all()
        # 入力待ち gtk.mainで新規にループを起こすと先に進まないので
        # 既存ループのイテレータを回しながらレスポンスを待つ。
        while not self.responsed and not gtk.main_iteration():
            pass
        return self.resid


def msgerrinfo(s, oya=None):
    """ エラー
    """
    dlg = ao_messagedialog(parent=oya, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
            type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=s)
    dlg.set_position(gtk.WIN_POS_CENTER)
    dlg.run()
    dlg.destroy()

def msginfo(s, oya=None):
    """ メッセージ
    """
    dlg = ao_messagedialog(parent=oya, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
            type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK, message_format=s)
    dlg.set_position(gtk.WIN_POS_CENTER)
    dlg.run()
    dlg.destroy()

def msgyesno(s, oya=None):
    """ 2択
    """
    dlg = ao_messagedialog(parent=oya, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
            type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=s)
    dlg.set_position(gtk.WIN_POS_CENTER)
    rv = dlg.run()
    dlg.destroy()
    return rv




