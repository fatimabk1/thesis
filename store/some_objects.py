from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role, queuetime
import random
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.sql.expression import func
from collections import deque
import time
import sys


def endSession(session):
	try:
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()


# ------------------------------------------------------------------------------------------------ CLASSES



# simulates the store for a number of months and days
# handles restocking, inventory ordering, price/sale updates, removing expired products
# outputs aggregate stats to data visualizor application
# class Period_Simulator(sim, months, days):
# 	def __init__(self):
# 		self.simulator = sim

		






# class Stats:

# class Day_Simulator:













