#!/bin/bash

if [ -z "$1" ]; then
    echo "Dir is required argument. Example: $0 /path/to/poky"
    exit 1
fi

POKY_DIR="$1"

if [ ! -d "$POKY_DIR" ]; then
    echo "Dir [$POKY_DIR] not found."
    exit 1
fi

#так как build может содержать образы для нескольких машин
#происходит поиск конкретных собранных образов
#и предлагается выбор среди них
select_machine() {
    local poky_dir="$1"
    local result_machine_name="$2"
    local deploy_dir="$poky_dir/build/tmp/deploy/images"

    if [ ! -d "$deploy_dir" ]; then
        echo "Deploy directory [$deploy_dir] not found. Please build images first."
        exit 1
    fi

    local machines=()
    while IFS= read -r -d '' dir; do
        machines+=("$(basename "$dir")")
    done < <(find "$deploy_dir" -mindepth 1 -maxdepth 1 -type d -print0)

    if [ ${#machines[@]} -eq 0 ]; then
        echo "No built images found in $deploy_dir"
        exit 1
    fi

    echo "Available machines:"
    for i in "${!machines[@]}"; do
        echo "  $((i+1))) ${machines[i]}"
    done

    local choice
    while true; do
        read -rp "Enter the number of the machine to run: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#machines[@]} )); then
            printf -v "$result_machine_name" '%s' "${machines[choice-1]}"
            return 0
        else
            echo "Invalid choice, please enter a number between 1 and ${#machines[@]}"
        fi
    done
}


select_machine "$POKY_DIR" MACHINE

if [ -z "$MACHINE" ]; then
    echo "Can't get MACHINE"
    exit 1
fi

echo "Use $MACHINE"

source "$POKY_DIR/oe-init-build-env" "$POKY_DIR/build"

runqemu "$MACHINE"