#!/usr/bin/env python
#
# Remote entry point for Tilde based on websockets
# Author: Evgeny Blokhin

import os, sys
import math
import time
import logging

from sqlalchemy import text, and_, func
from sqlalchemy.orm.exc import NoResultFound
from ase.atoms import Atoms

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter

import ujson as json

import chk_tilde_install

from tilde.core.settings import settings, GUI_URL_TPL
from tilde.core.api import API
from tilde.core.common import html_formula, extract_chemical_symbols, str2html, num2name, generate_cif
import tilde.core.model as model
from tilde.berlinium import add_redirection, eplotter, wrap_cell, Async_Connection as Connection


logging.basicConfig(level=logging.WARNING)

CURRENT_TITLE = settings['title'] if settings['title'] else 'API version ' + API.version
DB_TITLE = settings['db']['default_sqlite_db'] if settings['db']['engine'] == 'sqlite' else settings['db']['dbname'] + '@' + settings['db']['engine']
settings['no_parse'] = True
work = API(settings)

class BerliniumGUIProvider:
    @staticmethod
    def login(req, client_id, db_session):
        data = {
            'title': CURRENT_TITLE,
            'debug_regime': settings['debug_regime'],
            'version': work.version,
            'cats': work.hierarchy_groups,
            'dbsize': work.count(db_session)
        }
        Connection.Clients[client_id].authorized = True

        if not req.get('settings'): req['settings'] = {}

        # *client-side* settings
        if req['settings'].get('colnum') not in [50, 100, 250]:
            req['settings']['colnum'] = 100

        if type(req['settings'].get('cols')) is not list or not 1 <= len(req['settings'].get('cols')) <= 40:
            return (None, 'Invalid settings!')

        for i in ['cols', 'colnum']:
            Connection.Clients[client_id].usettings[i] = req['settings'].get(i)

        # all available columns are compiled here and sent to user to select between them
        avcols = []
        for entity in work.hierarchy:

            if entity['has_column']:
                enabled = True if entity['cid'] in req['settings']['cols'] else False
                avcols.append({ 'cid': entity['cid'], 'category': entity['category'], 'sort': entity.get('sort', 1000), 'enabled': enabled })

        # settings of specified scope
        data['settings'] = { 'avcols': avcols, 'dbs': [DB_TITLE] }
        for i in ['exportability', 'local_dir', 'skip_unfinished', 'skip_if_path', 'webport']:
            if i in settings: data['settings'][i] = settings[i]

        return (data, None)

    @staticmethod
    def browse(req, client_id, db_session):
        data = {'html': '', 'count': 0, 'msg': None}
        error = None

        try:
            start, sortby = int(req.get('start', 0)), int(req.get('sortby', 0))
        except ValueError:
            return (data, 'Sorry, unknown parameters in request')

        start *= Connection.Clients[client_id].usettings['colnum']
        stop = start + Connection.Clients[client_id].usettings['colnum']

        if sortby   == 0:
            sortby = model.Metadata.chemical_formula
        elif sortby == 1:
            sortby = model.Metadata.location
        else:
            return (data, 'Unknown sorting requested!')

        if req.get('hashes'):
            if not isinstance(req['hashes'], list) or len(req['hashes'][0]) > 100:
                return (data, 'Invalid request!')

            proposition = req['hashes']
            data['count'] = len(proposition)
            proposition = proposition[start:stop]

        clauses = []
        if req.get('conditions'):
            join_exception = None
            for c in req['conditions']:
                if not 'cid' in c or not 'min' in c or not 'max' in c:
                    return (data, 'Invalid request!')
                try:
                    entity = [x for x in work.hierarchy if x['cid'] == int(c['cid'])][0]
                except IndexError:
                    return (data, 'Invalid category choice!')
                if not entity['has_slider']:
                    return (data, 'Invalid category choice!')

                cls, attr = entity['has_slider'].split('.')
                orm_inst = getattr(getattr(model, cls), attr)
                clauses.append(orm_inst.between(c['min'], c['max']))

                if cls == 'Lattice':
                    join_exception = cls
                else:
                    clauses.append(getattr(getattr(model, cls), 'checksum') == model.Calculation.checksum)

            if join_exception == 'Lattice':
                # Lattice objects require special join clause:
                clauses.extend([model.Lattice.struct_id == model.Structure.struct_id, model.Structure.final == True, model.Structure.checksum == model.Calculation.checksum])

        if req.get('tids'):
            for x in req['tids']:
                try: int(x)
                except: return (data, 'Invalid request!')

            proposition = []
            for i, _ in db_session.query(model.Calculation.checksum, sortby) \
                .join(model.Calculation.meta_data) \
                .join(model.Calculation.uitopics) \
                .filter(model.Topic.tid.in_(req['tids'])) \
                .group_by(model.Calculation.checksum, sortby) \
                .having(func.count(model.Topic.tid) == len(req['tids'])) \
                .filter(and_(*clauses)) \
                .order_by(sortby) \
                .slice(start, stop).all():
                proposition.append(i)

            if not proposition: return ({'msg': 'Nothing found'}, error)

            data['count'] = db_session.query(model.Calculation.checksum).join(model.Calculation.uitopics).filter(model.Topic.tid.in_(req['tids'])).group_by(model.Calculation.checksum).having(func.count(model.Topic.tid) == len(req['tids'])).filter(and_(*clauses)).count()

        elif clauses:
            proposition = []
            for i in db_session.query(model.Calculation.checksum).filter(and_(*clauses)).slice(start, stop).all():
                proposition += list(i)
            if not proposition: return ({'msg': 'Nothing found &mdash; change slider limits'}, error)

            data['count'] = db_session.query(model.Calculation.checksum).filter(and_(*clauses)).count()

        if not proposition: return (data, 'Invalid request!')

        html_output, res_count = '', 0
        html_output = '<thead><tr><th class="not-sortable"><input type="checkbox" id="d_cb_all"></th>'
        for entity in work.hierarchy:
            if entity['has_column'] and entity['cid'] in Connection.Clients[client_id].usettings['cols']:
                catname = str2html(entity['html']) if entity['html'] else entity['category'][0].upper() + entity['category'][1:]

                plottable = '<input class="sc" type="checkbox" />' if entity['plottable'] else ''

                html_output += '<th rel="' + str(entity['cid']) + '"><span>' + catname + '</span>' + plottable + '</th>'
        #if Connection.Clients[client_id].usettings['objects_expand']: html_output += '<th class="not-sortable">More...</th>'
        html_output += '</tr></thead><tbody>'

        for row, checksum in db_session.query(model.Grid.info, model.Metadata.checksum) \
            .filter(model.Grid.checksum == model.Metadata.checksum) \
            .filter(model.Grid.checksum.in_(proposition)) \
            .order_by(sortby).all():

            res_count += 1
            data_obj = json.loads(row)

            html_output += '<tr id="i_' + checksum + '" data-filename="' + data_obj.get('location', '').split(os.sep)[-1] + '">'
            html_output += '<td><input type="checkbox" id="d_cb_'+ checksum + '" class="SHFT_cb"></td>'

            for entity in work.hierarchy:
                if not entity['has_column'] or entity['cid'] not in Connection.Clients[client_id].usettings['cols']:
                    continue

                html_output += wrap_cell(entity, data_obj, work.hierarchy_values, table_view=True)

            #if Connection.Clients[client_id].usettings['objects_expand']: html_output += "<td class=objects_expand><strong>click by row</strong></td>"
            html_output += '</tr>'
        html_output += '</tbody>'

        if not res_count: return ({'msg': 'No objects found'}, error)

        data['html'] = html_output
        return (data, error)

    @staticmethod
    def tags(req, client_id, db_session):
        categs = []
        if not 'tids' in req: tids = None # standardize nulls
        else: tids = req['tids']

        if not tids:
            searchables = []
            for tid, cid, topic in db_session.query(model.Topic.tid, model.Topic.cid, model.Topic.topic).order_by(model.Topic.topic).all(): # FIXME assure there are checksums on such tid!
                try:
                    entity = [x for x in work.hierarchy if x['cid'] == cid][0]
                except IndexError:
                    return (None, 'Schema and data do not match: different versions of code and database?')

                if not entity.get('creates_topic'): continue # FIXME rewrite in SQL

                topic = num2name(topic, entity, work.hierarchy_values)
                searchables.append((tid, topic))

                if not entity.get('has_facet'): continue

                topic = html_formula(topic) if entity.get('is_chem_formula') else topic

                topic_dict = {'tid': tid, 'topic': topic}
                kind = 'tag'

                if entity['cid'] == 2: # FIXME
                    topic_dict['symbols'] = extract_chemical_symbols(topic)
                    kind = 'mendeleev'

                for n, tag in enumerate(categs):
                    if tag['cid'] == entity['cid']:
                        categs[n]['content'].append( topic_dict )
                        break
                else: categs.append({
                    'type': kind,
                    'cid': entity['cid'],
                    'category': str2html(entity['html'], False) if entity['html'] else entity['category'],
                    'sort': entity.get('sort', 1000),
                    'content': [ topic_dict ]
                })

            for entity in work.hierarchy:
                if entity['has_slider']:
                    cls, attr = entity['has_slider'].split('.')
                    orm_inst = getattr(getattr(model, cls), attr)
                    minimum, maximum = db_session.query(func.min(orm_inst), func.max(orm_inst)).one() # TODO: optimize
                    if minimum is not None and maximum is not None:
                        categs.append({
                            'type': 'slider',
                            'cid': entity['cid'],
                            'category': str2html(entity['html'], False) if entity['html'] else entity['category'],
                            'sort': entity.get('sort', 1000),
                            'min': math.floor(minimum*100)//100,
                            'max': math.ceil(maximum*100)//100
                        })

            categs.sort(key=lambda x: x['sort'])
            categs = {'blocks': categs, 'cats': work.hierarchy_groups, 'searchables': searchables}

        else:
            params = {}
            baseq = 'SELECT DISTINCT t1.tid FROM tags t1 INNER JOIN tags t2 ON t1.checksum = t2.checksum AND t2.tid = :param1'
            for n, list_item in enumerate(tids, start=1):
                params["param" + str(n)] = list_item
                if n > 1:
                    baseq += ' INNER JOIN tags t%s ON t%s.checksum = t%s.checksum AND t%s.tid = :param%s' % ( (n+1), n, (n+1), (n+1), n ) # FIXME self-joins in ORM
            current_engine = db_session.get_bind()
            for i in current_engine.execute(text(baseq), **params).fetchall():
                categs += list(i)

        return (categs, None)

    @staticmethod
    def summary(req, client_id, db_session):
        if len(req['datahash']) > 100: return (None, 'Invalid request!')

        step = -1
        clauses = [model.Lattice.struct_id == model.Structure.struct_id, model.Structure.checksum == req['datahash']]

        if step != -1:
            clauses.append(model.Structure.step == step)
        else:
            clauses.append(model.Structure.final == True)

        try:
            struct_id, a11, a12, a13, a21, a22, a23, a31, a32, a33 = db_session.query(model.Lattice.struct_id, model.Lattice.a11, model.Lattice.a12, model.Lattice.a13, model.Lattice.a21, model.Lattice.a22, model.Lattice.a23, model.Lattice.a31, model.Lattice.a32, model.Lattice.a33).filter(and_(*clauses)).one()
        except NoResultFound:
            return (None, 'Nothing found!')

        symbols, positions, is_final = [], [], False # TODO
        cell = [[a11, a12, a13], [a21, a22, a23], [a31, a32, a33]]
        for number, charge, magmom, x, y, z in db_session.query(model.Atom.number, model.Atom.charge, model.Atom.magmom, model.Atom.x, model.Atom.y, model.Atom.z).filter(model.Atom.struct_id == struct_id).all():
            symbols.append(number)
            positions.append([x, y, z])
        cif = generate_cif(Atoms(symbols=symbols, cell=cell, positions=positions, pbc=True)) # TODO

        info = db_session.query(model.Grid.info).filter(model.Grid.checksum == req['datahash']).one()
        info = json.loads(info[0])

        summary = []

        for entity in work.hierarchy:
            if not entity['has_summary_contrb']: continue # additional control to avoid redundancy
            #if entity['cid'] > 2000: # TODO apps

            catname = str2html(entity['html']) if entity['html'] else entity['category'].capitalize()
            summary.append( {'category': catname, 'sort': entity.get('sort', 1000), 'content': wrap_cell(entity, info, work.hierarchy_values)} )

        summary.sort(key=lambda x: x['sort'])

        return ({
            'phonons': None,
            'electrons': None,
            'info': info, # raw info object
            'summary': summary, # refined object
            'cif': cif
        }, None)

    @staticmethod
    def optstory(req, client_id, db_session):
        data, error = None, None

        try:
            tresholds = db_session.query(model.Struct_optimisation.tresholds) \
            .filter(model.Struct_optimisation.checksum == req['datahash']).one()
        except NoResultFound:
            return (None, 'Nothing found!')

        data = eplotter( task='optstory', data=json.loads(tresholds[0]) )

        return (data, error)

    @staticmethod
    def estory(req, client_id, db_session):
        data, error = None, None

        try:
            convergence = db_session.query(model.Energy.convergence) \
            .filter(model.Energy.checksum == req['datahash']).one()
        except NoResultFound:
            return (None, 'Nothing found!')

        data = eplotter( task='convergence', data=json.loads(convergence[0]) )

        return (data, error)

    @staticmethod
    def settings(req, client_id, db_session):
        data, error = 1, None

        # *server + client-side* settings
        if req['area'] == 'cols':
            for i in ['cols', 'colnum']:
                Connection.Clients[client_id].usettings[i] = req['settings'][i]

        else: error = 'Unknown settings context area!'

        return data, error


if __name__ == "__main__":
    Connection.GUIProvider = BerliniumGUIProvider
    DuplexRouter = SockJSRouter(Connection)

    application = web.Application(
        add_redirection(DuplexRouter.urls, GUI_URL_TPL % settings['webport']),
        debug = True if logging.getLogger().getEffectiveLevel()==logging.DEBUG or settings['debug_regime'] else False
    )
    application.listen(settings['webport'], address='0.0.0.0')

    logging.warning("%s serves http://127.0.0.1:%s" % (CURRENT_TITLE, settings['webport']))
    logging.warning("DB is %s" % DB_TITLE)
    logging.warning("Connections are %s" % Connection.Type)
    logging.warning("Press Ctrl+C to quit")

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass
