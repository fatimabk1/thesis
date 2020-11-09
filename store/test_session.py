from models import inventory, constants as const
from models import ModelInventory, provide_session
from tabulate import tabulate
from datetime import date
CLOCK = const.CLOCK


@provide_session
def funcA_no(headers, fmt, session=None):
    print("\treturned:")
    inv_ret = funcB(19)
    table = []
    table.append(inv_ret.__repr__())
    print(tabulate(table, headers, tablefmt=fmt))

    print("\tqueried:")
    inv = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == 19).one()
    table = []
    table.append(inv.__repr__())
    print("\n", tabulate(table, headers, tablefmt=fmt))
    return inv


@provide_session
def funcA_yes(headers, fmt, session=None):
    print("\treturned:")
    inv_ret = funcB(20, session)
    table = []
    table.append(inv_ret.__repr__())
    print(tabulate(table, headers, tablefmt=fmt))

    print("\OTHERERR:")
    inv = session.query(ModelInventory)\
        .filter(ModelInventory.grp_id == 18).one_or_none()
    if inv is None:
        print("None")
    else:
        table = []
        table.append(inv.__repr__())
        print("\n", tabulate(table, headers, tablefmt=fmt))
        return inv


@provide_session
def funcB(grp, session=None):
    today = date(CLOCK.year, CLOCK.month, CLOCK.day)
    inv = ModelInventory(
        grp_id=grp,
        cart_stock=0,
        shelved_stock=13,
        back_stock=0,
        pending_stock=0,
        available=today,
        sell_by=today)
    session.add(inv)
    session.commit()
    return inv


if __name__ == "__main__":
    headers = ["id",
               "grp_id",
               "cart",
               "shelved",
               "back",
               "pending",
               "available",
               "sell_by"]
    fmt = "fancy_grid"

    # NO PASS
    print("No passing session:")
    funcA_no(headers, fmt)

    # YES PASS
    print("\nPassing session:")
    funcA_yes(headers, fmt)
