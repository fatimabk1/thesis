from models.base import Base, Engine
from models import cost
from models import product
from models import inventory


Base.metadata.create_all(Engine)
