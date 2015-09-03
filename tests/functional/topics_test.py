#!/usr/bin/env python

import os, sys
import logging

import set_path
import tilde.core.model as model
from tilde.core.settings import EXAMPLE_DIR
from . import TestLayerDB


logger = logging.getLogger('tilde')
logger.setLevel(logging.INFO)

class Test_Topics(TestLayerDB):
    __test_calcs_dir__ = os.path.join(EXAMPLE_DIR, 'VASP')
    expected_topics_before = {
        "V3MYGXYORMRSAYFR4WN4MSX3L6JI2DE7E3QRC4KYTXMDGCI": [
            {'topic': u'SrTiO3',                         'cid': 1},
            {'topic': u'Sr',                             'cid': 2},
            {'topic': u'Ti',                             'cid': 2},
            {'topic': u'O',                              'cid': 2},
            {'topic': u'3',                              'cid': 3},
            {'topic': u'1',                              'cid': 4},
            {'topic': u'3D',                             'cid': 5},
            {'topic': u'total energy',                   'cid': 6},
            {'topic': u'electron structure',             'cid': 6},
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'O<sub>h</sub>',                  'cid': 10},
            {'topic': u'Pm-3m',                          'cid': 11},
            {'topic': u'8x8x8',                          'cid': 17},
            {'topic': u'VASP',                           'cid': 22},
            {'topic': u'VASP 5.2.2',                     'cid': 23},
            {'topic': u'plane waves',                    'cid': 80},
            {'topic': u'GGA',                            'cid': 75},
            {'topic': u'perovskite',                     'cid': 8},
            {'topic': u'insulator',                      'cid': 26},
            {'topic': u'cubic',                          'cid': 9}
        ],
        "HYO6KU4ZBQWJJIGLO3DFO44DBO2LVZGYEHTPEIDEK2WGMCI": [
            {'topic': u'Si16',                           'cid': 1},
            {'topic': u'Si',                             'cid': 2},
            {'topic': u'1',                              'cid': 3},
            {'topic': u'1',                              'cid': 4},
            {'topic': u'3D',                             'cid': 5},
            {'topic': u'total energy',                   'cid': 6},
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'C<sub>s</sub>',                  'cid': 10},
            {'topic': u'Cm',                             'cid': 11},
            {'topic': u'4x4x4',                          'cid': 17},
            {'topic': u'VASP',                           'cid': 22},
            {'topic': u'VASP 4.6.35',                    'cid': 23},
            {'topic': u'plane waves',                    'cid': 80},
            {'topic': u'GGA',                            'cid': 75},
            {'topic': u'monoclinic',                     'cid': 9}
        ]
    }
    expected_topics_after = {
        "V3MYGXYORMRSAYFR4WN4MSX3L6JI2DE7E3QRC4KYTXMDGCI": [
            {'topic': u'SrTiO3',                         'cid': 1},
            {'topic': u'Xx',                             'cid': 2},
            {'topic': u'Yy',                             'cid': 2},
            {'topic': u'Zz',                             'cid': 2},
            {'topic': u'Ww',                             'cid': 2},
            {'topic': u'3',                              'cid': 3},
            {'topic': u'1',                              'cid': 4},
            {'topic': u'3D',                             'cid': 5},
            {'topic': u'total energy',                   'cid': 6},
            {'topic': u'electron structure',             'cid': 6},
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'O<sub>h</sub>',                  'cid': 10},
            {'topic': u'Pm-3m',                          'cid': 11},
            {'topic': u'8x8x8',                          'cid': 17},
            {'topic': u'PSAV',                           'cid': 22},
            {'topic': u'VASP 5.2.2',                     'cid': 23},
            {'topic': u'plane waves',                    'cid': 80},
            {'topic': u'GGA',                            'cid': 75},
            {'topic': u'black magic',                    'cid': 75},
            {'topic': u'white magic',                    'cid': 75},
            {'topic': u'perovskite',                     'cid': 8},
            {'topic': u'room-temperature superconductor','cid': 8},
            {'topic': u'insulator',                      'cid': 26},
            {'topic': u'cubic',                          'cid': 9}
        ],
        "HYO6KU4ZBQWJJIGLO3DFO44DBO2LVZGYEHTPEIDEK2WGMCI": [
            {'topic': u'Si16',                           'cid': 1},
            {'topic': u'Xx',                             'cid': 2},
            {'topic': u'Yy',                             'cid': 2},
            {'topic': u'Zz',                             'cid': 2},
            {'topic': u'Ww',                             'cid': 2},
            {'topic': u'1',                              'cid': 3},
            {'topic': u'1',                              'cid': 4},
            {'topic': u'3D',                             'cid': 5},
            {'topic': u'total energy',                   'cid': 6},
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'C<sub>s</sub>',                  'cid': 10},
            {'topic': u'Cm',                             'cid': 11},
            {'topic': u'4x4x4',                          'cid': 17},
            {'topic': u'PSAV',                           'cid': 22},
            {'topic': u'VASP 4.6.35',                    'cid': 23},
            {'topic': u'plane waves',                    'cid': 80},
            {'topic': u'GGA',                            'cid': 75},
            {'topic': u'black magic',                    'cid': 75},
            {'topic': u'white magic',                    'cid': 75},
            {'topic': u'room-temperature superconductor','cid': 8},
            {'topic': u'monoclinic',                     'cid': 9}
        ]
    }
    checksums = expected_topics_before.keys()

    @classmethod
    def setUpClass(cls):
        super(Test_Topics, cls).setUpClass(dbname=__name__.split('.')[-1])

    def test_replaced_topics(self):
        obtained_topics_before = {}
        for checksum in self.checksums:
            found_topics = map( lambda x: {'cid': x.cid, 'topic': x.topic}, self.db.session.query(model.uiTopic).join(model.tags, model.uiTopic.tid == model.tags.c.tid).filter(model.tags.c.checksum == checksum).all() )
            obtained_topics_before[checksum] = found_topics
            obtained_topics_before[checksum].sort()
            self.expected_topics_before[checksum].sort()

        try: self.assertEqual(self.expected_topics_before, obtained_topics_before,
            "Expected and found topics *before* correction differ,\n    expected:\n%s\n    found:\n%s\n" % (self.expected_topics_before, obtained_topics_before))
        except:
            TestLayerDB.failed = True
            raise
        else:
            model.correct_topics(self.db.session, model, self.checksums, 22, 'PSAV', 'REPLACE', self.engine.hierarchy)
            model.correct_topics(self.db.session, model, self.checksums, 2, ['Xx', 'Yy', 'Zz', 'Ww'], 'REPLACE', self.engine.hierarchy)
            model.correct_topics(self.db.session, model, self.checksums, 75, ['black magic', 'white magic'], 'APPEND', self.engine.hierarchy)
            model.correct_topics(self.db.session, model, self.checksums, 8, 'room-temperature superconductor', 'APPEND', self.engine.hierarchy)

            obtained_topics_after = {}
            for checksum in self.checksums:
                found_topics = map( lambda x: {'cid': x.cid, 'topic': x.topic}, self.db.session.query(model.uiTopic).join(model.tags, model.uiTopic.tid == model.tags.c.tid).filter(model.tags.c.checksum == checksum).all() )
                obtained_topics_after[checksum] = found_topics
                obtained_topics_after[checksum].sort()
                self.expected_topics_after[checksum].sort()

            try: self.assertEqual(self.expected_topics_after, obtained_topics_after,
                "Expected and found topics *after* correction differ,\n  expected:\n%s\n  found:\n%s\n" % (self.expected_topics_after, obtained_topics_after))
            except:
                TestLayerDB.failed = True
                raise
