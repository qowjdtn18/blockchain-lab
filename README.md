# Blockchain Lab

A growing Python project for learning how a blockchain works by building and
running a small local peer-to-peer network.

## Objective

Explore block hashing, Proof-of-Work, peer communication, and consensus through
an implementation you can inspect and run on one computer. The current version
supports three nodes and demonstrates how competing blocks can split a network.
This is an educational prototype, not a cryptocurrency for real funds.

## How it works

Each node keeps its own chain, starting from an identical Genesis block. Text
messages are collected locally. The `mine` command creates a block and searches
for a nonce whose SHA-256 hash has the requested number of leading zeros.
After committing the block locally, the node waits for Enter before sending it
to peers over HTTP. Peers verify the hash, difficulty, previous-block link, and
index before accepting it.

The first valid block accepted at a height wins locally. There is no chain
reorganization or automatic fork recovery. Chains are held in memory and reset
when nodes restart.

## Setup

Use Python 3.15. From this directory in Windows PowerShell:

    py -3.15 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt

Dependencies: `ecdsa`, `pycryptodome`, `base58`, `Flask`, and `requests`.

No pre-generated keypair is included. First run the program once to generate a
local Legacy Bitcoin P2PKH vanity keypair with the default prefix `LAB`:

    python main.py --vanity-prefix LAB

Wait for the address search to finish, then enter `exit`. The generated
`keypair.json` contains a private key, stays on your machine, and is excluded
from Git. Never use these keys for real funds.

## Run three nodes

Open three terminals in this directory, activating the virtual environment in
each. Start all three nodes before mining:

    # Terminal 1
    python main.py --config node1.json --vanity-prefix LAB --difficulty 4

    # Terminal 2
    python main.py --config node2.json --vanity-prefix LAB --difficulty 4

    # Terminal 3
    python main.py --config node3.json --vanity-prefix LAB --difficulty 4

Nodes listen on localhost ports 8001, 8002, and 8003. Configuration files define
each node's name, port, and peers. Use the same difficulty across the network.

| Argument | Purpose |
| --- | --- |
| `--config` | Node configuration file; omission defaults to Node1 on port 8001 with no peers |
| `--vanity-prefix` | Case-insensitive address prefix after the initial `1`; default `LAB` |
| `--difficulty` | Required leading hexadecimal zeros in a block hash; default `4` |

A vanity address contains a chosen pattern. With `LAB`, addresses begin with
`1lab` in any letter case. Matching local keys are reused on later runs.

## Commands

| Command | Action |
| --- | --- |
| `msg <text>` | Queue a local text message |
| `mine` | Mine one block, then wait for Enter before broadcasting |
| `showChain` | Display the local chain in ASCII boxes |
| `demoSetup` | Create missing node configuration files without overwriting existing ones |
| `exit` | Stop the node |

For normal operation, press Enter after mining to send the block, then compare
`showChain` output across the nodes. A valid received block returns HTTP 200;
a block that fails validation returns HTTP 400. An unreachable peer produces a
warning while the sender continues.

## Fork experiment

The Enter prompt deliberately separates local commitment from propagation.
Normally, broadcasting would follow mining immediately. Here, manual release
makes competing-block scenarios reproducible without synchronizing random
mining completion times.

Start fresh nodes with the same difficulty. Mine on Node2 and Node3, leaving both
at their broadcast prompts until each has committed a block at the same height.
Then press Enter on each. The nodes reject the competing block and retain
different hashes at that height. Node1 accepts whichever arrives first.

## Hash format

SHA-256 hashes the UTF-8 encoding of a JSON array in this order:

    [index, timestamp, prev_hash, data, nonce, miner_address]

Serialization uses `json.dumps(fields, separators=(",", ":"), ensure_ascii=True)`.
The resulting hash is lowercase hexadecimal. The stored block adds a seventh
field, `hash`, which is excluded from its own hash input. Genesis is trusted and
is exempt from the Proof-of-Work target.
