from datetime import datetime
from models import shopper, lane, employee, inventory, const
from models import (ModelShopper,
                    ModelEmployee,
                    ModelLane,
                    Status,
                    Role,
                    Shift,
                    Schedule)
from models.base import provide_session, Session
import sys


# steps for now, later it will be the set # of minutes in a day
@provide_session
def day(steps, session=None): 
    for i in range(steps):
        if i == 0:
            employee.set_day_schedule(day, session)

        if i % 60 == 0:
            # num_shoppers = something based on busyness
            shopper.create(1)

        # -------------------------------------------------- advance shoppers
        group = session.query(ModelShopper.id).all()
        if group:
            for sid in group:
                stat = shopper.step(sid)
                s = None
                if (stat is Status.QUEUE_READY or stat is Status.QUEUEING
                        or stat is Status.DONE):
                    s = session.query(ModelShopper)\
                        .filter(ModelShopper.id == sid).one()
                    assert(s.status == stat)

                    if stat is Status.QUEUE_READY:
                        lane.enque(sid)  # CHECK if we should pass a session
                        s.set_status(Status.QUEUEING)
                    elif stat is Status.QUEUEING:
                        shopper.increment_qtime(sid, session)
                    elif stat is Status.DONE:
                        session.delete(s)
                    session.commit()

        # -------------------------------------------------- advance lanes
        lane.manage(session)  # open/close/etc
        group = session.query(ModelLane.id).all()
        for lid in group:
            lane.step(lid)

        # -------------------------------------------------- advance employees
        employee.prepare_employees(session)
        group = session.query(ModelEmployee)\
            .filter(ModelEmployee.role != Role.CASHIER,
                    ModelEmployee.role != Role.IDLE).all()
        for emp in group:
            emp.do_task(session)


def run():
    # overall setup
    session = Session()
    for i in range(const.NUM_EMPLOYEES):
        employee.create_employee(session)
    employee.make_week_schedule(session)
    session.close()

    for i in range(const.NUM_DAYS):
        day()

    session.close()
