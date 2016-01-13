#!/usr/bin/python
# -*- coding: utf-8 -*-
#  draw.py
import sys
from cairocanvas import CairoCanvas
if __name__ == "__main__":
    n = sys.argv[1].split()
    t = u"" if len(n) < 4 else not n.insert(4,u" ") and u"".join(n[3:])
    cTmp = CairoCanvas()
    cTmp.writepage(long(n[0]), currentpage=int(n[1]), maxpage=int(n[2]), title=t)