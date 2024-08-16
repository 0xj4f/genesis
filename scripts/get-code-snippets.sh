#!/bin/bash

version=0.2.3
LOGFILE="snippets/code.snippet.${version}.py"
# LOGFILE="snippets/code.snippet.profile.${version}.py"

> $LOGFILE

append_content() {
    echo "# $1" >> $LOGFILE
    # echo '```python' >> $LOGFILE
    cat "$1" >> $LOGFILE
    # echo '```' >> $LOGFILE
    echo "" >> $LOGFILE
}

files=$(find ./app -name "*.py")
# files=$( find ./app -name "*profile*.py")
for file in $files; do
    append_content $file
done
echo "Content of all specified files has been logged to $LOGFILE."
