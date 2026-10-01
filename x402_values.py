#!/usr/bin/env python3
"""Stage 2: attach recipient + amount to each x402 settlement.

Method: for the same block window, pull USDC Transfer logs and join to the
AuthorizationUsed set by transaction hash. transferWithAuthorization emits both
in one transaction, so the Transfer in a tx that also emitted AuthorizationUsed
is that settlement's payer -> recipient -> amount.

Guard against the obvious wrong answer: a tx may contain several Transfers
(router/aggregator paths). We only accept a join when the tx has exactly as many
Transfers as AuthorizationUsed events and the Transfer's `from` equals the
authorizer. Anything else is recorded as ambiguous and excluded from value totals
rather than guessed.
"""
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
D = os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure"))
OUT = os.path.join(D, "settlements.jsonl")


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
                raise RuntimeError(str(r["error"])[:120])
            return r["result"]
        except Exception:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def get_logs_split(start, end, depth=0):
    try:
        return rpc("eth_getLogs", [{"address": USDC, "topics": [TRANSFER],
                                    "fromBlock": hex(start), "toBlock": hex(end)}], tries=2)
    except Exception:
        if start >= end or depth > 14:
            raise
        mid = (start + end) // 2
        return get_logs_split(start, mid, depth + 1) + get_logs_split(mid + 1, end, depth + 1)


def main():
    win = json.load(open(os.path.join(D, "window.json")))
    lo, hi = win["from_block"], win["to_block"]

    auth_by_tx = defaultdict(list)
    for line in open(os.path.join(D, "authorizations.jsonl")):
        r = json.loads(line)
        auth_by_tx[r["tx"]].append(r["authorizer"])
    print(f"authorizations: {sum(len(v) for v in auth_by_tx.values())} in {len(auth_by_tx)} txs",
          flush=True)

    xfer_by_tx = defaultdict(list)
    CH = 800
    seen = 0
    for start in range(lo, hi, CH):
        end = min(start + CH - 1, hi)
        logs = get_logs_split(start, end)
        for lg in logs:
            tx = lg["transactionHash"]
            if tx not in auth_by_tx:      # only txs we care about
                continue
            xfer_by_tx[tx].append({
                "from": "0x" + lg["topics"][1][-40:],
                "to": "0x" + lg["topics"][2][-40:],
                "value": int(lg["data"], 16),
            })
        seen += len(logs)
        print(f"  {start}-{end}: {len(logs)} transfers scanned (total {seen})", flush=True)

    matched = ambiguous = 0
    with open(OUT, "w") as f:
        for tx, authorizers in auth_by_tx.items():
            xs = xfer_by_tx.get(tx, [])
            if len(xs) != len(authorizers):
                ambiguous += len(authorizers)
                continue
            ok = True
            for a, x in zip(sorted(authorizers), sorted(xs, key=lambda z: z["from"])):
                if x["from"] != a:
                    ok = False
            if not ok:
                ambiguous += len(authorizers)
                continue
            for x in xs:
                f.write(json.dumps({"tx": tx, "payer": x["from"], "payee": x["to"],
                                    "usdc": x["value"] / 1e6}) + "\n")
                matched += 1
    print(f"DONE matched={matched} ambiguous_excluded={ambiguous} -> {OUT}")


if __name__ == "__main__":
    main()
