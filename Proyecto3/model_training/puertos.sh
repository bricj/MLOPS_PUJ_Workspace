#!/bin/bash

for port in 32148 30921 32569 31485 30855
do
  sudo socat TCP-LISTEN:$port,fork TCP:192.168.58.2:$port &
done
wait
