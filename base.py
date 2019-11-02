from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Engine = create_engine('postgresql://fatimakahbi:postgres@localhost:5432/store')
Session = sessionmaker(bind=Engine)
Base = declarative_base()