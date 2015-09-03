# Author: Evgeny Blokhin

import os, sys

from tilde.connectors import viewer_wrap


def list(path, root):
    output = ''
    error = None
    dirs = []
    files = []
    try:
        for item in os.listdir(root + path):
            if os.path.isdir(root + path + os.sep + item):
                dirs.append(item)
            else: files.append(item)
    except OSError:
        return (output, 'Requested path is not readable!')
    dirs.sort()
    files.sort()
    for i in dirs:
        output += viewer_wrap(i, path, 'DIR')
    for i in files:
        output += viewer_wrap(i, path, 'FILE')
    return (output, error)

def report(analyzer_obj, sess_ctx, path, root):
    checksum, error = None, None
    try: calc, error = analyzer_obj.parse(root + path)
    except (OSError, IOError):
        error = 'Requested file is not readable!'
    if not error:
        calc, error = analyzer_obj.classify(calc)
        if not error:
            calc = analyzer_obj.postprocess(calc)
            checksum, error = analyzer_obj.save(calc, sess_ctx)
        del calc
    return (checksum, error)
