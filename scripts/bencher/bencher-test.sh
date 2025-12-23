curl --tlsv1.2 -sSfL bencher_console:3000/download/install-cli.sh | sh
source $HOME/.cargo/env

bencher run --host http://bencher_api:61016 --project yocto-bencher-test --file processing.log "bencher mock"