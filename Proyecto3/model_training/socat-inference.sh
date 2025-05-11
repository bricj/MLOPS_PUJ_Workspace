#!/bin/bash
# Redirigir desde la IP específica 10.43.101.166
sudo socat TCP-LISTEN:5433,bind=10.43.101.166,fork TCP:192.168.58.2:30433 &
wait

