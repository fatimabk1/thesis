from datetime import datetime
from models import shopper, lane, employee
from models import ModelShopper, ModelEmployee, ModelLane, Status
from models import provide_session
import sys


# steps for now, later it will be the set # of minutes in a day
@provide_session
def day(steps, session=None): 
    for i in range(steps):
        if i % 60 == 0:
            # num_shoppers = something based on busyness
            shopper.create(1)

        # advance shoppers
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

        # advance lanes
        lane.manage()  # open/close/etc
        group = session.query(ModelLane.id).all()
        for lid in group:
            lane.step(lid)

        # advance employees
        unload_list = Inventory.unload_list()
        restock_list = Inventory.restock_list()
        toss_list = Inventory.toss_list()
        group = session.query(ModelEmployee.id).all()
        for eid in group:
            if employee.valid_task(eid) is True:
                employee.step(eid)
            else:
                emp = session.query(ModelEmployee)\
                    .filter(ModelEmployee.id == eid).one()
                if emp.get_role() is CASHIER:  # where get_task() returns the employee's currently listed role
                    sys.exit("FATAL: employee should not have an invalid cashier role")
                    employee.switch_role(eid)
                    switch_to_alt(employee.employee_id)
                else:
                    grp = refresh_shift(employee.shift):  # MAKE SEPARATE FUNC; get new task for E shift
                    if grp is not None:
                        employee.set_grp(grp)
                        employee.advance()
                    else:  # nothing to do in this shift
                        switch_to_alt(employee.employee_id) 
                        employee.advance()
            employee.step()





