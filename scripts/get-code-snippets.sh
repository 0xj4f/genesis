#!/bin/bash

LOGFILE="snippets/code.snippet.py"

# Ensure the logfile is empty before starting
> $LOGFILE

# Function to append file content to the log
append_content() {
    echo "# $1" >> $LOGFILE
    # echo '```python' >> $LOGFILE
    cat "$1" >> $LOGFILE
    # echo '```' >> $LOGFILE
    echo "" >> $LOGFILE
}

# Append content of each file
append_content "app/main.py"
append_content "app/auth/auth.py"
append_content "app/database/user_db_interface.py"
append_content "app/database/session.py"
append_content "app/models/user_api_model.py"
append_content "app/models/user_db_model.py"
append_content "app/routes/users.py"
append_content "app/routes/profiles.py"
append_content "app/services/user_service.py"
append_content "app/services/profile_service.py"
append_content "app/utils/security.py"
append_content "app/utils/helpers.py"

echo "Content of all specified files has been logged to $LOGFILE."
