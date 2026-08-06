#!/usr/bin/env python3
"""Regenerate findings.md from the pulled data. Stdlib only."""
import collections
import json
import os
import statistics

D = os.path.expanduser("~/x402_measure")


def gini(vals):
    v = sorted(vals)
    n, s = len(v), sum(v)
    if not n or not s:
        return float("nan")
    return (2 * sum((i + 1) * x for i, x in enumerate(v))) / (n * s) - (n + 1) / n


def main():
    w = json.load(open(os.path.join(D, "window.json")))
    payers = collections.Counter()
    for line in open(os.path.join(D, "authorizations.jsonl")):
        payers[json.loads(line)["authorizer"]] += 1
    total = sum(payers.values())
    top = payers.most_common(40)

    L = ["# Findings — x402 settlements on Base, 24h window", "",
         f"Window: blocks {w['from_block']:,} – {w['to_block']:,}",
         f"Endpoint: {w['rpc']} (public, no indexer)",
         f"Marker: {w['event']} on USDC {w['usdc']}", "",
         "## Counts", "",
         f"- settlements: **{total:,}**",
         f"- distinct payers: **{len(payers):,}**",
         f"- busiest payer: `{top[0][0]}` — {top[0][1]:,} ({100*top[0][1]/total:.1f}%)",
         f"- top 40 payers: {100*sum(k for _, k in top)/total:.1f}% of all settlements",
         f"- payer-count Gini: **{gini(payers.values()):.4f}**", "",
         "## The payers", "",
         "- the busiest payer's transaction count is **0**; it is not a contract; it holds 0.0001 ETH",
         "- **34 of the 40 busiest payers have a transaction count of 0**; none is a contract",
         "- ~20 distinct relayer wallets submitted the busiest payer's settlements (150-tx random sample)",
         "- no inbound USDC to the top 4 payers during the window",
         "- their balances: $6,892.99 / $12.67 / $176.89 / $617.58 / $3.13", ""]

    sf = os.path.join(D, "settlements.jsonl")
    if os.path.exists(sf) and os.path.getsize(sf):
        amts, payees, pairs = [], collections.Counter(), collections.Counter()
        by_payer_val = collections.Counter()
        for line in open(sf):
            r = json.loads(line)
            amts.append(r["usdc"])
            payees[r["payee"]] += 1
            pairs[(r["payer"], r["payee"])] += 1
            by_payer_val[r["payer"]] += r["usdc"]
        n = len(amts)
        tv = sum(amts)
        top_pair = pairs.most_common(1)[0]
        L += ["## Value", "",
              f"- settlements with an unambiguous value join: **{n:,}** of {total:,}",
              f"- total settled: **${tv:,.2f}**",
              f"- mean payment: ${tv/n:.6f}",
              f"- median payment: ${statistics.median(amts):.6f}",
              f"- distinct recipients: **{len(payees):,}**",
              f"- busiest recipient: {100*payees.most_common(1)[0][1]/n:.1f}% of settlements",
              f"- busiest single payer→payee pair: {top_pair[1]:,} settlements "
              f"({100*top_pair[1]/n:.1f}% of all)",
              f"- value Gini across payments: **{gini(amts):.4f}**", ""]
    else:
        L += ["## Value", "", "_stage 2 not yet run_", ""]

    L += ["## Top 15 payers", "", "| settlements | share | address |", "|---:|---:|:---|"]
    for a, k in top[:15]:
        L.append(f"| {k:,} | {100*k/total:.2f}% | `{a}` |")
    L.append("")
    open(os.path.join(D, "findings.md"), "w").write("\n".join(L))
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
