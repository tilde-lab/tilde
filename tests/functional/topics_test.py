
import os
from operator import itemgetter
from pprint import pformat

import tilde.core.model as model
from tilde.core.settings import EXAMPLE_DIR
from . import TestLayerDB


class Test_Topics(TestLayerDB):
    __test_calcs_dir__ = os.path.join(EXAMPLE_DIR, 'VASP')
    expected_topics_before = {
        "U6DLJBOGUN5JNT736TBXPCQVQPA4CPWCXWMVACMHLRDZGCI": [
            {'topic': u'SrTiO3',                         'cid': 1},
            {'topic': u'Sr',                             'cid': 2},
            {'topic': u'Ti',                             'cid': 2},
            {'topic': u'O',                              'cid': 2},
            {'topic': u'3',                              'cid': 3},
            {'topic': u'3',                              'cid': 5},
            {'topic': u'1',                              'cid': 6},
            #{'topic': u'2',                              'cid': 6}, FIXME
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'O<sub>h</sub>',                  'cid': 10},
            {'topic': u'Pm-3m',                          'cid': 11},
            #{'topic': u'8x8x8',                          'cid': 17}, FIXME
            {'topic': u'2',                              'cid': 22},
            {'topic': u'2',                              'cid': 80},
            {'topic': u'2',                              'cid': 75},
            {'topic': u'4',                              'cid': 8},
            {'topic': u'0',                              'cid': 26}, #{'topic': u'1' FIXME
            {'topic': u'cubic',                          'cid': 9},
            {'topic': u'none',                           'cid': 510},
            {'topic': u'none',                           'cid': 511},
            {'topic': u'none',                           'cid': 150},
            {'topic': u'1',                              'cid': 15},
            {'topic': u'0',                              'cid': 28},
            {'topic': u'221 &mdash; Pm-3m',              'cid': 50},
            {'topic': u'2',                              'cid': 1006},
            {'topic': u'0',                              'cid': 106}
        ],
        "EPVVPXXAWI6K2D746ETSOSMHE42TKFWRIQJ4SUASFAZAECI": [
            {'topic': u'Si16',                           'cid': 1},
            {'topic': u'Si',                             'cid': 2},
            {'topic': u'1',                              'cid': 3},
            {'topic': u'3',                              'cid': 5},
            {'topic': u'1',                              'cid': 6},
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'C<sub>s</sub>',                  'cid': 10},
            {'topic': u'Cm',                             'cid': 11},
            #{'topic': u'4x4x4',                          'cid': 17}, FIXME
            {'topic': u'2',                              'cid': 22},
            {'topic': u'2',                              'cid': 80},
            {'topic': u'2',                              'cid': 75},
            {'topic': u'monoclinic',                     'cid': 9},
            {'topic': u'none',                           'cid': 510},
            {'topic': u'none',                           'cid': 511},
            {'topic': u'none',                           'cid': 150},
            {'topic': u'1',                              'cid': 15},
            {'topic': u'0',                              'cid': 26},
            {'topic': u'0',                              'cid': 28},
            {'topic': u'8 &mdash; Cm',                   'cid': 50},
            {'topic': u'2',                              'cid': 1006},
            {'topic': u'0',                              'cid': 106}
        ]
    }
    expected_topics_after = {
        "U6DLJBOGUN5JNT736TBXPCQVQPA4CPWCXWMVACMHLRDZGCI": [
            {'topic': u'SrTiO3',                         'cid': 1},
            {'topic': u'Xx',                             'cid': 2},
            {'topic': u'Yy',                             'cid': 2},
            {'topic': u'Zz',                             'cid': 2},
            {'topic': u'Ww',                             'cid': 2},
            {'topic': u'3',                              'cid': 3},
            {'topic': u'3',                              'cid': 5},
            {'topic': u'1',                              'cid': 6},
            #{'topic': u'2',                              'cid': 6}, FIXME
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'O<sub>h</sub>',                  'cid': 10},
            {'topic': u'Pm-3m',                          'cid': 11},
            #{'topic': u'8x8x8',                          'cid': 17}, FIXME
            {'topic': u'5',                              'cid': 22},
            {'topic': u'2',                              'cid': 80},
            {'topic': u'2',                              'cid': 75},
            {'topic': u'222',                            'cid': 75},
            {'topic': u'240',                            'cid': 75},
            {'topic': u'4',                              'cid': 8},
            {'topic': u'165',                            'cid': 8},
            {'topic': u'0',                              'cid': 26}, #{'topic': u'1', FIXME
            {'topic': u'cubic',                          'cid': 9},
            {'topic': u'none',                           'cid': 510},
            {'topic': u'none',                           'cid': 511},
            {'topic': u'none',                           'cid': 150},
            {'topic': u'1',                              'cid': 15},
            {'topic': u'0',                              'cid': 28},
            {'topic': u'221 &mdash; Pm-3m',              'cid': 50},
            {'topic': u'2',                              'cid': 1006},
            {'topic': u'0',                              'cid': 106}
        ],
        "EPVVPXXAWI6K2D746ETSOSMHE42TKFWRIQJ4SUASFAZAECI": [
            {'topic': u'Si16',                           'cid': 1},
            {'topic': u'Xx',                             'cid': 2},
            {'topic': u'Yy',                             'cid': 2},
            {'topic': u'Zz',                             'cid': 2},
            {'topic': u'Ww',                             'cid': 2},
            {'topic': u'1',                              'cid': 3},
            {'topic': u'3',                              'cid': 5},
            {'topic': u'1',                              'cid': 6},
            {'topic': u'PBE',                            'cid': 7},
            {'topic': u'C<sub>s</sub>',                  'cid': 10},
            {'topic': u'Cm',                             'cid': 11},
            #{'topic': u'4x4x4',                          'cid': 17}, FIXME
            {'topic': u'5',                              'cid': 22},
            {'topic': u'2',                              'cid': 80},
            {'topic': u'2',                              'cid': 75},
            {'topic': u'222',                            'cid': 75},
            {'topic': u'240',                            'cid': 75},
            {'topic': u'165',                            'cid': 8},
            {'topic': u'monoclinic',                     'cid': 9},
            {'topic': u'none',                           'cid': 510},
            {'topic': u'none',                           'cid': 511},
            {'topic': u'none',                           'cid': 150},
            {'topic': u'1',                              'cid': 15},
            {'topic': u'0',                              'cid': 26},
            {'topic': u'0',                              'cid': 28},
            {'topic': u'8 &mdash; Cm',                   'cid': 50},
            {'topic': u'2',                              'cid': 1006},
            {'topic': u'0',                              'cid': 106}
        ]
    }
    checksums = list(expected_topics_before)

    @classmethod
    def setUpClass(cls):
        super(Test_Topics, cls).setUpClass(dbname=__name__.split('.')[-1])

    def test_replaced_topics(self):
        obtained_topics_before = {}
        for checksum in self.checksums:
            found_topics = list(map( lambda x: {'cid': x.cid, 'topic': x.topic}, self.db.session.query(model.Topic).join(model.tags, model.Topic.tid == model.tags.c.tid).filter(model.tags.c.checksum == checksum).all() ))
            obtained_topics_before[checksum] = found_topics
            obtained_topics_before[checksum].sort(key=itemgetter('cid', 'topic'))
            self.expected_topics_before[checksum].sort(key=itemgetter('cid', 'topic'))

        try: self.assertEqual(self.expected_topics_before, obtained_topics_before,
            "Expected and found topics *before* correction differ,\n    expected:\n%s\n    found:\n%s\n" % (
                pformat(self.expected_topics_before),
                pformat(obtained_topics_before)
            ))
        except:
            TestLayerDB.failed = True
            raise
        else:
            model.correct_topics(self.db.session, model, self.checksums, 22,    '5',                         'REPLACE', self.engine.hierarchy)
            model.correct_topics(self.db.session, model, self.checksums, 2,     ['Xx', 'Yy', 'Zz', 'Ww'],    'REPLACE', self.engine.hierarchy)
            model.correct_topics(self.db.session, model, self.checksums, 75,    [str(0xDE), str(0xF0)],      'APPEND', self.engine.hierarchy)
            model.correct_topics(self.db.session, model, self.checksums, 8,     str(0xA5),                   'APPEND', self.engine.hierarchy)

            obtained_topics_after = {}
            for checksum in self.checksums:
                found_topics = list(map( lambda x: {'cid': x.cid, 'topic': x.topic}, self.db.session.query(model.Topic).join(model.tags, model.Topic.tid == model.tags.c.tid).filter(model.tags.c.checksum == checksum).all() ))
                obtained_topics_after[checksum] = found_topics
                obtained_topics_after[checksum].sort(key=itemgetter('cid', 'topic'))
                self.expected_topics_after[checksum].sort(key=itemgetter('cid', 'topic'))

            try: self.assertEqual(self.expected_topics_after, obtained_topics_after,
                "Expected and found topics *after* correction differ,\n  expected:\n%s\n  found:\n%s\n" % (
                    pformat(self.expected_topics_after),
                    pformat(obtained_topics_after)
                ))
            except:
                TestLayerDB.failed = True
                raise
