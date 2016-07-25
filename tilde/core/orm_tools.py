
# ORM tools
# Idea by Fawzi Mohamed
# Author: Evgeny Blokhin

import bcrypt


class UniqueMixin(object):
    @classmethod
    def unique_filter(cls, query, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def as_unique(cls, session, *arg, **kw):
        return _unique(session, cls, cls.unique_filter, cls, arg, kw)

    @classmethod
    def as_unique_todict(cls, session, *arg, **kw):
        return _unique_todict(session, cls, cls.unique_filter, arg, kw)

def _unique(session, cls, queryfunc, constructor, arg, kw):
    '''
    https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/UniqueObject
    Checks if ORM entity exists according to criteria,
    if yes, returns it, if no, creates
    '''
    with session.no_autoflush:
        q = session.query(cls)
        q = queryfunc(q, *arg, **kw)
        obj = q.first()
        if not obj:
            obj = constructor(*arg, **kw)
            session.add(obj)
    return obj

def _unique_todict(session, cls, queryfunc, arg, kw):
    '''
    Checks if ORM entity exists according to criteria,
    if yes, returns it, if no, returns dict representation
    (required for further DB replication and syncing)
    '''
    q = session.query(cls)
    q = queryfunc(q, *arg, **kw)
    obj = q.first()
    if not obj:
        obj = kw
        obj['__cls__'] = cls.__mapper__.class_.__name__
    return obj

def get_or_create(cls, session, defaults=None, **kwds):
    result = session.query(cls).filter_by(**kwds).first()
    if result:
        return result, False
    new_vals = defaults
    if defaults is None:
        new_vals = {}
    new_vals.update(kwds)
    result = cls(**new_vals)
    session.add(result)
    session.flush()
    return result, True

def correct_topics(session, model, calc_id, cid, new_topics, mode, topics_hierarchy):
    assert model.Calculation.__tablename__

    found_entity = None
    for e in topics_hierarchy:
        if e['cid'] == cid:
            found_entity = e
            break
    assert found_entity, "Wrong topic identifier!"

    if isinstance(calc_id, str):
         calc_id = [calc_id]
    assert isinstance(calc_id, list)
    if isinstance(new_topics, str):
         new_topics = [new_topics]
    assert isinstance(new_topics, list)

    if mode == 'REPLACE':
        _replace_topics(session, model, calc_id, cid, new_topics)
    elif mode == 'APPEND':
        assert found_entity.get('multiple', False)
        _append_topics(session, model, calc_id, cid, new_topics)

def _replace_topics(session, model, calc_id, cid, new_topics):
    new_terms = []
    for new_topic in new_topics:
        new_term, created = model.get_or_create(model.Topic, session, cid=cid, topic=new_topic)
        new_terms.append(new_term)
    session.commit()

    for checksum in calc_id:
        for tid in session.query(model.tags.c.tid).join(model.Topic, model.tags.c.tid == model.Topic.tid).filter(model.Topic.cid == cid, model.tags.c.checksum == checksum).all():
             session.execute(model.delete(model.tags).where(model.and_(model.tags.c.checksum == checksum, model.tags.c.tid == tid[0])))
        session.commit()

        for new_term in new_terms:
            session.execute(model.insert(model.tags).values(checksum=checksum, tid=new_term.tid))
        session.commit()

def _append_topics(session, model, calc_id, cid, new_topics):
    new_terms = []
    for new_topic in new_topics:
        new_term, created = model.get_or_create(model.Topic, session, cid=cid, topic=new_topic)
        new_terms.append(new_term)
    session.commit()
    for new_term in new_terms:
        for checksum in calc_id: # .values([model.tag(checksum=checksum, tid=new_term.tid) for checksum in calc_id])
            try: session.execute(model.insert(model.tags).values(checksum=checksum, tid=new_term.tid))
            except model.IntegrityError:
                logger.critical("The pair (%s, %s) is already present in the tags table!" % (checksum, new_term.tid))
                session.rollback()
    session.commit()
