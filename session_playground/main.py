from character import ModelCharacter
from base import Session


def create_characters(session):
    for i in range(10):
        char = ModelCharacter()
        if i % 2 == 0:
            char.strength = 0
            char.luck = 0
            char.intelligence = 0
            char.charm = 0
        session.add(char)
    session.commit()


def get_subset(char_lst):
    my_lst = [char for char in char_lst
             if char.intelligence % 2 == 0]
    return my_lst


def pop_and_edit(lst):
    for char in lst:
        char.luck = 555
        lst.append(char)


def in_place_edit(lst):
    count = len(lst)
    print("count = ", count)
    for i in range(count):
        print("\thi")
        char = lst.pop(0)
        char.luck = 222
        print("\t" + char.__str__())
        lst.append(char)

def print_all(session):
    characters = session.query(ModelCharacter)\
        .order_by(ModelCharacter.id).all()
    for char in characters:
        char.print()


if __name__ == '__main__':
    session = Session()
    create_characters(session)

    print("\nBEFORE: ")
    print_all(session)

    char_lst = session.query(ModelCharacter).all()  # pull all chars
    sublist = get_subset(char_lst)  # get subset to edit

    print("\nIn place Edit:")
    in_place_edit(sublist)
    for char in char_lst:
        char.print()

    print("\nPopped and edited:")
    sublist = get_subset(char_lst)
    sublist.sort(key=lambda x: x.id)
    for char in char_lst:
        char.print()

    print("\nAFTER no session: ")
    char_lst.sort(key=lambda x: x.id)
    for char in char_lst:
        char.print()

    print("\nAFTER w/session: ")
    print_all(session)

    # psql -c "DROP DATABASE playground;"
    # psql -c "CREATE DATABASE playground;"
