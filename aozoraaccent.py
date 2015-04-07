#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  aozoraaccent.py
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


""" アクセント分解による文字の置換
"""
accenttable = {
    u'!@':u'¡', u'?@':u'¿',
    u'A`':u'À', u"A'":u'Á', u'A^':u'Â', u'A~':u'Ã', u'A:':u'Ä', u'A&':u'Å',
    u'AE&':u'Æ',
    u'C,':u'Ç',
    u'E`':u'È', u"E'":u'É', u'E^':u'Ê', u'E:':u'Ë',
    u'I`':u'Ì', u"I'":u'Í', u'I^':u'Î', u'I:':u'Ï',
    u'N~':u'Ñ',
    u'O`':u'Ò', u"O'":u'Ó', u'O^':u'Ô', u'O~':u'Õ',u'O:':u'Ö', u'O/':u'Ø',
    u'U`':u'Ù', u"U'":u'Ú', u'U^':u'Û', u'U:':u'Ü',
    u"Y'":u'Ý', u's&':u'ß',
    u'a`':u'à', u"a'":u'á', u'a^':u'â', u'a~':u'ã', u'a:':u'ä', u'a&':u'å',
    u'ae&':u'æ',u'c,':u'ç',
    u'e`':u'è', u"e'":u'é', u'e^':u'ê', u'e:':u'ë',
    u'i`':u'ì', u"i'":u'í', u'i^':u'î', u'i:':u'ï',
    u'n~':u'ñ',
    u'o`':u'ò', u"o'":u'ó', u'o^':u'ô', u'o~':u'õ', u'o:':u'ö', u'o/':u'ø',
    u'u`':u'ù', u"u'":u'ú', u'u^':u'û', u'u:':u'ü',
    u"y'":u'ý', u'y:':u'ÿ',
    u'A_':u'Ā', u'a_':u'ā',
    u'E_':u'Ē', u'e_':u'ē',
    u'I_':u'Ī', u'i_':u'ī',
    u'O_':u'Ō', u'o_':u'ō',
    u'OE&':u'Œ',u'oe&':u'œ',u'U_':u'Ū', u'u_':u'ū' }

    # u'--':u'Ð', u'--':u'Þ', u'--':u'ð', u'--':u'þ',


def __replacesub(src):
    """ 下請け
        ネスティング対応
        変換した文字列と、変換前の全長を返す
    """
    pos = src.find(u'〔')
    length = len(src)
    if pos == -1:
        return src, length

    rv = []
    changed = False
    rv.append(src[:pos])
    rv.append(src[pos])     # 〔
    pos += 1
    while pos < length:
        if src[pos] == u'〕':
            if changed:
                rv[1] =u'' # 〔を抜去
            else:
                rv.append(src[pos])
            src = ''.join(rv)
            pos += 1
            length = pos
            break

        if src[pos] == u'〔':
            tmp,l = __replacesub(src[pos:])
            rv.append(tmp)
            pos += l
            continue

        tmp = src[pos:pos+2]
        if tmp in accenttable:
            rv.append(accenttable[tmp])
            pos += 2
            changed = True
            continue

        tmp = src[pos:pos+3]
        if tmp in accenttable:
            rv.append(accenttable[tmp])
            pos += 3
            changed = True
            continue

        rv.append(src[pos])
        pos += 1
    else:
        src = ''.join(rv)

    return src, length

def replace(src):
    """ アクセント分解された文字を置換する
        処理された場合は両端の〔〕を抜去して返す
        〔〕が閉じていなかったり、アクセント分解が出現しなかった
        場合はそのまま返す
        ネスティングに対応している
    """
    length = len(src)
    pos = 0
    l = 1
    rv = []
    while pos < length and l > 0:
        s,l = __replacesub(src[pos:])
        rv.append(s)
        pos += l
    if l == 0:
        # 無限ループ発生時
        print u'aozoraaccent.replaceにて無限ループ %s %d' % (src,pos)
    return ''.join(rv)
