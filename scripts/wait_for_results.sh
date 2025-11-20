#!/bin/bash

until [ -f /yocto/results ]; do
  sleep 5
done

echo "Test results received"
