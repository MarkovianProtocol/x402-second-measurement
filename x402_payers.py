#!/usr/bin/env python3
"""Measure the facts about the busiest payers that findings.md reports, for the pulled window.

Writes payers.json: for the 40 busiest payers, transaction count and contract code at the window's
last block; for the top 5, ETH and USDC balances there; USDC sent TO the top 4 inside the window;
and how many distinct wallets submitted a random 150 of the busiest payer's settlements.
State is read at the window's last block; if the endpoint no longer serves that block's state,
it falls back to the latest block and records which one it used. Stdlib only.
"""
import collections, json, os, random, time, urllib.request

D = os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure"))
RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def rpc(method, params, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                                         "params": params}).encode(),
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": "markovian-x402-measure/1.0"})
            r = json.load(urllib.request.urlopen(req, timeout=45))
            if "error" in r:
                raise RuntimeError(str(r["error"])[:160])
            return r["result"]
        except Exception:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def logs_to(addr, start, end, depth=0):
    topic = "0x" + "0" * 24 + addr[2:]
    try:
        return rpc("eth_getLogs", [{"address": USDC, "topics": [TRANSFER, None, topic],
                                    "fromBlock": hex(start), "toBlock": hex(end)}], tries=2)
    except Exception:
        if start >= end or depth > 12:
            raise
        mid = (start + end) // 2
        return logs_to(addr, start, mid, depth + 1) + logs_to(addr, mid + 1, end, depth + 1)


def main():
    w = json.load(open(os.path.join(D, "window.json")))
    txs = collections.defaultdict(list)
    for line in open(os.path.join(D, "authorizations.jsonl")):
        r = json.loads(line)
        txs[r["authorizer"]].append(r["tx"])
    top = sorted(txs, key=lambda a: -len(txs[a]))[:40]

    tag = hex(w["to_block"])
    try:
        rpc("eth_getBalance", [top[0], tag], tries=2)
    except Exception:
        tag = "latest"
    state_block = w["to_block"] if tag != "latest" else int(rpc("eth_blockNumber", []), 16)

    rows = []
    for a in top:
        nonce = int(rpc("eth_getTransactionCount", [a, tag]), 16)
        code = rpc("eth_getCode", [a, tag])
        delegated = code.startswith("0xef0100") and len(code) == 48   # EIP-7702: a wallet pointing at contract code
        rows.append({"payer": a, "settlements": len(txs[a]), "nonce": nonce,
                     "contract": code not in ("0x", "0x0") and not delegated,
                     "delegate": "0x" + code[8:] if delegated else None})
    for r in rows[:5]:
        r["eth"] = int(rpc("eth_getBalance", [r["payer"], tag]), 16) / 1e18
        data = "0x70a08231" + "0" * 24 + r["payer"][2:]
        r["usdc"] = int(rpc("eth_call", [{"to": USDC, "data": data}, tag]), 16) / 1e6
    for r in rows[:4]:
        r["usdc_in_window"] = sum(int(l["data"], 16) for l in logs_to(r["payer"], w["from_block"], w["to_block"])) / 1e6

    random.seed(20261001)
    sample = random.sample(txs[top[0]], min(150, len(txs[top[0]])))
    submitters = collections.Counter(rpc("eth_getTransactionByHash", [h])["from"].lower() for h in sample)

    out = {"state_block": state_block, "state_at_window_end": tag != "latest", "top40": rows,
           "busiest_sample": len(sample), "busiest_submitters": len(submitters)}
    json.dump(out, open(os.path.join(D, "payers.json"), "w"), indent=1)
    z = sum(r["nonce"] == 0 for r in rows)
    print(f"state at block {state_block} ({'window end' if out['state_at_window_end'] else 'latest; window-end state not served'})")
    print(f"zero-nonce payers in top 40: {z}; contracts: {sum(r['contract'] for r in rows)}; "
          f"EIP-7702 delegated wallets: {sum(bool(r['delegate']) for r in rows)}")
    print(f"busiest payer: nonce {rows[0]['nonce']}, ETH {rows[0]['eth']}, USDC {rows[0]['usdc']}")
    print(f"distinct submitters for {len(sample)} of its settlements: {len(submitters)}")


if __name__ == "__main__":
    main()
