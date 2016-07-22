"""
As an example, get some property of the calculations of some category,
using the relational and serialized query approaches.

some property = space group
some category = gaussian basis set type
"""
from __future__ import print_function

import sys
import time
import ujson as json
import six

from . import set_path
from tilde.core import model
from tilde.core.api import API
from tilde.core.settings import EXAMPLE_DIR
from . import TestLayerDB


class Hierarchy_Params(object):
    work = API()
    searched_category = (80, 'gaussians')       # defined in /init-data.sql
    searched_category_num = None                # defined in hierarchy
    space_grp_topic_source = 'ng'               # defined in parsers and set in API.classify()
    categ_found = False
    for cid, series in six.iteritems(work.hierarchy_values):
        if categ_found: break
        elif cid == searched_category[0]:
            for num, name in six.iteritems(series):
                if name == searched_category[1]:
                    categ_found, searched_category_num = True, num
                    break
    else: raise RuntimeError("Cannot determine the category number!")

def get_serialized_results(sess_handle, topic_cid, topic_num, topic_src):
    serialized_results = {}
    for checksum, grid_json in sess_handle.query(model.Grid.checksum, model.Grid.info).join(model.tags, model.Grid.checksum == model.tags.c.checksum).join(model.Topic, model.tags.c.tid == model.Topic.tid).filter(model.Topic.cid == topic_cid, model.Topic.topic == topic_num).all():
        grid_json = json.loads(grid_json)
        try: serialized_results[checksum] = grid_json[topic_src]
        except KeyError: pass # no such property in JSON
    return serialized_results

def get_relational_results(sess_handle, topic_num):
    relational_results = {}
    for checksum, space_grp in sess_handle.query(model.Calculation.checksum, model.Spacegroup.n).join(model.Spacegroup, model.Calculation.checksum == model.Spacegroup.checksum).join(model.Basis, model.Calculation.checksum == model.Basis.checksum).filter(model.Basis.kind == topic_num).all():
        relational_results[checksum] = space_grp
    return relational_results

class Test_Query_Approaches(TestLayerDB):
    __test_calcs_dir__ = EXAMPLE_DIR

    @classmethod
    def setUpClass(cls):
        super(Test_Query_Approaches, cls).setUpClass(dbname=__name__.split('.')[-1])

    def test_equality(self):
        tick1 = time.time()
        serialized_results = get_serialized_results(
            self.db.session,
            Hierarchy_Params.searched_category[0],
            Hierarchy_Params.searched_category_num,
            Hierarchy_Params.space_grp_topic_source
        )
        tick2 = time.time()
        self.report.warning("Query in serialized approach (%s results) took %1.2f sc" % (len(serialized_results), tick2 - tick1))

        tick1 = time.time()
        relational_results = get_relational_results(
            self.db.session,
            Hierarchy_Params.searched_category_num
        )
        tick2 = time.time()
        self.report.warning("Query in relational approach (%s results) took %1.2f sc" % (len(relational_results), tick2 - tick1))

        try: self.assertEqual(serialized_results, relational_results,
            "Approaches give different results!\nSerialized:\n%s\nRelational:\n%s\n" % (serialized_results, relational_results))
        except:
            TestLayerDB.failed = True
            raise


if __name__ == "__main__":
    # NB -m tests.functional.query_approaches_test

    from tilde.core.settings import settings, connect_database

    session = connect_database(settings, default_actions=False)
    print("DB: %s" % (settings['db']['default_sqlite_db'] if settings['db']['engine'] == 'sqlite' else settings['db']['dbname']))

    tick1 = time.time()
    serialized_results = get_serialized_results(
        session,
        Hierarchy_Params.searched_category[0],
        Hierarchy_Params.searched_category_num,
        Hierarchy_Params.space_grp_topic_source
    )
    tick2 = time.time()
    print("Query in serialized approach (%s results) took %1.2f sc" % (len(serialized_results), tick2 - tick1))

    tick1 = time.time()
    relational_results = get_relational_results(
        session,
        Hierarchy_Params.searched_category_num
    )
    tick2 = time.time()
    print("Query in relational approach (%s results) took %1.2f sc" % (len(relational_results), tick2 - tick1))

    print("Results equal?", serialized_results==relational_results)
