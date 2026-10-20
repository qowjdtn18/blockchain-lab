import hashlib
import json
import base58
import argparse
import requests
from flask import Flask, request
from pathlib import Path
from threading import Thread, Lock
from Crypto.Hash import RIPEMD160
from ecdsa import SigningKey, SECP256k1
from datetime import datetime, timezone

chain = []
difficulty = 4
chain_lock = Lock()

app = Flask(__name__) 


# =============================================================================
# Web Server Folks
# =============================================================================
@app.route("/block", methods=["POST"])
def receive_block():
    block = request.get_json()
    with chain_lock: # AI Suggested: to lock the tread... its like mutex.
        if validate_block(block,chain,difficulty):
            chain.append(block)
        else:
            return {"message": "Block Rejected"}, 400
    return {"message": "Block Accepted"}, 200

def broadcast_block(block, peers):
    for peer in peers:
        print(f"[+] Sending Block #{block['index']} to {peer}")
        url = peer + "/block"
        try:
            response = requests.post(url, json=block, timeout=3)
            response.raise_for_status()
            print(f"[+] Block sent to {peer}")
        except requests.RequestException as error:
            print(f"[!] Failed to send block to {peer}: {error}")

# =============================================================================
# Key Generation
# =============================================================================
def generate_keypair(vanity_prefix):
    ##Var
    max_attempts = 1_000_000
    print("Searching for Address... This may take a while")
    for attempt in range(1, max_attempts + 1):
        # Generate a new private key and derive the corresponding public key
        private_key = SigningKey.generate(curve=SECP256k1)
        compressed_public_key = private_key.get_verifying_key().to_string("compressed")

        public_key_hash = RIPEMD160.new(hashlib.sha256(compressed_public_key).digest()).digest()

        # print("Compressed public key:", compressed_public_key.hex())
        # print("Public key hash:", public_key_hash.hex())
        # print("Hashed Key", public_key_hash.hex())
        prepended_hash = b'\x00' + public_key_hash
        # print("Prepended hash:", prepended_hash.hex())

        checksum = hashlib.sha256(hashlib.sha256(prepended_hash).digest()).digest()[:4]
        appended_hash_with_checksum = prepended_hash + checksum
        encoded_address = base58.b58encode(appended_hash_with_checksum)
        # print("Encoded address:", encoded_address.decode("ascii"))
        if encoded_address.decode("ascii").lower().startswith("1" + vanity_prefix.lower()):
            print("Public Address:", encoded_address.decode("ascii"))
            keypair = {
                "private_key": private_key.to_string().hex(),
                "public_key": compressed_public_key.hex(),
                "address": encoded_address.decode("ascii")
            }
            with open("keypair.json", "w", encoding="utf-8") as f:
                json.dump(keypair, f, indent=4)
            print("Saved to keypair.json")    
            return keypair
    else:
        print("Reached maximum attempts. Try again")
    return None

# =============================================================================
# Genesis Block Input Creation
# =============================================================================
def create_genesis_block_input():
    return {
        "index": 0,
        "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "timestamp": "2026-01-01T00:00:00Z",
        "data": ["Genesis Block"],
        "nonce": 0,
        "miner_address": "GENESIS"
    }

# =============================================================================
# Hash Creation
# =============================================================================
def calculate_hash(block):
    fields = [
        block["index"],
        block["timestamp"],
        block["prev_hash"],
        block["data"],
        block["nonce"],
        block["miner_address"],
    ]

    serialized = json.dumps(fields, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    # sha256 only takes byte... so we need everything in ascii and encode into utf-8
    return hashlib.sha256(serialized).hexdigest() #just to see 256 to hex
# =============================================================================
# Mining Function
# =============================================================================
def mine_block(previous_block, data, miner_address, difficulty):
    new_block = {
        "index": previous_block["index"] + 1,
        "prev_hash": previous_block["hash"],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": data.copy(),
        "nonce": 0,
        "miner_address": miner_address,
    }
    ## Now.... We set up the goal.
    target_prefix = "0" * difficulty #How many Leading Zeros? that was an input
    ## Now we mine
    while True: # Go until we find a hash that meets the requirements
        new_block["hash"] = calculate_hash(new_block)
        if new_block["hash"].startswith(target_prefix):#In this assignment
            break
        new_block["nonce"] += 1#next nonce
    return new_block

# =============================================================================
# Validate Block
# When Node B receives a mined block from Node A, Node B must perform the following four checks before 
# appending it to its local chain:
# 
# 1. Hash Verification: Recompute the hash from the block payload fields (excluding the hash field) and 
# confirm it exactly equals the block's hash attribute.
# 
# 2. Difficulty Verification: Check that the recomputed hash begins with the required number of leading 
# zeros (e.g., "0000").
# 
# 3. Chain Continuity: Confirm that the block's prev_hash equals the hash of Node B's current tip block.
# 
# 4. Index Sequence: Confirm that the block's index equals Node B's current tip index +1.
#
# =============================================================================
def validate_block(Received_block, chain, difficulty):
    # 1. Hash Verification
    newRecHash = calculate_hash(Received_block)

    if Received_block["hash"] != newRecHash:
        print("Reject as Hash Doesn't Match!")
        return False
    # 2. Difficulty Verification
    target_prefix = "0" * difficulty
    if not newRecHash.startswith(target_prefix):
        print("Reject as Difficulty Doesn't Match!")
        return False
    if chain[-1]["hash"] != Received_block["prev_hash"]:
        print("Reject as current Tip Block != Previous Hash... Not a correct link")
        return False
    # 3. Chain Continuity
    if Received_block["index"] != chain[-1]["index"] + 1:
        print("Index Does not match!")
        return False
    
    return True


# =============================================================================
# Chain Formatting
# =============================================================================
def show_chain(chain):
    width = 78
    border = "+" + "=" * width + "+"

    for position, block in enumerate(chain):
        if position:
            print(" " * (width // 2) + "|")
            print(" " * (width // 2) + "v")

        lines = [
            f"BLOCK #{block['index']}",
            f"Timestamp: {block['timestamp']}",
            f"Nonce: {block['nonce']}",
            f"Miner: {block['miner_address']}",
            f"Previous: {block['prev_hash']}",
            f"Hash: {block['hash']}",
            "Data: " + json.dumps(block["data"], ensure_ascii=True),
        ]
        print(border)
        for line in lines:
            for start in range(0, len(line), width - 2):
                print("| " + line[start:start + width - 2].ljust(width - 2) + " |")
        print(border)


# =============================================================================
# Startup Helpers
# =============================================================================

def parse_arguments(): #Taking user Input to start main.py
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required = False, help="Path to the node config file")
    parser.add_argument("--vanity-prefix", default="LAB", help="Vanity prefix for the public address (default: 'LAB')")
    parser.add_argument("--difficulty", type=int, default = 4, help="Mining difficulty (number of leading zeros, default: 4)")

    args = parser.parse_args()
    if not 0 <= args.difficulty <= 64:
        parser.error("--difficulty must be between 0 and 64.")
    return args


def load_config(config_path): # Reading Node Config File. It has port information...
    if config_path:
        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {"node_id": "Node1", "port": 8001, "peers": []}


def load_or_generate_keypair(vanity_prefix):#Keygen
    try:
        with open("keypair.json", "r", encoding="utf-8") as file:
            keypair = json.load(file)

        address = keypair["address"]

        if address.lower().startswith("1" + vanity_prefix.lower()): #if keypair.json is found
            print("[+] Loading keypair from keypair.json... (Found existing match)")
            print("[+] Public Address :", address)
            print("[+] Search skipped.")
            return keypair
    except (FileNotFoundError, json.JSONDecodeError, KeyError, AttributeError, TypeError):
        pass

    return generate_keypair(vanity_prefix)#if not found, create one.


def initialize_chain():#initialize chain by putting genesis input first.
    genesis = create_genesis_block_input()
    genesis["hash"] = calculate_hash(genesis)
    return [genesis]


# =============================================================================
# Interactive Commands
# =============================================================================


# =============================================================================
# Command Handlers
# =============================================================================
def handle_msg_command(message, pending_messages):
    pending_messages.append(message)
    print("[+] Message added.")


def handle_show_chain_command(chain):
    show_chain(chain)


def handle_exit_command():
    return False


def handle_help_command():
    print("Commands: msg <text>, mine, showChain, demoSetup, exit")


def handle_demo_setup_command():
    for number in range(1, 4):
        path = Path(f"node{number}.json")
        if path.exists():
            print(f"[+] Keeping existing {path}")
            continue

        peers = []

        for peer in range(1, 4):
            if peer != number:  # Exclude itself.
                peers.append(f"http://127.0.0.1:{8000 + peer}")

        config = {
            "node_id": f"Node{number}",
            "port": 8000 + number,
            "peers": peers,
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)
        print(f"[+] Created {path}")

def handle_mine_command(chain, pending_messages, miner_address, difficulty, node_id, peers):
    print(f"[+] Triggering Mining Cycle on {node_id}...")
    #take mutex
    with chain_lock:
        previous_block = chain[-1]
    #now prev block have the data...
    block = mine_block(previous_block, pending_messages, miner_address, difficulty)#-1 is end of the inded.
    #mine with the stored buffer data
    with chain_lock:
        if not validate_block(block, chain, difficulty):
            print("[!] Chain changed during mining. Try again.")
            return
        chain.append(block)
        pending_messages.clear()
    print(f"[+] Block #{block['index']} Mined! Nonce: {block['nonce']}")
    print("[+] Block Hash:", block["hash"])
    print("[+] Miner:", block["miner_address"])

    # Wait outside the lock so incoming blocks can still be processed.
    try:
        while input("[+] Press Enter to broadcast this block...") != "":
            print("[!] Press Enter without typing a command to broadcast.")
    except (EOFError, KeyboardInterrupt):
        print("\n[!] Broadcast cancelled. The block remains in the local chain.")
        return

    broadcast_block(block, peers)

# =============================================================================
# Command Loop
# =============================================================================
def run_command_loop(chain, miner_address, difficulty, node_id, peers):
    pending_messages = []
    handle_help_command()
    running = True
    while running:
        try:
            command = input(f"{node_id}> ").strip() # strip() removes leading and trailing whitespace from the input string.
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if command.startswith("msg "):
            handle_msg_command(command[4:], pending_messages)
        elif command == "mine":
            handle_mine_command(chain, pending_messages, miner_address, difficulty, node_id, peers)#handle it with seperate UI
        elif command == "showChain":
            handle_show_chain_command(chain)
        elif command == "exit":
            running = handle_exit_command()
        elif command == "demoSetup":
            handle_demo_setup_command()
        elif command:
            handle_help_command()

# =============================================================================
# Main
# =============================================================================

def main():
    global chain, difficulty

    args = parse_arguments()
    config = load_config(args.config)
    difficulty = args.difficulty
    chain = initialize_chain()

    keypair = load_or_generate_keypair(args.vanity_prefix)
    
    if keypair is None:
        return
    
    server_thread = Thread(
        target=app.run,
        kwargs={"host": "127.0.0.1", "port": config["port"], "use_reloader": False},
        daemon=True,
    )
    server_thread.start()

    run_command_loop(chain, keypair["address"], args.difficulty, config["node_id"], config["peers"])

if __name__ == "__main__":
    main()

