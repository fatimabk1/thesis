#!/bin/bash

# -------------------------------------- INITIATE
# rm logfile
# psql -c '\i db_init.sql'
# psql -c '\q'


# -------------------------------------- RUN APPLICATION
echo "Welcome to store simulator. 'run' runs the simulator and 'quit' exits"
echo -n "store-sim=# "
read COMMAND

while [ "$COMMAND" != "quit" ]; do
	echo you entered: $COMMAND
	if [ "$COMMAND" == "run" ];then
		pg_dump store > store.dump
		python prog.py 
		pg_restore -c -d store store_dump.tar
	elif [ "$COMMAND" == "quit" ]; then
		break
	fi 
	echo -n "store-sim=# "
	read COMMAND
done

# -------------------------------------- CLEANUP
# psql -c 'DROP DATABASE store;'
# psql -c '\q'
# compress/decompress store.dump later when we input large 
# amounts of data: https://www.postgresql.org/docs/9.1/backup-dump.html