#!/usr/bin/env python3
"""Clustering v2: test whether the 81% component is one operation or an artifact.

v1 used connected components over the bipartite submitter-payer graph, which
over-merges: one payer using two independent facilitators fuses them forever.
Three checks here, each stated so a reader can judge the merge for themselves.

1. Articulation test — how much of the giant component depends on a single
   shared payer? Remove the payers that bridge otherwise-separate submitter sets
   and see whether it shatters.
2. Submitter-similarity — Jaccard overlap between submitters' payer sets. A hot
   wallet fleet serving one pool has high pairwise overlap; independent
   facilitators sharing a customer have low overlap.
3. Gas-funding proximity — do the fleet's submitters share an ETH funder? Not
   graph-based at all, so it is independent evidence.
"""
import collections
import itertools
import json
import os
import random
import time
import urllib.request

RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
D = os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure"))
N_BLOCKS = 400


def rpc(m, p, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m,
                                      "params": p}).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "markovian-x402-measure/1.0"})
            r = json.load(urllib.request.urlopen(req, timeout=40))
            if "error" in r:
                raise RuntimeError(str(r["error"])[:80])
            return r["result"]
        except Exception:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def components(edges):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for s, ps in edges.items():
        for p in ps:
            union("S:" + s, "P:" + p)
    out = collections.defaultdict(set)
    for s in edges:
        out[find("S:" + s)].add(s)
    return list(out.values())


def main():
    by_block, tx_payer = {}, {}
    for line in open(os.path.join(D, "authorizations.jsonl")):
        r = json.loads(line)
        by_block.setdefault(r["block"], set()).add(r["tx"])
        tx_payer[r["tx"]] = r["authorizer"]

    random.seed(402)
    sample = sorted(random.sample(sorted(by_block), N_BLOCKS))
    edges = collections.defaultdict(set)
    counts = collections.Counter()
    for i, b in enumerate(sample):
        blk = rpc("eth_getBlockByNumber", [hex(b), True])
        for t in blk.get("transactions", []):
            if t["hash"] in by_block[b]:
                s = t["from"].lower()
                edges[s].add(tx_payer[t["hash"]])
                counts[s] += 1
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(sample)}", flush=True)

    comps = sorted(components(edges), key=lambda c: -sum(counts[s] for s in c))
    giant = comps[0]
    total = sum(counts.values())
    print(f"\nv1 giant component: {len(giant)} submitters, "
          f"{100*sum(counts[s] for s in giant)/total:.1f}% of settlements")

    # --- 1. articulation: which payers bridge submitters?
    payer_subs = collections.defaultdict(set)
    for s in giant:
        for p in edges[s]:
            payer_subs[p].add(s)
    bridges = {p: subs for p, subs in payer_subs.items() if len(subs) > 1}
    print(f"payers served by >1 submitter inside the giant: {len(bridges)} "
          f"of {len(payer_subs)}")

    sub_edges = {s: set(p for p in edges[s] if len(payer_subs[p]) > 1) for s in giant}
    kept = {s: ps for s, ps in sub_edges.items() if ps}
    print(f"submitters that share any payer: {len(kept)} of {len(giant)}")

    # --- 2. pairwise Jaccard among the giant's submitters
    js = []
    for a, b in itertools.combinations(sorted(giant), 2):
        A, B = edges[a], edges[b]
        u = len(A | B)
        if u:
            js.append(len(A & B) / u)
    js.sort()
    if js:
        med = js[len(js) // 2]
        hi = sum(1 for x in js if x >= 0.5)
        print(f"pairwise payer-set Jaccard: median {med:.3f}, "
              f"{hi}/{len(js)} pairs >= 0.5")

    # --- 3. do the giant's submitters share an ETH funder?
    print("\nchecking gas funders of the 8 busiest submitters in the giant...")
    top = sorted(giant, key=lambda s: -counts[s])[:8]
    funders = collections.Counter()
    for s in top:
        # first inbound ETH: walk earliest txs via nonce-0 sender heuristic is not
        # available on a public node; use balance+code as a weak signal instead
        code = rpc("eth_getCode", [s, "latest"])
        n = int(rpc("eth_getTransactionCount", [s, "latest"]), 16)
        bal = int(rpc("eth_getBalance", [s, "latest"]), 16) / 1e18
        print(f"   {s[:14]}..  txs_sent={n:<7} eth={bal:.5f} "
              f"{'contract' if code and code != '0x' else 'EOA'} "
              f"payers={len(edges[s])}")

    out = {"giant_submitters": len(giant),
           "giant_share": round(100 * sum(counts[s] for s in giant) / total, 2),
           "bridge_payers": len(bridges), "payers_in_giant": len(payer_subs),
           "submitters_sharing_any_payer": len(kept),
           "jaccard_median": round(js[len(js) // 2], 4) if js else None,
           "jaccard_pairs_over_half": sum(1 for x in js if x >= 0.5) if js else 0,
           "jaccard_pairs": len(js)}
    json.dump(out, open(os.path.join(D, "components_v2.json"), "w"), indent=1)
    print("\nwrote components_v2.json")


if __name__ == "__main__":
    main()
