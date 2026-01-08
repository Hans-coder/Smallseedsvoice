#!/bin/bash
# Load environment variables and run Threads poster

# Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run script
./venv/bin/python post_to_threads.py
