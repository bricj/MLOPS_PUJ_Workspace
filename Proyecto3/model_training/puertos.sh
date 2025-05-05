#!/bin/bash

for port in 32148 30921 30307 32569 31485
do
  sudo socat TCP-LISTEN:$port,fork TCP:192.168.58.2:$port &
done
wait
