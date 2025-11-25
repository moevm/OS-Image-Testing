touch user-data
touch meta-data

echo "#cloud-config
password: ""$2""
chpasswd:
  expire: false
users:
- default
- name: ""$1""
  ssh_redirect_user: true
  plain_text_passwd: ""$2""
  sudo: ['ALL=(ALL) NOPASSWD:ALL']
  groups: users, sudo, admin
  shell: /bin/bash
  lock_passwd: false" > user-data

echo "instance-id: 510/susevm" > meta-data

cloud-localds cloud-init.iso user-data meta-data