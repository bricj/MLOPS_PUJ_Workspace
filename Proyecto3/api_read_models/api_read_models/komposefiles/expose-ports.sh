#!/bin/bash

NODE_IP="localhost"  # <-- Reemplaza con la IP correcta

for port in 45189
do
  echo "Exponiendo puerto $port en $NODE_IP..."
  sudo socat TCP-LISTEN:$port,fork TCP:$NODE_IP:$port &
done

wait
