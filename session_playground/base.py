from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


my_conn_string = 'postgresql://fatimakahbi:postgres@localhost:5432/playground'

Engine = create_engine(my_conn_string)
Session = sessionmaker(bind=Engine)
Base = declarative_base()

