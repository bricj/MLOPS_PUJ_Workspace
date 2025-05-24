#!/bin/bash

for port in 30900 30901 30500 30543
do
  sudo socat TCP-LISTEN:$port,fork TCP:192.168.49.2:$port &
done
wait
