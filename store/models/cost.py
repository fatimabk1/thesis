from sqlalchemy import Column, Integer, Float, String, Date
from base import Base


class ModelCost(Base):
    __tablename__ = "tbl_cost"

    cost_id = Column(Integer, primary_key=True)
    stamp = Column(Date)
    value = Column(Float)
    ctype = Column(String(30))
    # ctype refers to cost type: "labor", "stock", or "overhead"

    def __repr__(self):
        return "<Cost(id='{}', timestamp='{}', value={}, cost type={})>"\
            .format(self.cost_id, self.stamp, self.value, self.ctype)
