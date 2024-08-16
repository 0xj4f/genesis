#!/bin/bash
LOGFILE=code.txt

echo app/main.py >> $LOGFILE
echo "$(cat app/main.py)" >> $LOGFILE

echo app/auth/auth.py >> $LOGFILE
echo "$(cat app/auth/auth.py)" >> $LOGFILE

echo app/database/database_config.py >> $LOGFILE
echo "$(cat app/database/database_config.py)" >> $LOGFILE

echo app/database/database_interface.py >> $LOGFILE
echo "$(cat app/database/database_interface.py)" >> $LOGFILE

echo app/database/session.py >> $LOGFILE
echo "$(cat app/database/session.py)" >> $LOGFILE

echo app/models/api_models.py >> $LOGFILE
echo "$(cat app/models/api_models.py)" >> $LOGFILE

echo app/models/database_models.py >> $LOGFILE
echo "$(cat app/models/database_models.py)" >> $LOGFILE
