from sqlalchemy import Column, Integer, String, Float, Enum
from base import Base, Engine


class ModelCharacter(Base):
    __tablename__ = "tbl_character"

    id = Column(Integer, primary_key=True)
    strength = Column(Integer, default=3)
    luck = Column(Integer, default=3)
    intelligence = Column(Integer, default=3)
    charm = Column(Integer, default=3)

    def __str__(self):
        return ("<char_{}: strength={}, luck={}, intelligence={}, charm={}"
                .format(self.id, self.strength,
                        self.luck, self.intelligence,
                        self.charm))
    
    def print(self):
        print(self.__str__())

Base.metadata.create_all(Engine)
