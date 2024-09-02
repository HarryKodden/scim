#!/bin/sh

# Start the first process
uvicorn main:app --host 0.0.0.0 &
PID1=$!

# Check if DATABASE_URL is set, then start the second process
if [ -n "$DATABASE_URL" ]; then
    sh -c "sleep 5 && huey_consumer.py task_runner.huey" &
    PID2=$!
fi

# Wait for the uvicorn process to complete
wait $PID1

# If the huey process was started, wait for it to complete as well
if [ -n "$PID2" ]; then
    wait $PID2
fi