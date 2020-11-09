from sqlalchemy import create_engine, event, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool
import contextlib
from functools import wraps


my_conn_string = 'postgresql://fatimakahbi:postgres@localhost:5432/store'
# conn_string = 'postgresql://{}:{}@{}:{}/store'\
#     .format(os.environ["USER"],
#             os.environ["PASSWORD"],
#             os.environ["HOST"],
#             os.environ["PORT"])
Engine = create_engine(my_conn_string)
# Session = sessionmaker(bind=Engine)
Base = declarative_base()


Session = scoped_session(
    sessionmaker(
        autocommit=False, autoflush=False, bind=Engine, expire_on_commit=False
    )
)


def check_object_status(obj):
    insp = inspect(obj)
    if insp.transient:
        print('transient')
    elif insp.pending:
        print('pending')
    elif insp.persistent:
        print('persistent')
    elif insp.deleted:
        print('deleted')
    else:
        assert(insp.detached)
        print('detached')


def check_session(session):
    if session.dirty:
        print("DIRTY -- objects to be updated in db")
    elif session.new:
        print("NEW -- new objects to add to db")
    elif session.deleted:
        print("DELETED -- objects to be deleted as from db")
    else:
        print("CLEAN -- clean session")


@contextlib.contextmanager
def create_session():
    """
    Contextmanager that will create and teardown a session.
    """
    session = Session()
    # strong_reference_session(session)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def provide_session(func):
    """
    Function decorator that provides a session if it isn't provided.
    If you want to reuse a session or run the function as part of a
    database transaction, you pass it to the function, if not this wrapper
    will create one and close it for you.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        arg_session = "session"

        func_params = func.__code__.co_varnames
        session_in_args = arg_session in func_params and \
            func_params.index(arg_session) < len(args)
        session_in_kwargs = arg_session in kwargs

        if session_in_kwargs or session_in_args:
            return func(*args, **kwargs)
        else:
            with create_session() as session:
                kwargs[arg_session] = session
                return func(*args, **kwargs)

    return wrapper
# all code from Incubator-Airflow project
