#! /bin/sh
COUNTER=0
while [ "$COUNTER" -lt 3 ]; do
	echo 'stdout'
	echo 'stderr' >&2
	sleep 1
	COUNTER=$((COUNTER + 1))
done
