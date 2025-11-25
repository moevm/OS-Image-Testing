cat << EOF > user-data
#cloud-config
password: $2
chpasswd:
  expire: false
users:
- default
- name: $1
  ssh_redirect_user: true
  plain_text_passwd: $2
  sudo: ['ALL=(ALL) NOPASSWD:ALL']
  groups: users, sudo, admin
  shell: /bin/bash
  lock_passwd: false
EOF

cat << EOF > meta-data
instance-id: 420/susevm
EOF

cloud-localds cloud-init.iso user-data meta-data