#!/bin/bash

# -------------------------------------- INITIATE
# rm logfile
# psql -c '\i db_init.sql'
# psql -c '\q'


# -------------------------------------- RUN APPLICATION
echo "Welcome to store simulator. 'r' runs the simulator, 'q' exits and 't' rebuilds the database"
echo -n "store-sim=# "
read COMMAND
LAST=$COMMAND

while [ "$COMMAND" != "q" ]; do
	if [ "$COMMAND" == "r" ];then
		LAST=$COMMAND
		pg_dump store > store.dump
		python prog.py 
		psql -c "DROP DATABASE store;"  --output='/dev/null'
		psql -c "CREATE DATABASE store;"  --output='/dev/null'
		psql store < store.dump --output='/dev/null'
	elif [ "$COMMAND" == "q" ]; then
		LAST=$COMMAND
		break
	elif [ "$COMMAND" == "t" ]; then
		psql -c "DROP DATABASE store;"  --output='/dev/null'
		psql -c "\i db_init.sql"
		echo "database rebuilt"
	fi 
	echo -n "store-sim=# "
	read COMMAND
done

# -------------------------------------- CLEANUP
# psql -c 'DROP DATABASE store;'
# psql -c '\q'
# compress/decompress store.dump later when we input large 
# amounts of data: https://www.postgresql.org/docs/9.1/backup-dump.html		
# psql -c '\q'pg_restore -C -d store store.dump
