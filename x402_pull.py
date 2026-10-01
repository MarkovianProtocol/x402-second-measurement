#!/usr/bin/env python3
"""Pull x402-style settlements from Base directly, no indexer.

x402 settles as EIP-3009 transferWithAuthorization on USDC, which emits
AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce).
That event is the marker. We page eth_getLogs over a fixed block window and
record (block, txhash, authorizer) so the pull is reproducible from the same
window by anyone with a Base RPC endpoint.
"""
import json
import os
import sys
import time
import urllib.request

USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
AUTH = "0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5"
RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
CHUNK = 1500
OUT = os.path.join(os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure")), "authorizations.jsonl")
META = os.path.join(os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure")), "window.json")


def rpc(method, params, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1,
                                      "method": method, "params": params}).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "markovian-x402-measure/1.0"})
            r = json.load(urllib.request.urlopen(req, timeout=45))
            if "error" in r:
                raise RuntimeError(r["error"].get("message", "")[:120])
            return r["result"]
        except Exception as e:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def get_logs_split(start, end, depth=0):
    """eth_getLogs with bisection: public endpoints reject over-dense ranges."""
    try:
        return rpc("eth_getLogs", [{"address": USDC, "topics": [AUTH],
                                    "fromBlock": hex(start), "toBlock": hex(end)}], tries=2)
    except Exception:
        if start >= end or depth > 12:
            raise
        mid = (start + end) // 2
        return get_logs_split(start, mid, depth + 1) + get_logs_split(mid + 1, end, depth + 1)


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "-" else 24.0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if len(sys.argv) > 3:                   # fixed window: x402_pull.py - FROM_BLOCK TO_BLOCK
        lo, hi = int(sys.argv[2]), int(sys.argv[3])
    else:
        head = int(rpc("eth_blockNumber", []), 16)
        blocks = int(hours * 3600 / 2)      # Base ~2s blocks
        lo, hi = head - blocks, head
    hdr = rpc("eth_getBlockByNumber", [hex(hi), False])
    lob = rpc("eth_getBlockByNumber", [hex(lo), False])
    json.dump({"rpc": RPC, "usdc": USDC, "event": "AuthorizationUsed",
               "topic0": AUTH, "from_block": lo, "to_block": hi,
               "from_ts": int(lob["timestamp"], 16),
               "to_ts": int(hdr["timestamp"], 16),
               "pulled_at": int(time.time())}, open(META, "w"), indent=1)

    n = 0
    with open(OUT, "w") as f:
        for start in range(lo, hi, CHUNK):
            end = min(start + CHUNK - 1, hi)
            logs = get_logs_split(start, end)
            for lg in logs:
                f.write(json.dumps({
                    "block": int(lg["blockNumber"], 16),
                    "tx": lg["transactionHash"],
                    "authorizer": "0x" + lg["topics"][1][-40:],
                }) + "\n")
            n += len(logs)
            print(f"  {start}-{end}: {len(logs)} (total {n})", flush=True)
    print("DONE", n, "authorizations |", OUT)


if __name__ == "__main__":
    main()
