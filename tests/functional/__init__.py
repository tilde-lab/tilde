
# Common code for running functests
# Author: Evgeny Blokhin

import os, sys
import time
import logging
import random
import unittest

import pg8000

import set_path
import tilde.core.model
from tilde.core.api import API
from tilde.core.settings import settings, connect_database, DATA_DIR, EXAMPLE_DIR, TEST_DBS_FILE, TEST_DBS_REF_FILE


logger = logging.getLogger('functests')
logger.setLevel(logging.INFO)

DELETE_TEST_DB = False

class Setup_DB:
    def __init__(self, dbname='test'):
        self.dbname = '%s__%s_%s_db' % ( dbname, time.strftime("%m%d_%H%M%S"), "".join( random.choice("0123456789abcdef") for i in range(4) ) )
        self.session = None

        if not os.path.exists(TEST_DBS_REF_FILE):
            sys.stderr.write( '\nRef file with DB names not found, creating...\n' ) # fixme in a more elegant way
            with open(TEST_DBS_REF_FILE, "w") as refsave:
                refsave.write(self.dbname + "\n")
        else:
            test_dbs_ref = [line.strip() for line in open(TEST_DBS_REF_FILE, 'r')]
            for line in test_dbs_ref:
                if line.startswith(dbname): break
            else:
                with open(TEST_DBS_REF_FILE, "a") as refsave:
                    refsave.write(self.dbname + "\n")

class Setup_FileDB(Setup_DB):
    def create(self):
        self.dbtype = settings['db']['engine'] = 'sqlite'
        self.session = connect_database(settings, named=self.dbname)()
        logger.warning( '%s created' % self.dbname )

        if not DELETE_TEST_DB:
            sys.stderr.write( '\n%s created\n' % self.dbname ) # fixme in a more elegant way
            with open(TEST_DBS_FILE, "a") as tmpsave:
                tmpsave.write(self.dbname + "\n")

    def __del__(self):
        if self.session:
            self.session.close()
        if os.path.exists(os.path.join(DATA_DIR, self.dbname)) and DELETE_TEST_DB:
            os.unlink(os.path.join(DATA_DIR, self.dbname))
            logger.warning( "%s purged" % self.dbname )

        #if not DELETE_TEST_DB: logger.warning( "%s is kept" % self.dbname )

class Setup_ServerDB(Setup_DB):
    def create(self):
        self.dbtype = settings['db']['engine'] = 'postgresql'
        settings['db']['dbname'] = 'postgres' # we can only be sure this DB exists!
        try: db = pg8000.connect(host = settings['db']['host'], port = int(settings['db']['port']), user = settings['db']['user'], password = settings['db']['password'], database = settings['db']['dbname'])
        except: sys.exit('Cannot connect for test DB creation with these credentials: ' + str(settings['db']))
        db.autocommit = True
        cursor = db.cursor()
        cursor.execute("CREATE DATABASE %s;" % self.dbname)
        db.commit()
        cursor.close()
        db.close()
        logger.warning( '%s created' % self.dbname )

        if not DELETE_TEST_DB:
            sys.stderr.write( '\n%s created\n' % self.dbname ) # fixme in a more elegant way
            with open(TEST_DBS_FILE, "a") as tmpsave:
                tmpsave.write(self.dbname + "\n")

        settings['db']['dbname'] = self.dbname
        self.session = connect_database(settings, no_pooling=True)()

    def __del__(self):
        if self.session:
            self.session.close()

        if not DELETE_TEST_DB:
            #logger.warning( "%s is kept" % self.dbname )
            return

        if not self.dbname.startswith("test_"): sys.exit('Not allowed.')

        settings['db']['dbname'] = 'postgres'
        try: db = pg8000.connect(host = settings['db']['host'], port = int(settings['db']['port']), user = settings['db']['user'], password = settings['db']['password'], database = settings['db']['dbname'])
        except: sys.exit('Cannot connect for test DB cleaning with these credentials: ' + str(settings['db']))
        db.autocommit = True
        cursor = db.cursor()
        cursor.execute("DROP DATABASE %s;" % self.dbname) # Warning, additional caution is required here!
        db.commit()
        cursor.close()
        db.close()
        logger.warning( "%s purged" % self.dbname )

class TestLayerDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls, dbname='test', preferred_engine=None):
        cls.starttime = time.time()

        if preferred_engine == 'postgresql':
            dbcls = Setup_ServerDB(dbname=dbname)
        elif preferred_engine == 'sqlite':
            dbcls = Setup_FileDB(dbname=dbname)
        else:
            if settings['db']['engine'] == 'postgresql':
                dbcls = Setup_ServerDB(dbname=dbname)
            else:
                dbcls = Setup_FileDB(dbname=dbname)

        cls.db = dbcls
        cls.db.create()
        cls.engine = API()

        expath = getattr(cls, '__test_calcs_dir__', os.path.join(EXAMPLE_DIR, 'VASP'))
        logger.info("Path to consider: %s" % expath)

        for task in cls.engine.savvyize(expath, recursive=True):
            filename = os.path.basename(task)

            for calc, error in cls.engine.parse(task):
                if error:
                    logger.info("%s %s" % (filename, error))
                    continue

                calc, error = cls.engine.classify(calc)
                if error:
                    logger.info("%s %s" % (filename, error))
                    continue

                checksum, error = cls.engine.save(calc, cls.db.session)
                if error:
                    logger.info("%s %s" % (filename, error))
                    continue

                logger.info(task + " successfully added")

        cls.perf = time.time() - cls.starttime
        logger.info("test repository built in %1.2f sec" % cls.perf)

    @classmethod
    def tearDownClass(cls):
        failed = getattr(cls, 'failed', False)
        if not failed:
            del cls.db
