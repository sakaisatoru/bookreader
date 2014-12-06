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


from __future__ import with_statement

from hypertext import HyperTextView

from readersub import ReaderSetting, AozoraDialog
from aozoracard import AuthorList
import sys, codecs, re, os.path, datetime, unicodedata
from threading import Thread
import gtk, cairo, pango, pangocairo, gobject

sys.stdout=codecs.getwriter( 'UTF-8' )(sys.stdout)

from HTMLParser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self.nTableCount = 0
        self.nTrCount = 0
        self.nTdCount = 0
        self.record=[]
        self.page=[]

    def handle_starttag(self, tag, attrs):
        if tag == u'table':
            self.nTableCount += 1
            self.nTrCount = 0
            self.nTdCount = 0
        elif tag == u'tr':
            self.nTrCount += 1
            self.nTdCount = 0
        elif tag == u'td':
            self.nTdCount += 1
        elif tag == u'a':
            if self.nTdCount == 2 and self.nTableCount == 2:
                self.record.append(attrs[0][1])

    def handle_data(self, data):
        if self.nTableCount == 2:
            if self.nTrCount >= 2:
                if self.nTdCount < 4:
                    self.record.append(data.lstrip().rstrip( u' \r\n' ))

    def handle_endtag(self, tag):
        if self.nTableCount == 2:
            if tag == u'tr':
                self.page.append(self.record)
                self.record=[]

    def ReadRecord(self):
        for s in self.page:
            yield s


if __name__ == u'__main__':
    a = MyHTMLParser()

    with codecs.open( u'whatsnew1.html' ) as f0:
        a.feed(f0.read())
        a.close()
        for i in a.ReadRecord():
            print i
