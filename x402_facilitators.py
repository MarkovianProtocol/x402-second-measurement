#!/usr/bin/env python3
"""Who submits x402 settlements — i.e. who the facilitators actually are.

A facilitator is the party that submits the transferWithAuthorization transaction
and pays its gas. That is exactly tx.from for a settlement transaction. We sample
blocks across the same 24h window, pull full blocks (transactions included), and
count submitters for the settlements we already identified in stage 1.

Sampling, not census: 43,200 full-block fetches is hours on a public endpoint.
The sample size is reported with the result.
"""
import json
import os
import random
import sys
import time
import urllib.request
from collections import Counter

RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
D = os.path.expanduser("~/x402_measure")
OUT = os.path.join(D, "facilitators.json")


def rpc(method, params, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1,
                                      "method": method, "params": params}).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "markovian-x402-measure/1.0"})
            r = json.load(urllib.request.urlopen(req, timeout=40))
            if "error" in r:
                raise RuntimeError(str(r["error"])[:100])
            return r["result"]
        except Exception:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def main():
    n_blocks = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    win = json.load(open(os.path.join(D, "window.json")))

    # settlement tx hashes -> payer, grouped by block
    by_block = {}
    tx_payer = {}
    for line in open(os.path.join(D, "authorizations.jsonl")):
        r = json.loads(line)
        by_block.setdefault(r["block"], set()).add(r["tx"])
        tx_payer[r["tx"]] = r["authorizer"]
    blocks = sorted(by_block)
    print(f"settlement-bearing blocks in window: {len(blocks):,}", flush=True)

    random.seed(402)
    sample = sorted(random.sample(blocks, min(n_blocks, len(blocks))))

    submitters = Counter()
    sub_payers = {}
    seen = 0
    for i, b in enumerate(sample):
        blk = rpc("eth_getBlockByNumber", [hex(b), True])
        want = by_block[b]
        for t in blk.get("transactions", []):
            if t["hash"] in want:
                s = t["from"].lower()
                submitters[s] += 1
                sub_payers.setdefault(s, set()).add(tx_payer[t["hash"]])
                seen += 1
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(sample)} blocks, {seen} settlements", flush=True)

    tot = sum(submitters.values())
    rows = []
    for addr, k in submitters.most_common():
        rows.append({"submitter": addr, "settlements": k,
                     "share": round(100 * k / tot, 2),
                     "distinct_payers_served": len(sub_payers[addr])})
    out = {"window": win, "sampled_blocks": len(sample),
           "settlements_in_sample": tot,
           "distinct_submitters": len(submitters),
           "top10_share": round(100 * sum(k for _, k in submitters.most_common(10)) / tot, 2),
           "submitters": rows[:60]}
    json.dump(out, open(OUT, "w"), indent=1)

    print(f"\nsampled {len(sample)} blocks -> {tot:,} settlements")
    print(f"distinct submitters (facilitator relayers): {len(submitters)}")
    print(f"top-10 submitter share: {out['top10_share']}%")
    print("\ntop submitters:")
    for r in rows[:12]:
        print(f"  {r['submitter']}  {r['settlements']:>6}  {r['share']:>5}%  "
              f"serving {r['distinct_payers_served']} payers")


if __name__ == "__main__":
    main()
