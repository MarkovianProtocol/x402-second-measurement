# Findings — x402 settlements on Base, 24h window

Window: blocks 49,556,153 – 49,599,353
Endpoint: https://mainnet.base.org (public, no indexer)
Marker: AuthorizationUsed on USDC 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913

## Counts

- settlements: **234,490**
- distinct payers: **3,704**
- busiest payer: `0x2b4ee3387008e5ff1a9996fc8b48d2fd61389037` — 133,528 (56.9%)
- top 40 payers: 77.6% of all settlements
- payer-count Gini: **0.9509**

## The payers

- the busiest payer's transaction count is **0**; it is not a contract; it holds 0.0001 ETH
- **34 of the 40 busiest payers have a transaction count of 0**; none is a contract
- ~20 distinct relayer wallets submitted the busiest payer's settlements (150-tx random sample)
- no inbound USDC to the top 4 payers during the window
- their balances: $6,892.99 / $12.67 / $176.89 / $617.58 / $3.13

## Value

- settlements with an unambiguous value join: **200,530** of 234,490
- total settled: **$558,695.15**
- mean payment: $2.786093
- median payment: $0.014997
- distinct recipients: **1,521**
- busiest recipient: 67.0% of settlements
- busiest single payer→payee pair: 133,527 settlements (66.6% of all)
- value Gini across payments: **0.9957**

## Top 15 payers

| settlements | share | address |
|---:|---:|:---|
| 133,528 | 56.94% | `0x2b4ee3387008e5ff1a9996fc8b48d2fd61389037` |
| 6,523 | 2.78% | `0x391bf5a6bd0cf464e6b90021f130d874d7d1ef00` |
| 5,140 | 2.19% | `0x8f9ac214e8b6f2e2b0dfe7ef6597e6072da2f394` |
| 4,353 | 1.86% | `0xa39c469c59270f5403b4641131b89bfe2459889f` |
| 2,557 | 1.09% | `0x0f862ad60d515c635b53c2cd49e6396baf1afa8a` |
| 2,400 | 1.02% | `0x519212a752e23cfa50d3d8955a9dd4aec500cda0` |
| 2,303 | 0.98% | `0xbcced9a3738108a9a71a273297bbb934df9246e7` |
| 2,301 | 0.98% | `0xd8268d399521b583451ce14be498b9659cebc50b` |
| 2,197 | 0.94% | `0x8a38a79aa89f832c55a124ce8ff0205443fb8c5a` |
| 1,976 | 0.84% | `0xc609a2e2a929874fc55b8033d94d0f5595980918` |
| 1,869 | 0.80% | `0xcfa370b01125f985ca1be78bfda9fd790b3da8dc` |
| 1,400 | 0.60% | `0xe59f62e39a79284f1e63da29d9ec2c129c37b2fa` |
| 1,344 | 0.57% | `0x28c3f67102e74f03e42182d34f0ca3ef7d54c305` |
| 1,161 | 0.50% | `0xa642526f6ced234c60ed6ee9e820436936f82ebc` |
| 1,115 | 0.48% | `0x92755a29632489087c8390972d5f9c0cc4ab1c55` |
