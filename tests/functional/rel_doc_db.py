
import time
import ujson as json

import set_path
from tilde.core import model
from tilde.core.api import API
from tilde.core.settings import settings, connect_database


session = connect_database(settings)
searched_bstype = 'gaussians'
space_grp_topic_source = 'ng' # defined by API.classify()
serialized_results, relational_results = {}, {}

tick1 = time.time()
for checksum, grid_json in session.query(model.uiGrid.checksum, model.uiGrid.info).join(model.tags, model.uiGrid.checksum == model.tags.c.checksum).join(model.uiTopic, model.tags.c.tid == model.uiTopic.tid).filter(model.uiTopic.topic == searched_bstype).all():
    grid_json = json.loads(grid_json)
    try: serialized_results[checksum] = grid_json[space_grp_topic_source]
    except KeyError: pass # no such property in datasets JSON
print "Query in serialized approach took %1.2f sc" % (time.time() - tick1)

tick2 = time.time()
for checksum, space_grp in session.query(model.Calculation.checksum, model.Spacegroup.n).join(model.Spacegroup, model.Calculation.checksum == model.Spacegroup.checksum).join(model.Basis, model.Calculation.checksum == model.Basis.checksum).filter(model.Basis.kind == searched_bstype).all():
    relational_results[checksum] = space_grp
print "Query in relational approach took %1.2f sc" % (time.time() - tick2)

print "Approaches give equal results?", serialized_results == relational_results
