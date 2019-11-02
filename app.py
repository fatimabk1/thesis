from base import Engine, Session, Base
from models import inventory, product, category, price, revenue, cost, employee, role


def all_inventory(session):
	print("a")

	inv_list = session.query(inventory).all()
	print("b")

	for each in inv_list:
		print(each)

	return 0
	# return render_template('show_all.html', items=session.query(inventory).all())

def run():
	session = Session()

	try:
		all_inventory(session)
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()

if __name__ == "__main__":
	run()