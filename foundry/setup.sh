#!/usr/bin/env bash
# Install Foundry dependencies for Night Shift Security harness
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v forge &>/dev/null; then
    echo "Foundry not installed. Install via: curl -L https://foundry.paradigm.xyz | bash"
    exit 1
fi

if [ ! -d "lib/forge-std" ]; then
    forge install foundry-rs/forge-std
fi

forge build
echo "Foundry harness ready."