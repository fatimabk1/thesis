from models.Base import Base, Engine
from models import Cost, Product, Inventory, Cart, Employee


Base.metadata.create_all(Engine)
