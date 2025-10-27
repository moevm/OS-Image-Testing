#!/bin/sh
### BEGIN INIT INFO
# Provides:          pts-autoinstall
# Required-Start:    $network $remote_fs
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:
# Short-Description: Auto-install PTS tests and configure DNS
### END INIT INFO

TESTS="system/openssl"

case "$1" in
  start)
    if [ ! -s /etc/resolv.conf ] || ! grep -q "nameserver" /etc/resolv.conf; then
        echo "Configuring DNS..."
        echo "nameserver 8.8.8.8" > /etc/resolv.conf
    fi

    phoronix-test-suite batch-install $TESTS
    ;;
  stop)
    ;;
  restart|reload|force-reload)
    $0 stop
    $0 start
    ;;
  *)
    echo "Usage: $0 {start|stop|restart}"
    exit 1
    ;;
esac

exit 0
