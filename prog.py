from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role
from objects import shopper, simulator


def all_inventory(session):
	print("a")
	inv_list = session.query(inventory).all()
	print("b")
	for each in inv_list:
		print(each)

	return 0

def run():
	session = Session()
	num_products = session.query(product.grp_id).count()

	shoppers = []
	for x in range (50):
		shoppers[x] = shopper(num_products)

	for each in shoppers:
		shopper.shop()
		shopper.checkout()


	try:
		all_inventory(session)
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()

	print("c")

if __name__ == "__main__":
	run()