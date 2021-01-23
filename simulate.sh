#!/bin/bash

# -------------------------------------- INITIATE
# rm logfile
# psql -c '\i db_init.sql'
# psql -c '\q'


# -------------------------------------- RUN APPLICATION
PURPLE='\033[0;35m'
NC='\033[0m' # No Color
echo "Welcome to store simulator. 'r' runs the simulator, 'q' exits and 't' rebuilds the database"
psql -c "CREATE DATABASE store;"  --output='/dev/null'
python store/create_tables.py            # RELATIVE PATH --output='/dev/null'
echo "" > build_logfile
python store/db_build.py 2> build_logfile
psql -c "\i store/db_init.sql"                                      # RELATIVE PATH
pg_dump store > store/data/store.dump                               # RELATIVE PATH
echo -e "${PURPLE}DB setup confirmed.${NC}"
echo -e -n "${PURPLE}store-sim=# ${NC}"
read COMMAND

while true; do
	if [ "$COMMAND" == "r" ];then
        # python store/test_session.py
        echo "" > logfile
        python store/main.py 2> logfile
        # python store/prog.py                                        # RELATIVE PATH
        psql -c "DROP DATABASE store;"
        psql -c "CREATE DATABASE store;"
        psql store < store/data/store.dump --output='/dev/null'     # RELATIVE PATH
        echo -e "${PURPLE}Program execution complete.${NC}"
	elif [ "$COMMAND" == "q" ]; then
        psql -c "DROP DATABASE store;" --output='/dev/null'
        echo -e "${PURPLE}DB removed.${NC}"
		break
	elif [ "$COMMAND" == "t" ]; then
		psql -c "DROP DATABASE store;"  --output='/dev/null'
        psql -c "CREATE DATABASE store;"  --output='/dev/null'
        python store/create_tables.py --output='/dev/null'     # RELATIVE PATH
        psql -c "\i store/db_init.sql"                                # RELATIVE PATH
        echo "" > build_logfile
        python store/db_build.py 2> build_logfile
        pg_dump store > store/data/store.dump
		echo -e "${PURPLE}DB rebuilt.${NC}"
    else
        :
	fi 
	echo ""
    echo -n -e "${PURPLE}store-sim=# ${NC}"
	read COMMAND
done
