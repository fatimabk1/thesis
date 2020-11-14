from datetime import datetime
from models import Shopper, Lane, Employee, Inventory, Const
from models import (ModelShopper,
                    ModelEmployee,
                    ModelLane,
                    Status,
                    Role,
                    Shift,
                    Schedule)
from models.base import provide_session, Session
import sys


# steps for now, later it will be the constant # of minutes in a day
@provide_session
def day(lanes, session=None):
    steps = 30
    open_lanes = 0
    Employee.set_day_schedule(day, session)

    for i in range(steps):
        if i % 60 == 0:
            # num_shoppers = something based on busyness
            Shopper.create(1)

        # -------------------------------------------------- advance shoppers
        group = session.query(ModelShopper.id).all()
        if group:
            for sid in group:
                stat = Shopper.step(sid)
                s = None
                if (stat is Status.QUEUE_READY or stat is Status.QUEUEING
                        or stat is Status.DONE):
                    s = session.query(ModelShopper)\
                        .filter(ModelShopper.id == sid).one()
                    assert(s.status == stat)

                    if stat is Status.QUEUE_READY:
                        Lane.queue_shopper(sid, lanes, open_lanes)  # CHECK if we should pass a session
                        s.set_status(Status.QUEUEING)
                    elif stat is Status.QUEUEING:
                        Shopper.increment_qtime(sid, session)
                    elif stat is Status.DONE:
                        session.delete(s)
                    session.commit()

        # -------------------------------------------------- advance lanes
        open_lanes = Lane.manage(lanes, open_lanes)  # expand & open -OR- collapse
        if Const.shift_change(Const.CLOCK):
            Lane.shift_change(session)
        for index, ln in enumerate(lanes):
            if index >= open_lanes and ln.length == 0:
                ln.close()  # test if values persist -- may need to pass a session to return employee
            ln.step(session)

        # -------------------------------------------------- advance employees
        Employee.prepare_employees(session)
        group = session.query(ModelEmployee)\
            .filter(ModelEmployee.role != Role.CASHIER,
                    ModelEmployee.role != Role.IDLE).all()
        for emp in group:
            emp.do_task(session)


@provide_session
def setup(session=None):
    # create & schedule employees
    for i in range(Const.NUM_EMPLOYEES):
        Employee.create_employee(session)
    Employee.make_week_schedule(session)

    # create and open minimum lanes
    lanes = []
    for i in range(Const.MAX_LANES):
        ln = SingleLane()
        if i < Const.MIN_LANES:
            ln.open()
        lanes[i] = ln

    # create products and stock all inventory
    products = session.query(ModelProduct).all()
    for prod in products:
        prod.setup()

    session.commit()

def run():
    lanes = []
    open_lanes = Const.MIN_LANES
    setup()

    for i in range(Const.NUM_DAYS):
        day(lanes, open_lanes)
