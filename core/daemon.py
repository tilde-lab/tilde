#!/usr/bin/env python
#
# Tilde project: daemon
# (acting as a GUI service)
# Provides a user interface for database management
# NB: non-english users of python on Windows beware mimetypes in registry HKEY_CLASSES_ROOT/MIME/Database/ContentType (see http://bugs.python.org/review/9291/patch/191/354)
# v190514

import os
import sys
import json
import socket
import time
from itertools import ifilter
import math
import logging

from numpy import dot
from numpy import array

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps')) # this is done to have all 3rd party code in core/deps

import tornado
from sockjs.tornado import SockJSRouter, SockJSConnection

from ase.data import chemical_symbols, covalent_radii
from ase.data.colors import jmol_colors
from ase.lattice.spacegroup.cell import cell_to_cellpar

from settings import settings, connect_database, write_settings, write_db, check_db_version, repositories, DATA_DIR, MAX_CONCURRENT_DBS
from api import API
from common import dict2ase, html_formula, str2html
from plotter import bdplotter, eplotter


DELIM = '~#~#~'
CURRENT_TITLE = settings['title'] if settings['title'] else 'Tilde ' + API.version
E_LOWER_DEFAULT = -7.0
E_UPPER_DEFAULT = 7.0
if settings['db']['type'] == 'sqlite': DEFAULT_DBTITLE = settings['default_sqlite_db']
elif settings['db']['type'] == 'postgres': DEFAULT_DBTITLE = 'master.db'

Tilde = API()

# NB:
# Users stores User objects associated with their sessions
# Repo_pool stores opened DB handles
# Tilde_tags stores DataMap instances for opened DBs
Users, Repo_pool, Tilde_tags = {}, {}, {}

class User:
    def __init__(self):
        self.usettings = {}
        self.cur_db = DEFAULT_DBTITLE

class DataMap:
    def __init__(self, db_name):
        self.c2t = {}
        self.t2c = {}
        self.error = None
        cursor = Repo_pool[db_name].cursor()
        try: cursor.execute( 'SELECT checksum, tid FROM tags' )
        except:
            Repo_pool[db_name].commit() # Postgres: prevent transaction aborting...
            self.error = 'DataMap error: ' + "%s" % sys.exc_info()[1]
        else:
            for row in cursor.fetchall():
                i = int(row[1])

                try: self.c2t[ row[0] ]
                except KeyError: self.c2t[ row[0] ] = [ i ]
                else: self.c2t[ row[0] ].append( i )

                try: self.t2c[ i ]
                except KeyError: self.t2c[ i ] = [ row[0] ]
                else: self.t2c[ i ].append( row[0] )

    def c_by_t(self, *args):
        checksums = self.t2c[ int(args[0]) ]
        for n, arg in enumerate(args):
            try: args[n + 1]
            except IndexError: break
            else: checksums = list(  set(checksums) & set(self.t2c[ int(args[n + 1]) ])  ) # logic AND intersection
        return list(set(checksums))

    def t_by_c(self, *args):
        tags = []
        for arg in args:
            tags.extend( self.c2t[ arg ] ) # logic OR intersection
        return list(set(tags))              

class Request_Handler:
    @staticmethod
    def login(userobj, session_id):
        data, error = { 'title': CURRENT_TITLE, 'demo_regime': settings['demo_regime'], 'debug_regime': settings['debug_regime'], 'version': API.version, 'custom_about_link': settings['custom_about_link'], 'cats': Tilde.supercategories  }, None
        
        # *client-side* settings
        if userobj['settings']['colnum'] not in [50, 100, 500]: userobj['settings']['colnum'] = 100
        if type(userobj['settings']['cols']) is not list or not 1 <= len(userobj['settings']['cols']) <= 25: return (None, 'Invalid settings!')

        global Users
        for i in ['cols', 'colnum', 'objects_expand']:
            Users[session_id].usettings[i] = userobj['settings'][i]

        # all available columns are compiled here and sent to user for him to select between them
        avcols = []
        for item in Tilde.hierarchy:
            
            if 'has_column' in item:
                if 'source' in item and '#' in item['source']: continue # todo
                enabled = True if item['cid'] in userobj['settings']['cols'] else False
                avcols.append({ 'cid': item['cid'], 'category': item['category'], 'sort': item['sort'], 'enabled': enabled })

        # settings of specified scope
        data['settings'] = { 'avcols': avcols, 'dbs': [DEFAULT_DBTITLE] + filter(lambda x: x != DEFAULT_DBTITLE, Repo_pool.keys()) }
        for i in ['exportability', 'quick_regime', 'local_dir', 'skip_unfinished', 'skip_if_path', 'webport', 'db']:
            if i in settings: data['settings'][i] = settings[i]

        # TODO: RESTRICT IN ACTIONS EVERYBODY EXCEPT THE FIRST USER!
        
        data = json.dumps(data)
        return (data, error)

    @staticmethod
    def list(userobj, session_id):
        data, error = None, None
        if settings['demo_regime']: return (data, 'Action not allowed!')

        userobj['path'] = userobj['path'].replace('../', '')
        discover = settings['local_dir'] + userobj['path']
        if not os.path.exists(discover): error = 'Not existing path was requested!'
        elif not os.access(discover, os.R_OK): error = 'A requested path is not readable (check privileges?)'
        else:
            if userobj['transport'] in Tilde.Conns.keys():
                data, error = Tilde.Conns[ userobj['transport'] ]['list']( userobj['path'], settings['local_dir'] )
            if not data and not userobj['path'] and not error: data = 'Notice: specified folder is empty.'
        return (data, error)

    @staticmethod
    def report(userobj, session_id, callback=None):
        data, error = None, None
        if settings['demo_regime']: return (data, 'Action not allowed!')
        if not settings['local_dir']: return (data, 'Please, define working path!')
        userobj['path'] = userobj['path'].replace('../', '')

        if not error:
            if userobj['transport'] in Tilde.Conns.keys():
                data, error = Tilde.Conns[ userobj['transport'] ]['report']( userobj['path'], settings['local_dir'], Tilde )
        
        if not error:
            global Tilde_tags
            if Users[session_id].cur_db in Tilde_tags:
                # force update tags in memory
                Tilde_tags[ Users[session_id].cur_db ] = DataMap( Users[session_id].cur_db )
                if Tilde_tags[ Users[session_id].cur_db ].error:
                    error = 'DataMap creation error: ' + Tilde_tags[ Users[session_id].cur_db ].error

        if callback: callback( (data, error) )
        else: return (data, error)

    @staticmethod
    def browse(userobj, session_id):
        data, error = None, None

        startn = 0 # not user-editable actually

        global Tilde_tags
        if not Users[session_id].cur_db in Tilde_tags: Tilde_tags[ Users[session_id].cur_db ] = DataMap( Users[session_id].cur_db )
        if Tilde_tags[ Users[session_id].cur_db ].error: return (data, 'DataMap creation error: ' + Tilde_tags[ Users[session_id].cur_db ].error)

        if not 'tids' in userobj: tids = None # json may contain nulls, standardize them
        else: tids = userobj['tids']

        if tids:
            data_clause = Tilde_tags[ Users[session_id].cur_db ].c_by_t( *tids )
            rlen = len(data_clause)

        elif 'hashes' in userobj:
            data_clause = userobj['hashes']
            rlen = len(data_clause)
            if not rlen or not isinstance(data_clause, list) or len(data_clause[0]) != 56: return (data, 'Invalid browsing!')

        else: return (data, 'Error: neither tid nor hash was provided!')        
        
        data_clause = data_clause[ startn : Users[session_id].usettings['colnum']+1 ]
        data_clause = map(lambda x: x.encode('utf-8'), data_clause) # for postgres
        if len(data_clause) == 1: data_clause.append('dummy_entity_to_prevent_an_error_with_one_value') # for postgres
        
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        try:            
            if settings['db']['type'] == 'sqlite':         cursor.execute('SELECT checksum, structures, energy, info, apps FROM results WHERE checksum IN ("%s")' % ('","'.join(data_clause),))
            elif settings['db']['type'] == 'postgres':     cursor.execute('SELECT checksum, structures, energy, info, apps FROM results WHERE checksum IN %s' % (tuple(data_clause),))
        except: error = 'DB error: ' + "%s" % sys.exc_info()[1]
        else:
            rescount = 0
            
            # building data table header: compulsory part
            data = '<thead>'
            data += '<tr>'
            data += '<th class=not-sortable><input type="checkbox" id="d_cb_all"></th>'
            
            # dynamic part
            for item in Tilde.hierarchy:
                if 'has_column' in item and item['cid'] in Users[session_id].usettings['cols']:
                    if 'source' in item and '#' in item['source']: continue # todo
                    
                    catname = str2html(item['html']) if 'html' in item else item['category'][0].upper() + item['category'][1:]
                    
                    plottable = '<input class=sc type=checkbox />' if 'plottable' in item else ''
                    
                    data += '<th rel=' + str(item['cid']) + '><span>' + catname + '</span>' + plottable + '</th>'
            
            # compulsory part
            if Users[session_id].usettings['objects_expand']: data += '<th class="not-sortable">More...</th>'
            data += '</tr>'
            data += '</thead>'
            data += '<tbody>'
            
            for row in cursor.fetchall():
                
                # building data table rows
                rescount += 1
                data_obj = {}
                data_obj['structures'] = json.loads(row[1])
                data_obj['energy'] = row[2]
                data_obj['info'] = json.loads(row[3])
                data_obj['apps'] = json.loads(row[4])

                # compulsory part
                data += '<tr id=i_' + row[0] + '>'
                data += '<td><input type=checkbox id=d_cb_'+ row[0] + ' class=SHFT_cb></td>'

                # dynamic part
                for item in Tilde.hierarchy:
                    if not 'has_column' in item: continue
                    if not item['cid'] in Users[session_id].usettings['cols']: continue
                    if 'source' in item and '#' in item['source']: continue # todo
                    
                    data += Tilde.wrap_cell(item, data_obj, table_view=True)

                # --compulsory part--
                if Users[session_id].usettings['objects_expand']: data += "<td class=objects_expand><strong>click by row</strong></td>"
                data += '</tr>'
            data += '</tbody>'
            if not rescount: error = 'No objects match!'
            data += '||||Matched items: %s' % rlen
            if rescount > Users[session_id].usettings['colnum']: data += ' (%s shown)' % Users[session_id].usettings['colnum']
        return (data, error)

    @staticmethod
    def tags(userobj, session_id):
        data, error = None, None

        global Tilde_tags
        if not Users[session_id].cur_db in Tilde_tags: Tilde_tags[ Users[session_id].cur_db ] = DataMap( Users[session_id].cur_db )
        if Tilde_tags[ Users[session_id].cur_db ].error: return (data, 'DataMap creation error: ' + Tilde_tags[ Users[session_id].cur_db ].error)

        if not 'tids' in userobj: tids = None # json may contain nulls, standardize them
        else: tids = userobj['tids']
                
        if not tids:
            cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
            try: cursor.execute( 'SELECT tid, categ, topic FROM topics' )
            except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])
            
            tags = []
            for item in cursor.fetchall():
                if not item[0] in Tilde_tags[ Users[session_id].cur_db ].t2c: continue # this is to assure there are checksums on such tid
                
                try: match = [x for x in Tilde.hierarchy if x['cid'] == item[1]][0]
                except IndexError: return (data, 'Schema and data do not match: different versions of code and database?')
                
                if not 'has_label' in match or not match['has_label']: continue
                
                if match['cid'] in [1, 511, 521, 522]: i = html_formula(item[2]) # TODO!!!
                else: i = item[2]

                if not 'sort' in match: sort = 1000
                else: sort = match['sort']
                for n, tag in enumerate(tags):
                    if tag['category'] == match['category']:
                        tags[n]['content'].append( {'tid': item[0], 'topic': i} )
                        break
                else: tags.append({'cid': match['cid'], 'category': match['category'], 'sort': sort, 'content': [ {'tid': item[0], 'topic': i} ]})

            tags.sort(key=lambda x: x['sort'])
            
            tags = {'blocks': tags, 'cats': Tilde.supercategories}
        else:
            data_clause = Tilde_tags[ Users[session_id].cur_db ].c_by_t( *tids )
            tags = Tilde_tags[ Users[session_id].cur_db ].t_by_c( *data_clause )
        data = json.dumps(tags)
        return (data, error)

    @staticmethod
    def phonons(userobj, session_id):
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT phonons FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: error = 'DB error: ' + "%s" % sys.exc_info()[1]
        else:
            row = cursor.fetchone()
            data = row[0]
        return (data, error)

    @staticmethod
    def summary(userobj, session_id):
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT structures, energy, phonons, electrons, info, apps FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: error = 'DB error: ' + "%s" % sys.exc_info()[1]
        else:
            row = cursor.fetchone()
            if row is None: error = 'No objects found!'
            else:
                # TODO
                summary = []
                data_obj = {}
                data_obj['structures'] = json.loads(row[0])
                data_obj['energy'] = row[1]
                data_obj['info'] = json.loads(row[4])
                data_obj['apps'] = json.loads(row[5])
                
                for i in Tilde.hierarchy:
                    if not 'has_summary_contrb' in i: continue # additional control on skipping to avoid redundancy
                        
                    if i['cid'] > 2000:
                        # apps
                        summary.append( {  'category': i['category'], 'sort': i['sort'], 'content': [ Tilde.wrap_cell(i, data_obj) ]  } )
                        
                    else:
                        # classification
                        content = []
                        if '#' in i['source']:
                            n=0
                            while 1:
                                try: content.append(data_obj['info'][ i['source'].replace('#', str(n)) ])
                                except KeyError: break
                                n+=1
                        else:
                            content.append( Tilde.wrap_cell(i, data_obj) )
                        if len(content):
                            catname = str2html(i['html']) if 'html' in i else i['category'][0].upper() + i['category'][1:]
                            summary.append( {'category': catname, 'sort': i['sort'], 'content': content} )
                            
                summary.sort(key=lambda x: x['sort'])
                
                phon_flag = False
                if len(row[2]) > 10: phon_flag = True # avoids json.loads

                e_flag = {'dos': True, 'bands': True}                    
                if '"dos": {}' in row[3] and '"projected": []' in row[3]: e_flag['dos'] = False # avoids json.loads
                if '"bands": {}' in row[3]: e_flag['bands'] = False
                    
                data = json.dumps({
                'phonons': phon_flag,
                'electrons': e_flag,
                'info': row[4], # raw info object
                'summary': summary # refined object
                })
        return (data, error)
        
    @staticmethod
    def optstory(userobj, session_id):
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT info FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])        
        
        row = cursor.fetchone()
        if row is None: return (data, 'No objects found!')
        
        info = json.loads(row[0])
        
        if not info['tresholds']: return (data, 'No convergence data found!')
        
        data = json.dumps(eplotter( task='optstory', data=info['tresholds'] ))
        
        return (data, error)
        
    @staticmethod
    def estory(userobj, session_id):
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT info FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])        
        
        row = cursor.fetchone()
        if row is None: return (data, 'No objects found!')
        
        info = json.loads(row[0])
        
        if not info['convergence']: return (data, 'No convergence data found!')
        
        data = json.dumps(eplotter( task='convergence', data=info['convergence'] ))
        
        return (data, error)

    @staticmethod
    def settings(userobj, session_id):
        data, error = None, None

        global Tilde, Users, Tilde_tags

        # *server-side* settings
        if userobj['area'] == 'scan':
            if settings['demo_regime']: return (data, 'Action not allowed!')
            
            for i in ['quick_regime', 'skip_unfinished', 'skip_if_path']:
                settings[i] = userobj['settings'][i]

            if not write_settings(settings): return (data, 'I/O error: failed to save settings in ' + DATA_DIR)

            Tilde.reload( db_conn=Repo_pool[ Users[session_id].cur_db ], settings=settings )
        
        # *server-side* settings    
        elif userobj['area'] == 'path':
            if settings['demo_regime']: return (data, 'Action not allowed!')
            
            if not len(userobj['path']): return (data, 'Please, input a valid working path.')
            if not os.path.exists(userobj['path']) or not os.access(userobj['path'], os.R_OK): return (data, 'Cannot read this path, may be invalid or not enough privileges?')
            if 'win' in sys.platform and userobj['path'].startswith('/'): return (data, 'Working path should not start with slash.')
            if 'linux' in sys.platform and not userobj['path'].startswith('/'): return (data, 'Working path should start with slash.')

            userobj['path'] = os.path.abspath(userobj['path'])
            if not userobj['path'].endswith(os.sep): userobj['path'] += os.sep
            settings['local_dir'] = userobj['path']
            data = userobj['path']
            
            if not write_settings(settings): return (data, 'I/O error: failed to save settings in ' + DATA_DIR)
        
        # *server-side* settings
        elif userobj['area'] == 'general':
            if settings['demo_regime']: return (data, 'Action not allowed!')

            try:
                userobj['settings']['webport'] = int(userobj['settings']['webport'])
                userobj['settings']['db']['port'] = int(userobj['settings']['db']['port'])
            except: return (data, 'Port is not correct!')
            
            new_settings = {}
            new_settings.update(settings)
            for i in ['webport', 'title', 'demo_regime', 'debug_regime', 'db']:
                new_settings[i] = userobj['settings'][i]
            
            if not write_settings(new_settings): return (data, 'I/O error: failed to save settings in ' + DATA_DIR)
        
        # *server + client-side* settings
        elif userobj['area'] == 'cols':
            for i in ['cols', 'colnum', 'objects_expand']:
                Users[session_id].usettings[i] = userobj['settings'][i]

        # *server + client-side* settings
        elif userobj['area'] == 'switching':
            if settings['db']['type'] != 'sqlite': return (data, 'Database ' + userobj['switching'] + ' was left!')
            if not userobj['switching'] in Repo_pool or Users[session_id].cur_db == userobj['switching']: return (data, 'Database ' + userobj['switching'] + ' was left!')
            
            Users[session_id].cur_db = userobj['switching']
            Tilde.reload( db_conn=Repo_pool[ Users[session_id].cur_db ] )
            if Users[session_id].cur_db in Tilde_tags:
                # force update tags in memory
                Tilde_tags[ Users[session_id].cur_db ] = DataMap( Users[session_id].cur_db )
                if Tilde_tags[ Users[session_id].cur_db ].error:
                    error = 'DataMap creation error: ' + Tilde_tags[ Users[session_id].cur_db ].error
            logging.debug('Switched to ' + userobj['switching'])
        
        else: error = 'Unknown settings context area!'

        if not data: data = 1
        return (data, error)
    
    @staticmethod    
    def try_pgconn(userobj, session_id):
        data, error = None, None
        if settings['demo_regime']: return (data, 'Action not allowed!')
        
        try: import psycopg2
        except ImportError:
            try: import pg8000
            except ImportError: return (data, 'Current python environment does not support Postgres!')
        
        creds = {'db': userobj['creds']}

        db = connect_database(creds, None)
        if not db: return (data, 'Connection to Postgres failed!')
        incompatible = check_db_version(db)
        if incompatible: return (data, 'Sorry, this DB is incompatible!')
        
        data = 1
        return (data, error)

    @staticmethod
    def check_export(userobj, session_id):
        data, error = None, None
        # this is doubling of DataExportHandler
        # in order to give a message if a data cannot be exported
        # could it be done within the sole DataExportHandler?
        if not 'id' in userobj or not 'db' in userobj or not userobj['id'] or not userobj['db']: return (data, 'Action invalid!')
        if len(userobj['id']) != 56 or not userobj['db'] in Repo_pool: return (data, 'Action invalid!')
        cursor = Repo_pool[ userobj['db'] ].cursor()
        sql = 'SELECT info FROM results WHERE checksum = %s' % settings['ph']
        cursor.execute( sql, (userobj['id'],) )
        row = cursor.fetchone()
        if not row: return (data, 'Object not found!')
        else:
            info = json.loads(row[0])
            if os.path.exists(info['location']):
                data = 1
                return (data, error)
            else: return (data, 'Sorry, i have no access to source file anymore!')

    @staticmethod
    def db_create(userobj, session_id):
        data, error = None, None
        if settings['demo_regime'] or settings['db']['type'] != 'sqlite': return (data, 'Action not allowed!')
        
        global Repo_pool
        
        if len(Repo_pool) == MAX_CONCURRENT_DBS: return (data, 'Due to memory limits cannot manage more than %s databases!' % MAX_CONCURRENT_DBS)
        
        error = write_db(userobj['newname'])
        userobj['newname'] += '.db'
        
        if not error:
            try: import sqlite3
            except ImportError: from pysqlite2 import dbapi2 as sqlite3
            
            Repo_pool[userobj['newname']] = sqlite3.connect( os.path.abspath(  DATA_DIR + os.sep + userobj['newname']  ) )
            Repo_pool[userobj['newname']].row_factory = sqlite3.Row
            Repo_pool[userobj['newname']].text_factory = str
            data, error = 1, None
        
        return (data, error)
    
    @staticmethod
    def db_copy(userobj, session_id):
        data, error = None, None
        if settings['demo_regime'] or settings['db']['type'] != 'sqlite': return (data, 'Action not allowed!')
        if not 'tocopy' in userobj or not 'dest' in userobj or not userobj['tocopy'] or not userobj['dest']: return (data, 'Action invalid!')
        if not userobj['dest'] in Repo_pool: return (data, 'Copying destination invalid!')

        global Tilde
        data_clause = '","'.join(  userobj['tocopy']  )
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        try: cursor.execute( 'SELECT id, checksum, structures, energy, phonons, electrons, info, apps FROM results WHERE checksum IN ("%s")' % data_clause )
        except: error = 'DB error: ' + "%s" % sys.exc_info()[1]
        else:
            # TODO: THIS IS I/O DANGEROUS
            Tilde.reload( db_conn=Repo_pool[ userobj['dest'] ] )

            for r in cursor.fetchall():
                calc = Tilde.restore(r, db_transfer_mode=True)
                checksum, error = Tilde.save(calc, db_transfer_mode=True)
                
            Tilde.reload( db_conn=Repo_pool[ Users[session_id].cur_db ] )
        data = 1
        return (data, error)
    
    # TODO: delegate content of these four methods to plotter!
    
    @staticmethod
    def ph_dos(userobj, session_id): # currently supported for: CRYSTAL, VASP
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT structures, phonons FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])
        
        row = cursor.fetchone()
        if row is None: return (data, 'No information found!')
        if row[1] is None: return (data, 'No phonons for this object!')

        s = json.loads(row[0])
        p = json.loads(row[1])

        # gamma-projected eigenvalues and gamma-projected atomic impacts from eigenvectors
        eigenvalues, impacts = [], []
        for set in p:
            if hasattr(set, 'ph_k_degeneracy'): degeneracy_repeat = set['ph_k_degeneracy']
            else: degeneracy_repeat = 1

            # gamma-projected eigenvalues
            for i in set['freqs']:
                for d in range(0, degeneracy_repeat): eigenvalues.append( i )

            # gamma-projected impacts from eigenvectors
            for item in set['ph_eigvecs']:
                c = []
                for f in range(len(item)/3):
                    c.append( math.sqrt( float(item[f*3])**2 + float(item[f*3 + 1])**2 + float(item[f*3 + 2])**2 ) )
                sm = sum(c)
                if sm == 0: sm=1 # e.g. when eigenvectors are unknown
                h = []
                for j in c: h.append( j/sm )
                for d in range(0, degeneracy_repeat): impacts.append(h)

        # sorting with order preserving
        ordered = zip(eigenvalues, impacts)
        ordered = sorted(ordered, key=lambda x: x[0])
        eigenvalues, impacts = zip(*ordered)

        #sigma = 8
        sigma = 10
        val_min = 0
        val_max = eigenvalues[-1] + 25
        pitch = 3

        return (json.dumps(bdplotter(task = 'dos', eigenvalues=eigenvalues, impacts=impacts, atomtypes=s[-1]['symbols'], sigma=sigma, omega_min=val_min, omega_max=val_max, omega_pitch=pitch)), error)
        
    @staticmethod
    def ph_bands(userobj, session_id): # currently supported for: CRYSTAL, "VASP"
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT structures, phonons FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])
        
        row = cursor.fetchone()
        
        if row is None: return (data, 'No information found!')
        if row[1] is None: return (data, 'No phonons for this object!')

        s = json.loads(row[0])
        p = json.loads(row[1])

        values = {}
        for set in p: values[ set['bzpoint'] ] = set['freqs']

        return (json.dumps(bdplotter( task = 'bands', values = values, xyz_matrix = s[-1]['cell'] )), error)

    @staticmethod
    def e_dos(userobj, session_id): # currently supported for: EXCITING, VASP
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT structures, electrons FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])
        
        row = cursor.fetchone()
        
        if row is None: return (data, 'No information found!')            
            
        s = json.loads(row[0])
        e = json.loads(row[1])

        if not len(e['dos']) and not len(e['projected']): return (data, 'Electron information is not full: plotting impossible!') # and (not 'e_proj_eigvals' in e or not 'impacts' in e):

        val_min = E_LOWER_DEFAULT if not 'min' in userobj else userobj['min']
        val_max = E_UPPER_DEFAULT if not 'max' in userobj else userobj['max']
        pitch=(val_max - val_min) / 200
        
        '''if 'e_proj_eigvals' in e and 'impacts' in e:
            data = json.dumps(bdplotter(task = 'dos', eigenvalues=e['e_proj_eigvals'], impacts=e['impacts'], atomtypes=s[-1]['symbols'], sigma=sigma, omega_min=val_min, omega_max=val_max, omega_pitch=pitch))'''
        
        # EXCITING EIGVAL.OUT
        if len(e['projected']):
            sigma=0.1 # tested on comparison with EXCITING XMLs
            return (json.dumps(bdplotter(task = 'dos', eigenvalues = e['projected'], sigma=sigma, omega_min=val_min, omega_max=val_max, omega_pitch=pitch)), error)
            
        # VASP vasprun.xml
        # EXCITING dos.xml        
        else:
            # reduce values
            keep = []
            for n, i in enumerate(e['dos']['x']):
                if val_min <= i <= val_max:
                    keep.append(n)
            for k in e['dos'].keys():
                e['dos'][k] = e['dos'][k][keep[0] : keep[-1]+1]        
            
            return (json.dumps(bdplotter(task = 'dos', precomputed = e['dos'])), error)

    @staticmethod
    def e_bands(userobj, session_id): # currently supported for: EXCITING
        data, error = None, None
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        sql = 'SELECT structures, electrons FROM results WHERE checksum = %s' % settings['ph']
        try: cursor.execute( sql, (userobj['datahash'], ) )
        except: return (data, 'DB error: ' + "%s" % sys.exc_info()[1])
        
        row = cursor.fetchone()
        if row is None: return (data, 'No information found!')
        
        s = json.loads(row[0])
        e = json.loads(row[1])

        if not len(e['bands']): return (data, 'Band structure is missing!')

        val_min = E_LOWER_DEFAULT if not 'min' in userobj else userobj['min']
        val_max = E_UPPER_DEFAULT if not 'max' in userobj else userobj['max']
            
        e['bands']['stripes'] = ifilter(lambda value: val_min < sum(value)/len(value) < val_max, e['bands']['stripes'])
        
        return (json.dumps(bdplotter( task = 'bands', precomputed = e['bands'] )), error)
        
    @staticmethod
    def delete(userobj, session_id):
        data, error = None, None
        if settings['demo_regime']: return (data, 'Action not allowed!')
        
        global Tilde_tags, Repo_pool
        
        cursor = Repo_pool[ Users[session_id].cur_db ].cursor()
        
        data_clause = userobj['hashes']
        data_clause = map(lambda x: x.encode('utf-8'), data_clause) # for postgres
        if len(data_clause) == 1: data_clause.append('dummy_entity_to_prevent_an_error_with_one_value') # for postgres
        
        try:
            if settings['db']['type'] == 'sqlite':
                data_clause = '","'.join(data_clause)
                cursor.execute( 'DELETE FROM results WHERE checksum IN ("%s")' % data_clause)
                cursor.execute( 'DELETE FROM tags WHERE checksum IN ("%s")' % data_clause)
            elif settings['db']['type'] == 'postgres':
                cursor.execute( 'DELETE FROM results WHERE checksum IN %s' % (tuple(data_clause),))
                cursor.execute( 'DELETE FROM tags WHERE checksum IN %s' % (tuple(data_clause),))
            Repo_pool[ Users[session_id].cur_db ].commit()
        except:
            Repo_pool[ Users[session_id].cur_db ].commit() # Postgres: prevent transaction aborting...
            return (data, 'DB error: ' + "%s" % sys.exc_info()[1])
        else:
            # force update tags in memory
            Tilde_tags[ Users[session_id].cur_db ] = DataMap( Users[session_id].cur_db )
            if Tilde_tags[ Users[session_id].cur_db ].error:
                error = 'DataMap creation error: ' + Tilde_tags[ Users[session_id].cur_db ].error
            data = 1
            return (data, error)

    @staticmethod
    def clean(userobj, session_id):
        data, error = None, None
        if settings['demo_regime'] or settings['db']['type'] != 'sqlite': return (data, 'Action not allowed!')
        if userobj['db'] == Users[session_id].cur_db: return (data, 'Deletion of current database is prohibited!')
        global Tilde_tags, Repo_pool
        try: Repo_pool[ userobj['db'] ].close()
        except:
            return (data, 'Cannot close database: ' + "%s" % sys.exc_info()[1])
        else:
            del Repo_pool[ userobj['db'] ]
            if userobj['db'] in Tilde_tags: del Tilde_tags[ userobj['db'] ]
            try: os.remove(os.path.abspath(  DATA_DIR + os.sep + userobj['db']  ))
            except:
                return (data, 'Cannot delete database: ' + "%s" % sys.exc_info()[1])

            if userobj['db'] == settings['default_sqlite_db']:
                settings['default_sqlite_db'] = Users[session_id].cur_db
                if not write_settings(settings): return (data, 'I/O error: failed to save settings in ' + DATA_DIR)

            data = 1
            return (data, error)

    @staticmethod
    def restart(userobj=None, session_id=None):
        data, error = None, None
        
        if settings['demo_regime']: return (data, 'Action not allowed!')
        
        # this is borrowed from tornado autoreload
        if sys.platform == 'win32':
            # os.execv is broken on Windows and can't properly parse command line
            # arguments and executable name if they contain whitespaces. subprocess
            # fixes that behavior.
            import subprocess
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        else:
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except OSError:
                # Mac OS X versions prior to 10.6 do not support execv in
                # a process that contains multiple threads.  Instead of
                # re-executing in the current process, start a new one
                # and cause the current process to exit.  This isn't
                # ideal since the new process is detached from the parent
                # terminal and thus cannot easily be killed with ctrl-C,
                # but it's better than not being able to autoreload at
                # all.
                # Unfortunately the errno returned in this case does not
                # appear to be consistent, so we can't easily check for
                # this error specifically.
                os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable] + sys.argv)
                sys.exit(0)

    @staticmethod
    def terminate(userobj=None, session_id=None):
        data, error = None, None
        if settings['demo_regime']: return (data, 'Action not allowed!')
        sys.exit(0)


class DuplexConnection(SockJSConnection):
    def on_open(self, info):
        global Users
        Users[ self.session.session_id ] = User()

    def on_message(self, message):
        userobj, output = {}, {'act': '', 'req': '', 'error': '', 'data': ''}
        output['act'], output['req'] = message.split(DELIM)

        if len(output['req']): userobj = json.loads(output['req'])

        if not hasattr(Request_Handler, output['act']):
            output['error'] = 'No server handler for action ' + output['act']
            self._send(output)
        else:

            # multiple answer
            if output['act'] == 'report' and userobj['transport'] == 'local' and userobj['directory'] > 0:                    
                discover = settings['local_dir'] + userobj['path']
                recursive = True if userobj['directory'] == 2 else False
                if not os.access(discover, os.R_OK):
                    output['error'] = 'A requested path is not readable (not enough privileges?)'
                    self._send(output)
                else:
                    tasks = Tilde.savvyize(discover, recursive)
                    if not tasks: self._send(output)
                    for n, task in enumerate(tasks, start=1):
                        checksum, error = Request_Handler.report({'path': task[len(settings['local_dir']):], 'transport': 'local'}, session_id=self.session.session_id)
                        finished = 1 if n == len(tasks) else 0
                        output['data'] = json.dumps({'filename': os.path.basename(task), 'error': error, 'checksum': checksum, 'finished': finished})
                        self._send(output)

            # single answer
            else:
                output['data'], output['error'] = getattr(Request_Handler, output['act'])( userobj, session_id=self.session.session_id )
                self._send(output)

    def on_close(self):
        del Users[ self.session.session_id ]

    def _send(self, output):
        if output['error'] is None and output['data'] is None: output['error'] = output['act'] + " handler has returned an empty result!"
        if output['data'] is None: output['data'] = ""
        if output['error'] is None: output['error'] = ""
        answer = "%s%s%s%s%s%s%s" % (output['act'], DELIM, output['req'], DELIM, output['error'], DELIM, output['data'])
        self.send( answer )

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(os.path.realpath(os.path.dirname(os.path.abspath(__file__))) + "/../htdocs/frontend.html")

'''class CIFDownloadHandler(tornado.web.RequestHandler):
    def get(self, req_str):
        if not '/' in req_str: raise tornado.web.HTTPError(404)
        items = req_str.split('/')
        if len(items) != 2: raise tornado.web.HTTPError(404)
        db, hash = items
        if len(hash) != 56 or not db in Repo_pool: raise tornado.web.HTTPError(404)

        try:
            cursor = Repo_pool[ db ].cursor()
            cursor.execute( 'SELECT structures FROM results WHERE checksum = ?', (hash,) )
            row = cursor.fetchone()
            if not row: raise tornado.web.HTTPError(404)
        except:
            raise tornado.web.HTTPError(404)
        else:
            struc = json.loads(row['structures'])
            filename = Tilde.formula( [i[0] for i in struc[-1]['atoms']] )
            content = struc[-1]['orig_cif']
            self.set_header('Content-type', 'application/download;')
            self.set_header('Content-disposition', 'attachment; filename="' + filename + '.cif')
            self.write(content)'''
            
class JSON3DDownloadHandler(tornado.web.RequestHandler):
    def get(self, req_str):
        if not '/' in req_str: raise tornado.web.HTTPError(404)
        items = req_str.split('/')
        if len(items) < 2 or len(items) > 3: raise tornado.web.HTTPError(404)
        
        db, hash, pos = items[0], items[1], -1
        if len(items) > 2:
            try: pos = int(items[2])
            except ValueError: raise tornado.web.HTTPError(404)
        
        if len(hash) != 56 or not db in Repo_pool: raise tornado.web.HTTPError(404)
        
        try:
            cursor = Repo_pool[ db ].cursor()
            sql = 'SELECT structures, info, apps FROM results WHERE checksum = %s' % settings['ph']
            cursor.execute( sql, (hash,) )
            row = cursor.fetchone()
            if not row: raise tornado.web.HTTPError(404)
        except:
            raise tornado.web.HTTPError(404)
        else:
            try: ase_obj = dict2ase(json.loads(row[0])[pos])
            except IndexError: raise tornado.web.HTTPError(404)

            info = json.loads(row[1])
            #symmetry = info['ng']
            nstruc = len(info['tresholds']) - 1 # from zero-th

            overlayed_apps = {}
            if pos in [-1, nstruc]:
                overlay_data = json.loads(row[2])
                for appkey in Tilde.Apps.keys():
                    if Tilde.Apps[appkey]['on3d'] and appkey in overlay_data:
                        overlayed_apps[appkey] = Tilde.Apps[appkey]['appcaption']
                   
            #if ase_obj.periodicity: ase_obj = crystal(ase_obj, spacegroup=symmetry, ondublicates='keep') # Warning! Symmetry may be determined for redefined structure! Needs testing : TODO
            
            if len(ase_obj) > 1250: raise tornado.web.HTTPError(404) # Sorry, this structure is too large for me to display!
            
            #ase_obj.center() # NB: check for slabs!            
            #mass_center = ase_obj.get_center_of_mass()
            #for i in range(len(mass_center)):
            #    if mass_center[i] == 0: mass_center[i] = 1
            #mass_center_octant = [ mass_center[0]/abs(mass_center[0]), mass_center[1]/abs(mass_center[1]), mass_center[2]/abs(mass_center[2]) ]
            
            # player.html atoms JSON format
            atoms = []
            for n, i in enumerate(ase_obj):
                if i.symbol == 'X': radius, rgb = 0.66, '0xffff00'
                else:
                    rgblist = (jmol_colors[ chemical_symbols.index( i.symbol ) ] * 255).tolist()
                    rgb = '0x%02x%02x%02x' % ( rgblist[0], rgblist[1], rgblist[2] )
                    if rgb == '0xffffff': rgb = '0xcccccc'
                    radius = covalent_radii[ chemical_symbols.index( i.symbol ) ]
                oa = {'t':i.symbol}
                for app in overlayed_apps.keys():
                    try: oa[app] = str( overlay_data[app][str(n+1)] ) # atomic index is counted from zero!
                    except KeyError: pass
                atoms.append( {'c':rgb, 'r': "%2.3f" % radius, 'x': "%2.3f" % i.position[0], 'y': "%2.3f" % i.position[1], 'z': "%2.3f" % i.position[2], 'o': oa} )

            # player.html cell depiction
            cell_points = []
            if ase_obj.get_pbc().all():
                for i in ase_obj.cell.tolist():
                    #cell_points.append([i[0]*mass_center_octant[0], i[1]*mass_center_octant[1], i[2]*mass_center_octant[2]])
                    cell_points.append(i)

            # player.html info area
            cellpar = cell_to_cellpar( ase_obj.cell ).tolist()
            descr = {'a': "%2.3f" % cellpar[0], 'b': "%2.3f" % cellpar[1], 'c': "%2.3f" % cellpar[2], 'alpha': "%2.3f" % cellpar[3], 'beta': "%2.3f" % cellpar[4], 'gamma': "%2.3f" % cellpar[5]}
            
            content = json.dumps({'atoms': atoms, 'cell': cell_points, 'descr': descr, 'overlayed': overlayed_apps})
            self.set_header('Content-type', 'application/json')
            self.write(content)

class DataExportHandler(tornado.web.RequestHandler):
    def get(self, req_str):
        if not settings['exportability']: raise tornado.web.HTTPError(404)
        if not '/' in req_str: raise tornado.web.HTTPError(404)
        items = req_str.split('/')
        if len(items) != 2: raise tornado.web.HTTPError(404)
        db, hash = items
        if len(hash) != 56 or not db in Repo_pool: raise tornado.web.HTTPError(404)

        try:
            cursor = Repo_pool[ db ].cursor()
            sql = 'SELECT info FROM results WHERE checksum = %s' % settings['ph']
            cursor.execute( sql, (hash,) )
            row = cursor.fetchone()
            if not row: raise tornado.web.HTTPError(404)
        except:
            raise tornado.web.HTTPError(404)
        else:
            info = json.loads(row[0])
            if os.path.exists(info['location']):
                file = open(info['location']).read()
                self.set_header('Content-type', 'application/download;')
                self.set_header('Content-disposition', 'attachment; filename="' + os.path.basename(info['location']))
                self.write(file)
            else:
                raise tornado.web.HTTPError(404)

if __name__ == "__main__":
    
    # check new version
    if not settings['demo_regime']:
        updatemsg = ''
        import urllib2
        try:
            updatemsg = urllib2.urlopen(settings['update_server'], timeout=2.5).read()
        except urllib2.URLError:
            updatemsg = 'Could not check new version: update server is down.'
        else:
            try: int(updatemsg.split('.')[0])
            except: updatemsg = 'Could not check new version: communication with update server failed.'
            else:
                if updatemsg.strip() == API.version: updatemsg = "Current version is up-to-date.\n"
                else: updatemsg = '\n\tAttention!\n\tWarning!\n\tYour program version (%s) is not actual!\n\tActual version is %s.\n\tUpdating is highly recommended!\n' % (API.version, updatemsg.strip())
        print updatemsg

    loglevel = logging.DEBUG if settings['debug_regime'] else logging.ERROR
    logging.getLogger().setLevel(loglevel)
    
    if settings['db']['type'] == 'sqlite':
        for r in repositories:
            Repo_pool[r] = connect_database(settings, r) # NB. at this stage DB connection is already checked
            
            # check DB_SCHEMA_VERSION
            incompatible = check_db_version(Repo_pool[r])
            if incompatible:
                del Repo_pool[r]
                print 'Sorry, database ' + DATA_DIR + os.sep + r + ' is incompatible.'
                continue
            
            Tilde_tags[r] = DataMap( r )
            if Tilde_tags[r].error: sys.exit('DataMap creation error: ' + Tilde_tags[r].error)
        
        if not settings['default_sqlite_db'] in Repo_pool: sys.exit("Fatal error!\nDefault database " + DATA_DIR + os.sep + settings['default_sqlite_db'] + " is incompatible, please, remove it to proceed.")
        default_conn = Repo_pool[settings['default_sqlite_db']]
    
    elif settings['db']['type'] == 'postgres':
        Repo_pool[DEFAULT_DBTITLE] = connect_database(settings, None) # NB. at this stage DB connection is already checked
        
        # check DB_SCHEMA_VERSION
        incompatible = check_db_version(Repo_pool[DEFAULT_DBTITLE])
        if incompatible:
            sys.exit('Fatal error!\nCurrent DB is incompatible!')
        
        Tilde_tags[DEFAULT_DBTITLE] = DataMap( DEFAULT_DBTITLE )
        if Tilde_tags[DEFAULT_DBTITLE].error: sys.exit('DataMap creation error: ' + Tilde_tags[DEFAULT_DBTITLE].error)
        default_conn = Repo_pool[DEFAULT_DBTITLE]
    
    Tilde.reload( db_conn = default_conn, settings = settings )

    DuplexRouter = SockJSRouter(DuplexConnection, '/duplex')
    config = {"debug": settings['debug_regime']}
    try:
        application = tornado.web.Application(
            [(r"/", IndexHandler),
            (r"/static/(.*)", tornado.web.StaticFileHandler),
            #(r"/cif/(.*)", CIFDownloadHandler),
            (r"/json3d/(.*)", JSON3DDownloadHandler),
            (r"/export/(.*)", DataExportHandler),
            #(r"/VERSION", UpdateServiceHandler)
            ] + DuplexRouter.urls,
            static_path = os.path.realpath(os.path.dirname(os.path.abspath(__file__))) + '/../htdocs',
            **config)
        application.listen(settings['webport'], address='0.0.0.0', no_keep_alive=True)
    except:
        errmsg = "Error while starting new Tilde daemon: " + "%s" % sys.exc_info()[1]
        logging.critical( errmsg )
        print errmsg
    else:
        if 'linux' in sys.platform:
            try: address = socket.gethostname() # socket.gethostbyname(socket.gethostname())
            except: address = 'localhost'
        else: address = 'localhost'
        address = address + ('' if int(settings['webport']) == 80 else ':%s' % settings['webport'])

        print "Welcome to " + CURRENT_TITLE + " GUI (" + settings['db']['type'] + " backend)\nPlease, open http://" + address + "/ in your browser\nTo terminate, hit Ctrl+C\n"

        try: tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt: sys.exit("\nBye-bye.")
