from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role
from objects import Shopper, Simulator, Status, endSession
from sqlalchemy import desc, asc
import time


def inventoryStats(session):
	# display inventory stats 
	rows = session.execute(
		"SELECT * FROM inventory ORDER BY grp_id ASC;"
	)
	for row in rows:
		# print(row.grp_id, ": ", row.shelved_stock)
		print("inventory --> ", row)

def shopperStats(sim):
	sim.shoppers.sort(key=lambda x: x.status.value, reverse = True)
	for shopper in sim.shoppers:
		shopper.__repr__()
	sim.shoppers.sort(key=lambda x: x.id, reverse = False)
	

if __name__ == "__main__":
	DEBUG = True
	session = Session()
	sim = Simulator()

	if DEBUG is True:
		inventoryStats(session)

	for i in range(200):
		print("-------------------------------------------------------------------- MINUTE ", i)
		sim.advance()
		if DEBUG is True:
			print("SHOPPERS ---- ")
			sim.shoppers.sort(key=lambda x: x.status.value, reverse=True)
			for shopper in sim.shoppers:
				if shopper.status == Status.SHOPPING or shopper.status == Status.QUEUEING or shopper.status == Status.CHECKOUT or shopper.status == Status.DONE:
					s = "<shopper %d: "%(shopper.id) + str(shopper.status) + "> --- %d items / %d planned" %(len(shopper.cart), shopper.count) 
					if shopper.status == Status.QUEUEING or shopper.status == Status.CHECKOUT:
						if shopper.queue is not None:
							s += " --- Lane %d" % (shopper.queue)
					s += ">"
					print(s)
			sim.shoppers.sort(key=lambda x: x.id, reverse=True)
			sim.lanes.__repr__()
			time.sleep(2)

	print("\n\n\n---------------SIMULATION COMPLETE------------------")
	if DEBUG is True:
		inventoryStats(session)
		shopperStats(sim)
	endSession(session)
	print(".\n.\n.\n.\n.\n.\nresetting")


