#!/usr/bin/env python
#
# Remote entry point for Tilde based on websockets
# Author: Evgeny Blokhin

# TODO render HTML entirely at the client

import os, sys
import math
import time
import logging

from sqlalchemy import text, and_, func
from sqlalchemy.orm.exc import NoResultFound
from ase.atoms import Atoms

from tornado import web, ioloop
from sockjs.tornado import SockJSRouter

import set_path
from tilde.core.settings import settings, connect_database
from tilde.core.api import API
from tilde.parsers import HASH_LENGTH
from tilde.core.common import html_formula, extract_chemical_symbols, str2html, generate_cif
import tilde.core.model as model
from tilde.berlinium import add_redirection, eplotter, wrap_cell
from tilde.berlinium.block_impl import Connection

import ujson as json


logging.basicConfig(level=logging.DEBUG)

CURRENT_TITLE = settings['title'] if settings['title'] else 'API version ' + API.version
DB_TITLE = settings['db']['default_sqlite_db'] if settings['db']['engine'] == 'sqlite' else settings['db']['dbname']
settings['no_parse'] = True
Tilde = API(settings)

class BerliniumGUIProvider:
    @staticmethod
    def login(req, session_id):
        data = {
            'title': CURRENT_TITLE,
            'debug_regime': settings['debug_regime'],
            'version': API.version,
            'cats': Tilde.supercategories
        }
        Connection.Clients[session_id].authorized = True
        Connection.Clients[session_id].db = connect_database(settings, default_actions=False, scoped=True)

        # *client-side* settings
        if req['settings']['colnum'] not in [50, 100, 250]: req['settings']['colnum'] = 100
        if type(req['settings']['cols']) is not list or not 1 <= len(req['settings']['cols']) <= 40: return (None, 'Invalid settings!')

        for i in ['cols', 'colnum']:
            Connection.Clients[session_id].usettings[i] = req['settings'][i]

        # all available columns are compiled here and sent to user for him to select between them
        avcols = []
        for entity in Tilde.hierarchy:

            if 'has_column' in entity:
                enabled = True if entity['cid'] in req['settings']['cols'] else False
                avcols.append({ 'cid': entity['cid'], 'category': entity['category'], 'sort': entity.get('sort', 1000), 'enabled': enabled })

        # settings of specified scope
        data['settings'] = { 'avcols': avcols, 'dbs': [DB_TITLE] }
        for i in ['exportability', 'local_dir', 'skip_unfinished', 'skip_if_path', 'webport']:
            if i in settings: data['settings'][i] = settings[i]

        return (data, None)

    @staticmethod
    def browse(req, session_id):
        data = {'html': '', 'count': 0, 'msg': None}
        error = None

        try: start, sortby = int(req.get('start', 0)), int(req.get('sortby', 0))
        except ValueError: return (data, 'Sorry, unknown parameters in request')
        start *= Connection.Clients[session_id].usettings['colnum']
        stop = start + Connection.Clients[session_id].usettings['colnum']
        if sortby   == 0: sortby = model.Metadata.chemical_formula
        elif sortby == 1: sortby = model.Metadata.location
        else: return (data, 'Unknown sorting requested!')

        if req.get('hashes'):
            if not isinstance(req['hashes'], list) or len(req['hashes'][0]) != HASH_LENGTH: return (data, 'Invalid request!')
            proposition = req['hashes']
            data['count'] = len(proposition)
            proposition = proposition[start:stop]

        clauses = []
        if req.get('conditions'):
            join_exception = None
            for c in req['conditions']:
                if not 'cid' in c or not 'min' in c or not 'max' in c: return (data, 'Invalid request!')
                try: entity = [x for x in Tilde.hierarchy if x['cid'] == int(c['cid'])][0]
                except IndexError: return (data, 'Invalid category choice!')

                cls, attr = entity['has_slider'].split('.')
                orm_inst = getattr(getattr(model, cls), attr)
                clauses.append(orm_inst.between(c['min'], c['max']))
                if cls == 'Lattice': join_exception = cls
                else: clauses.append(getattr(getattr(model, cls), 'checksum') == model.Calculation.checksum)

            if join_exception == 'Lattice':
                # Lattice objects require special join clause:
                clauses.extend([model.Lattice.struct_id == model.Structure.struct_id, model.Structure.final == True, model.Structure.checksum == model.Calculation.checksum])

        if req.get('tids'):
            for x in req['tids']:
                try: int(x)
                except: return (data, 'Invalid request!')

            proposition = []
            for i, _ in Connection.Clients[session_id].db.query(model.Calculation.checksum, sortby) \
                .join(model.Calculation.main_metadata) \
                .join(model.Calculation.uitopics) \
                .filter(model.uiTopic.tid.in_(req['tids'])) \
                .group_by(model.Calculation.checksum, sortby) \
                .having(func.count(model.uiTopic.tid) == len(req['tids'])) \
                .filter(and_(*clauses)) \
                .order_by(sortby) \
                .slice(start, stop).all():
                proposition.append(i)

            if not proposition: return ({'msg': 'Nothing found'}, error)

            data['count'] = Connection.Clients[session_id].db.query(model.Calculation.checksum).join(model.Calculation.uitopics).filter(model.uiTopic.tid.in_(req['tids'])).group_by(model.Calculation.checksum).having(func.count(model.uiTopic.tid) == len(req['tids'])).filter(and_(*clauses)).count()

        elif clauses:
            proposition = []
            for i in Connection.Clients[session_id].db.query(model.Calculation.checksum).filter(and_(*clauses)).slice(start, stop).all():
                proposition += list(i)
            if not proposition: return ({'msg': 'Nothing found &mdash; change slider limits'}, error)

            data['count'] = Connection.Clients[session_id].db.query(model.Calculation.checksum).filter(and_(*clauses)).count()

        if not proposition: return (data, 'Invalid request!')

        html_output, res_count = '', 0
        html_output = '<thead><tr><th class=not-sortable><input type="checkbox" id="d_cb_all"></th>'
        for entity in Tilde.hierarchy:
            if 'has_column' in entity and entity['cid'] in Connection.Clients[session_id].usettings['cols']:
                catname = str2html(entity['html']) if 'html' in entity else entity['category'][0].upper() + entity['category'][1:]

                plottable = '<input class=sc type=checkbox />' if 'plottable' in entity else ''

                html_output += '<th rel=' + str(entity['cid']) + '><span>' + catname + '</span>' + plottable + '</th>'
        #if Connection.Clients[session_id].usettings['objects_expand']: html_output += '<th class="not-sortable">More...</th>'
        html_output += '</tr></thead><tbody>'

        for row, checksum in Connection.Clients[session_id].db.query(model.uiGrid.info, model.Metadata.checksum) \
            .filter(model.uiGrid.checksum == model.Metadata.checksum) \
            .filter(model.uiGrid.checksum.in_(proposition)) \
            .order_by(sortby).all():

            res_count += 1
            data_obj = json.loads(row)

            html_output += '<tr id=i_' + checksum + '>'
            html_output += '<td><input type=checkbox id=d_cb_'+ checksum + ' class=SHFT_cb></td>'

            for entity in Tilde.hierarchy:
                if not 'has_column' in entity: continue
                if not entity['cid'] in Connection.Clients[session_id].usettings['cols']: continue

                html_output += wrap_cell(entity, data_obj, table_view=True)

            #if Connection.Clients[session_id].usettings['objects_expand']: html_output += "<td class=objects_expand><strong>click by row</strong></td>"
            html_output += '</tr>'
        html_output += '</tbody>'

        if not res_count: return ({'msg': 'No objects found.'}, error)

        data['html'] = html_output
        return (data, error)

    @staticmethod
    def tags(req, session_id):
        ui_controls = []
        if not 'tids' in req: tids = None # standardize nulls
        else: tids = req['tids']

        if not tids:
            for tid, cid, topic in Connection.Clients[session_id].db.query(model.uiTopic.tid, model.uiTopic.cid, model.uiTopic.topic).all():
                # TODO assure there are checksums on such tid!!!

                try: entity = [x for x in Tilde.hierarchy if x['cid'] == cid][0]
                except IndexError: return (None, 'Schema and data do not match: different versions of code and database?')

                if not entity.get('has_facet'): continue

                ready_topic = html_formula(topic) if entity.get('is_chem_formula') else topic

                topic_dict = {'tid': tid, 'topic': ready_topic}
                kind = 'tag'

                if entity['cid'] == 2: # FIXME
                    topic_dict['symbols'] = extract_chemical_symbols(topic)
                    kind = 'mendeleev'

                for n, tag in enumerate(ui_controls):
                    if tag['category'] == entity['category']:
                        ui_controls[n]['content'].append( topic_dict )
                        break
                else: ui_controls.append({
                            'type': kind,
                            'cid': entity['cid'],
                            'category': entity['category'],
                            'sort': entity.get('sort', 1000),
                            'content': [ topic_dict ]
                })

            for entity in Tilde.hierarchy:
                if 'has_slider' in entity:
                    cls, attr = entity['has_slider'].split('.')
                    orm_inst = getattr(getattr(model, cls), attr)
                    minimum, maximum = Connection.Clients[session_id].db.query(func.min(orm_inst), func.max(orm_inst)).one() # TODO: optimize
                    if minimum is not None and maximum is not None:
                        ui_controls.append({
                            'type': 'slider',
                            'cid': entity['cid'],
                            'category': entity['category'],
                            'sort': entity.get('sort', 1000),
                            'min': math.floor(minimum*100)/100,
                            'max': math.ceil(maximum*100)/100
                        })

            ui_controls.sort(key=lambda x: x['sort'])
            ui_controls = {'blocks': ui_controls, 'cats': Tilde.supercategories}

        else:
            params = {}
            baseq = 'SELECT DISTINCT t1.tid FROM tags t1 INNER JOIN tags t2 ON t1.checksum = t2.checksum AND t2.tid = :param1'
            for n, list_item in enumerate(tids, start=1):
                params["param" + str(n)] = list_item
                if n > 1:
                    baseq += ' INNER JOIN tags t%s ON t%s.checksum = t%s.checksum AND t%s.tid = :param%s' % ( (n+1), n, (n+1), (n+1), n ) # FIXME self-joins in ORM
            current_engine = Connection.Clients[session_id].db.get_bind()
            for i in current_engine.execute(text(baseq), **params).fetchall():
                ui_controls += list(i)

        return (ui_controls, None)

    @staticmethod
    def summary(req, session_id):
        if len(req['datahash']) != HASH_LENGTH: return (None, 'Invalid request!')

        step = -1
        clauses = [model.Lattice.struct_id == model.Structure.struct_id, model.Structure.checksum == req['datahash']]

        if step != -1: clauses.append(model.Structure.step == step)
        else: clauses.append(model.Structure.final == True)

        try: struct_id, a11, a12, a13, a21, a22, a23, a31, a32, a33 = Connection.Clients[session_id].db.query(model.Lattice.struct_id, model.Lattice.a11, model.Lattice.a12, model.Lattice.a13, model.Lattice.a21, model.Lattice.a22, model.Lattice.a23, model.Lattice.a31, model.Lattice.a32, model.Lattice.a33).filter(and_(*clauses)).one()
        except NoResultFound: return (None, 'Nothing found!')

        symbols, positions, is_final = [], [], False # TODO
        cell = [[a11, a12, a13], [a21, a22, a23], [a31, a32, a33]]
        for number, charge, magmom, x, y, z in Connection.Clients[session_id].db.query(model.Atom.number, model.Atom.charge, model.Atom.magmom, model.Atom.x, model.Atom.y, model.Atom.z).filter(model.Atom.struct_id == struct_id).all():
            symbols.append(number)
            positions.append([x, y, z])
        cif = generate_cif(Atoms(symbols=symbols, cell=cell, positions=positions, pbc=True)) # TODO

        info = Connection.Clients[session_id].db.query(model.uiGrid.info) \
            .filter(model.uiGrid.checksum == req['datahash']).one()

        summary = []
        info = json.loads(info[0])

        for entity in Tilde.hierarchy:
            if not 'has_summary_contrb' in entity: continue # additional control to avoid redundancy
            #if entity['cid'] > 2000: # TODO apps

            catname = str2html(entity['html']) if 'html' in entity else entity['category'].capitalize()
            summary.append( {'category': catname, 'sort': entity.get('sort', 1000), 'content': wrap_cell(entity, info)} )

        summary.sort(key=lambda x: x['sort'])

        return ({
            'phonons': None,
            'electrons': None,
            'info': info, # raw info object
            'summary': summary, # refined object
            'cif': cif
        }, None)

    @staticmethod
    def optstory(req, session_id):
        data, error = None, None

        try: tresholds = Connection.Clients[session_id].db.query(model.Struct_optimisation.tresholds) \
            .filter(model.Struct_optimisation.checksum == req['datahash']).one()
        except NoResultFound: return (None, 'Nothing found!')

        data = eplotter( task='optstory', data=json.loads(tresholds[0]) )

        return (data, error)

    @staticmethod
    def estory(req, session_id):
        data, error = None, None

        try: convergence = Connection.Clients[session_id].db.query(model.Energy.convergence) \
            .filter(model.Energy.checksum == req['datahash']).one()
        except NoResultFound: return (None, 'Nothing found!')

        data = eplotter( task='convergence', data=json.loads(convergence[0]) )

        return (data, error)

    @staticmethod
    def settings(req, session_id):
        data, error = 1, None

        # *server + client-side* settings
        if req['area'] == 'cols':
            for i in ['cols', 'colnum']:
                Connection.Clients[session_id].usettings[i] = req['settings'][i]

        else: error = 'Unknown settings context area!'

        return data, error


if __name__ == "__main__":
    test_session = connect_database(settings)
    test_session.close()

    Connection.GUIProvider = BerliniumGUIProvider
    DuplexRouter = SockJSRouter(Connection)

    application = web.Application(
        add_redirection(DuplexRouter.urls, settings['gui_url']),
        debug = True if logging.getLogger().getEffectiveLevel()==logging.DEBUG or settings['debug_regime'] else False
    )
    application.listen(settings['webport'], address='0.0.0.0')

    logging.debug("%s (%s backend) is on the air on port %s\nPress Ctrl+C to quit\n" % (CURRENT_TITLE, settings['db']['engine'], settings['webport']))

    try: ioloop.IOLoop.instance().start()
    except KeyboardInterrupt: pass
