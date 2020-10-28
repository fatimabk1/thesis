from models.base import Base, Engine
from models import cost, product, inventory, cart
from sqlalchemy.orm import relationship
# from models import product
# from models import inventory

# inventory.ModelInventory.product = relationship("Product", )
# product.ModelProduct.stock = relationship()

Base.metadata.create_all(Engine)
