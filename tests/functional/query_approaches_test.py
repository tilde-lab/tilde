"""
As an example, get some property of the calculations of some category,
using the relational and serialized query approaches.

some property = space group
some category = gaussian basis set type
"""
import sys
import time
import ujson as json

import set_path
from tilde.core import model
from tilde.core.api import API
from tilde.core.settings import EXAMPLE_DIR
from . import TestLayerDB


class Test_Query_Approaches(TestLayerDB):
    __test_calcs_dir__ = EXAMPLE_DIR

    _work = API()
    searched_category = (80, 'plane waves')              # defined in /init-data.sql
    searched_category_num = None                # defined in hierarchy
    space_grp_topic_source = 'ng'               # defined in parsers and set in API.classify()
    _categ_found = False
    for cid, series in _work.hierarchy_values.iteritems():
        if _categ_found: break
        elif cid == searched_category[0]:
            for num, name in series.iteritems():
                if name == searched_category[1]:
                    _categ_found, searched_category_num = True, num
                    break
    else: raise RuntimeError("Cannot determine the category number!")

    @classmethod
    def setUpClass(cls):
        super(Test_Query_Approaches, cls).setUpClass(dbname=__name__.split('.')[-1])

    def test_equality(self):
        serialized_results = {}
        tick1 = time.time()
        for checksum, grid_json in self.db.session.query(model.Grid.checksum, model.Grid.info).join(model.tags, model.Grid.checksum == model.tags.c.checksum).join(model.Topic, model.tags.c.tid == model.Topic.tid).filter(model.Topic.cid == self.searched_category[0], model.Topic.topic == self.searched_category_num).all():
            grid_json = json.loads(grid_json)
            try: serialized_results[checksum] = grid_json[self.space_grp_topic_source]
            except KeyError: pass # no such property in JSON
        self.report.warning("Query in serialized approach (%s results) took %1.2f sc" % (len(serialized_results), time.time() - tick1))

        relational_results = {}
        tick2 = time.time()
        for checksum, space_grp in self.db.session.query(model.Calculation.checksum, model.Spacegroup.n).join(model.Spacegroup, model.Calculation.checksum == model.Spacegroup.checksum).join(model.Basis, model.Calculation.checksum == model.Basis.checksum).filter(model.Basis.kind == self.searched_category_num).all():
            relational_results[checksum] = space_grp
        self.report.warning("Query in relational approach (%s results) took %1.2f sc" % (len(relational_results), time.time() - tick2))

        try: self.assertEqual(serialized_results, relational_results,
            "Approaches give different results!\nSerialized:\n%s\nRelational:\n%s\n" % (serialized_results, relational_results))
        except:
            TestLayerDB.failed = True
            raise
