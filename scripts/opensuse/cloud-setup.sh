#!/bin/bash

CI_KEY=""
KEY_FN="keys"

if [ ! -e "${KEY_FN}".pub ]; then
    ssh-keygen -t rsa -b 4096 -f keys -P ""
fi

PUB_KEYS_FILE=$(cat "${KEY_FN}".pub)

CI_KEY+=$(echo "${PUB_KEYS_FILE}" | cut -d " " -f 1)
CI_KEY+=" "
CI_KEY+=$(echo "${PUB_KEYS_FILE}" | cut -d " " -f 2)

cat << EOF > user-data
#cloud-config
password: $2
chpasswd:
  expire: false
users:
- default
- name: $1
  plain_text_passwd: $2
  sudo: ['ALL=(ALL) NOPASSWD:ALL']
  groups: users, sudo, admin
  shell: /bin/bash
  lock_passwd: false
  ssh_authorized_keys:
    - ${CI_KEY}
EOF

cat << EOF > meta-data
instance-id: 420/susevm
EOF

cloud-localds cloud-init.iso user-data meta-data
