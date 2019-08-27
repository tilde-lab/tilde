"""
This script introduces how the Tilde organizer
can be used as a bibliography manager.
See https://github.com/tilde-lab/pycrystal/tree/master/papers
for an example usage for the CRYSTAL17 code online bibliography.
Two files are currently needed:
* bib_els_file (raw bibliography items as presented online)
* bib_data_file (processed bibliography items, e.g. with DOI, PDF, etc.)
"""
import os
import sys
import json
import random
from hashlib import md5

import chk_tilde_install

from tilde.core.api import API
from tilde.core.settings import connect_database, settings
from tilde.parsers import Output


# these mappings were absent in the CRYSTAL17 online bibliography
MISSING_MAPPING = {'to127': ['O', 'Zr'], 'knaup2005': ['C', 'O', 'Si'], 'catti2000': ['O', 'Si'], 'to307': ['H', 'O', 'Si'], 'sto52': ['H', 'O', 'Si'], 'lindsay98': ['Cl', 'Si'], 'mukhopadhyay2004': ['O', 'Si'], 'to279': ['O', 'Si'], 'Gibbs99a': ['O', 'Si'], 'gibbs1999': ['O', 'Si'], 'gibbs2003': ['O', 'Si'], 'gibbs2006': ['Na', 'Mg', 'Al', 'Si', 'B', 'N', 'C', 'S', 'P', 'O'], 'sto89': ['O', 'Si'], 'to220': ['C', 'Si'], 'zwijnenburg2007': ['O', 'Si'], 'to264': ['O', 'Si'], 'goumans2007': ['O', 'Si'], 'to45': ['C', 'Si'], 'sonnet1999': ['Si'], 'to253': ['O', 'Si'], 'gnani2000': ['O', 'Si'], 'zwijnenburg2006': ['Si', 'Ge', 'Be', 'O', 'F', 'S'], 'to44': ['Si'], 'to126': ['Si'], 'knaup2005b': ['C', 'Si'], 'gibbs2000': ['O', 'Si'], 'sto72': ['Si'], 'sto92': ['H', 'Si']}

class PDF_Article(Output):
    def __init__(self, filename):
        Output.__init__(self, filename)
        self.related_files.append(filename)
        self.info['dtype'] = 0x1

    def get_checksum(self):
        if os.path.exists(self._filename):
            hash_md5 = md5()
            with open(self._filename, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            # NB. there are dups, and we need to workaround them
            return hash_md5.hexdigest() + 'PDF'

        self.related_files = []
        # for non-ready items, TODO
        return "".join([random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(48)]) + 'PDF'

    def set_meta_and_els(self, els):
        self.info['elements'] = els
        self.info['standard'] = ' / '.join(sorted(els))
        self.info['formula'] = ' / '.join(sorted(els))
        self.info['ng'] = 0
        self.info['nelem'] = 0
        self.info['H'] = 'unknown'
        self.info['framework'] = 0x3 # CRYSTAL
        self.info['ansatz'] = 0x3 # CRYSTAL

if __name__ == "__main__":
    try:
        bib_els_file = sys.argv[1]
        bib_data_file = sys.argv[2]
    except IndexError:
        raise RuntimeError

    f = open(bib_els_file)
    els2bib = json.loads(f.read())
    f.close()

    f = open(bib_data_file)
    data2meta = json.loads(f.read())
    f.close()

    folder = os.sep.join(bib_els_file.split(os.sep)[:-2])

    session = connect_database(settings)
    work = API()

    data2els = {}
    for el in els2bib['els2paperids']:
        for article_item in set(els2bib['els2paperids'][el]): # FIXME? set, as we have dups els
            data2els.setdefault(article_item, []).append(el)
    data2els.update(MISSING_MAPPING)

    for key in els2bib['paperids2bib']:
        # for non-ready items, TODO
        if key not in data2meta:
            filename = 'data/NONCE'
            doi = None
            authors = els2bib['paperids2bib'][key][0].replace(' and ', ', ').encode('ascii', 'ignore').split(', ')
            year = els2bib['paperids2bib'][key][2]
            article_title = els2bib['paperids2bib'][key][1].encode('ascii', 'ignore')
            pubdata = els2bib['paperids2bib'][key][3].encode('ascii', 'ignore')
            print("Missing: %s, %s, %s (%s)" % (authors, article_title, pubdata, year))
        else:
            filename = data2meta[key][0]
            doi = data2meta[key][1]
            authors = data2meta[key][2].encode('ascii', 'ignore').split(', ')
            year = data2meta[key][5]
            article_title = data2meta[key][3].encode('ascii', 'ignore')
            pubdata = data2meta[key][4].encode('ascii', 'ignore')

        seen = set()
        seen_add = seen.add
        authors = [x for x in authors if not (x in seen or seen_add(x))] # preserving order

        data_item = PDF_Article(os.path.join(folder, filename))
        data_item.set_meta_and_els(data2els[key])

        data_item.info['authors'] = authors
        data_item.info['year'] = year
        data_item.info['article_title'] = article_title
        if doi: data_item.info['doi'] = doi
        data_item.info['pubdata'] = pubdata

        checksum, error = work.save(data_item, session)
        if error:
            print(error)

    session.close()
