#!/bin/bash

version=0.2.1
LOGFILE="snippets/code.snippet.${version}.py"

> $LOGFILE

append_content() {
    echo "# $1" >> $LOGFILE
    # echo '```python' >> $LOGFILE
    cat "$1" >> $LOGFILE
    # echo '```' >> $LOGFILE
    echo "" >> $LOGFILE
}

files=$(find ./app -name "*.py")
for file in $files; do
    append_content $file
done
echo "Content of all specified files has been logged to $LOGFILE."