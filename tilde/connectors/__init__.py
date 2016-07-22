# Author: Evgeny Blokhin

import os
from six.moves.html_entities import codepoint2name


def htmlentities(source):
    new_source = ''
    for char in source:
        if ord(char) in codepoint2name: char = '&%s;' % codepoint2name[ord(char)]
        new_source += char
    return new_source

def viewer_wrap(actual, prefix, kind):
    if len(prefix): prefix += os.sep
    actual = actual.replace('\\', '/')
    prefix = prefix.replace('\\', '/')
    capt = actual if len(actual) <= 68 else actual[:67] + '...'
    a = htmlentities(actual)
    p = htmlentities(prefix)
    if kind is 'DIR':
        return "<li class='directory collapsed'><a href='' rel='" + p + a + "'>" + capt + "</a></li>"
    elif kind is 'FILE':
        ext_class = actual.split('.')[-1]
        return "<li class='file ext_" + ext_class + "'><a href='' rel='" + p + a + "'>" + capt + "</a></li>"
