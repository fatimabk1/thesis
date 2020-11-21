from models.Base import Base, Engine
from models import Cost, Product, Inventory, Cart


Base.metadata.create_all(Engine)
