# x402 second measurement

An independent re-measurement of one day of x402 settlement activity on Base,
run without an indexer and without the original authors' data, to check whether
an outsider with a public RPC endpoint arrives where they arrived.

The claim being checked is [arXiv 2607.12575](https://arxiv.org/abs/2607.12575),
"How Agentic Is Agentic Commerce? A Population-Scale Measurement of x402 Adoption
and Authenticity" (Ling, Zhou, Wu, Wang, July 2026): 136.7M settlements worth
$44.1M over 280 days, of which 21.2% fictitious and 63.78% internal to linked
clusters, with concentration Gini above 0.98 and most activity attributable to a
single gas-subsidized operator.

Their measurement is longer, broader, and more careful than this one. This
repository is a second measurement, not a replacement for the first.

## Method

x402 settles as an EIP-3009 `transferWithAuthorization` call on USDC. That call
emits `AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce)`,
topic0 `0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5`.
Counting those events over a block range counts settlements directly from chain
state, with no indexer in the path.

- Chain: Base mainnet, USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`
- Endpoint: the public `https://mainnet.base.org`
- Window: blocks **49,556,153 – 49,599,353** (24 hours, ending 2026-08-05)
- Stage 1 (`x402_pull.py`): page `eth_getLogs` for `AuthorizationUsed`, bisecting
  ranges the endpoint refuses as too dense; record block, tx, authorizer.
- Stage 2 (`x402_values.py`): pull USDC `Transfer` logs over the same window and
  join by transaction hash to attach payee and amount. A join is accepted only
  when the transaction's transfer count equals its authorization count and the
  transfer's `from` equals the authorizer. Anything else is counted as ambiguous
  and excluded from value totals rather than guessed.

Both stages are stdlib-only Python and take a block window, so the same numbers
are reproducible from the same blocks by anyone.

## Findings

See `findings.md` for the generated numbers and `window.json` for the exact
window and timestamps.

Headline: in this window there were **234,490 settlements from 3,704 distinct
payers**, of which a single address accounted for **56.9%**. That address, and
**34 of the 40 busiest payers — together 77.6% of all settlement — have a
transaction count of zero.** They have never sent a transaction. None of them is
a contract. They are keys that sign authorizations off-chain while other wallets
submit the transactions and pay the gas.

On value: 200,530 settlements joined unambiguously to an amount, totalling
**$558,695.15**, with a **median payment of $0.0149** and a value Gini of 0.9957.
A **single payer→payee pair accounted for 133,527 settlements — 66.6% of the
entire market** in the window.

## What this does and does not show

It shows counts, concentration, and the mechanical shape of the traffic in one
24-hour window, computed from chain state.

It does not reproduce the original paper's clustering analysis, does not
establish intent, and does not show that any particular payment is fictitious.
"Fictitious" and "internal to linked clusters" are the authors' findings under
their methodology over 280 days; nothing here extends or contradicts them. A key
with a zero nonce is not evidence of wrongdoing — gasless relayed transfer is a
legitimate and intended use of EIP-3009. What the zero nonce establishes is
narrower: the busiest participants in this market are not programs transacting
on their own behalf.

## Reproducing

    python3 x402_pull.py 24        # stage 1, writes authorizations.jsonl + window.json
    python3 x402_values.py         # stage 2, writes settlements.jsonl
    python3 analyze.py             # regenerates findings.md

To replay a fixed block window instead of the last 24 hours, and keep each run in its own folder:

    X402_DIR=./run-aug05 python3 x402_pull.py - 49556153 49599353

To check the single most load-bearing fact without running anything, ask any
block explorer or RPC endpoint for the transaction count of
`0x2b4ee3387008e5ff1a9996fc8b48d2fd61389037`.

Apache-2.0.

## Part two: who actually operates the settlements

A second paper, [arXiv 2607.19545](https://arxiv.org/abs/2607.19545) ("When HTTP 402
Meets the Blockchain", Wang, Yang, Chen, Ji, Payer, 21 July 2026), studies 15 x402
facilitators and treats facilitator centralization as a core risk. We checked the
centralization question against the same 24-hour window, from a different angle.

A facilitator, measured on-chain, is whoever submits the settlement transaction and
pays its gas — that is `tx.from`. Sampling 400 of the window's blocks (2,213
settlements) gives **77 distinct submitter addresses**, which looks like a broad
field.

It isn't. Two independent tests collapse it:

**Co-service graph** (`x402_components.py`). Treat submitters and payers as a
bipartite graph and take connected components: 77 submitters resolve to 36
components, and the largest — 23 submitters serving 164 payers — carries **81.4%**
of sampled settlements. This method over-merges by construction: one payer using two
independent facilitators fuses them. `x402_components2.py` measures how badly, and
the answer is "enough to matter" — median pairwise payer-set overlap between
submitters in the giant component is only 0.206, with no pair above 0.5. Treat the
81.4% as an upper bound from this method alone.

**Fleet fingerprint** (`x402_fleet.py`). Independent operators accumulate
transactions at their own pace; wallets driven by one system march in step. Lifetime
transaction counts of the observed submitters cluster hard:

| wallets | lifetime tx counts | spread | share of sampled settlements |
|---:|:---|---:|---:|
| 15 | 1,092,034 – 1,094,993 | 0.27% | 61.2% |
| 5 | 2,843,527 – 2,853,016 | 0.33% | 19.3% |
| 10 | 9,034 – 9,045 | 0.12% | 0.5% |

Fifteen addresses do not independently arrive within 0.27% of each other after a
million transactions apiece. **Two pools account for 80.5% of settlement**, and 30 of
the 77 visible submitters resolve to three operators. This test shares no assumptions
with the graph method, and the two agree.

### Limits

Nonce proximity shows wallets driven in lockstep by one controller; it does not
identify who that controller is, and does not imply wrongdoing — running a hot-wallet
pool is ordinary infrastructure practice for a payment facilitator. The sample is 400
of 43,200 blocks (about 1%), which is adequate for shares and not for absolute counts.
We did not attempt any part of the paper's security analysis: their eight
authorization rules and four attack vectors come from black-box testing of live
facilitators, which we have neither replicated nor verified.
