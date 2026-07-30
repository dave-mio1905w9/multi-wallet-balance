# multi-wallet-balance

I needed a simple, fast way to monitor my on-chain balances across different networks (EVM, Solana, Bitcoin) without opening heavy browser wallets or relying on third-party portfolio trackers that selling your data. 

This tool queries public RPC endpoints and APIs concurrently using `asyncio` and `httpx`. No heavy frameworks, no `web3.py` bloat, no configuration sprawl. It just takes a list of addresses (or a simple JSON config) and outputs a clean text table with fiat conversions.

## Installation

Clone the repository and install the single dependency:

```bash
pip install -r requirements.txt
```

## Usage

Create a `wallets.json` file to keep track of your addresses:

```json
[
  {"name": "main-eth", "chain": "eth", "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"},
  {"name": "sol-savings", "chain": "sol", "address": "HN7cABVi4LSebZfWvBv6f29Zvw6Jt7E1y5f7fX2kmR9D"},
  {"name": "btc-cold", "chain": "btc", "address": "3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5"}
]
```

Then run the tool:

```bash
python balance.py wallets.json
```

You can also query a single address directly from the command line:

```bash
python balance.py --chain eth 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
```

To see balances converted to EUR instead of USD:

```bash
python balance.py wallets.json --fiat EUR
```
