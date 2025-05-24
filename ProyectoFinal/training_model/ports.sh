# for port in 32148 30921 32569 31485 30855
# do
#   sudo socat TCP-LISTEN:$port,fork TCP:192.168.58.2:$port &
# done
# wait

sudo socat TCP-LISTEN:5433,bind=10.43.101.166,fork TCP:192.168.49.2:30543 &
wait