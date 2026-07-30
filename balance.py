import asyncio
import argparse
import sys
from pathlib import Path
import httpx

from multi_wallet_balance.explorers import (
    fetch_evm_balance,
    fetch_sol_balance,
    fetch_btc_balance,
    fetch_usd_prices,
)

def detect_chain(address: str) -> str:
    """Identify chain type based on address string heuristics."""
    # Some solana addresses can start with numbers or capitals, length check is safest
    # without pulling in base58 decoding directly.
    cleaned = address.strip()
    if cleaned.startswith("0x") and len(cleaned) == 42:
        return "evm"
    elif len(cleaned) >= 32 and len(cleaned) <= 44 and not cleaned.startswith("bc1"):
        return "sol"
    elif cleaned.startswith("1") or cleaned.startswith("3") or cleaned.startswith("bc1"):
        return "btc"
    return "unknown"

async def fetch_worker(address: str, chain: str) -> tuple[str, str, float | None]:
    # TODO: add fallback public RPCs if default rate limits us too hard
    try:
        if chain == "evm":
            val = await fetch_evm_balance(address)
        elif chain == "sol":
            val = await fetch_sol_balance(address)
        elif chain == "btc":
            val = await fetch_btc_balance(address)
        else:
            val = None
        
        # print(f"[DEBUG] Raw balance returned for {address}: {val}")
        return address, chain, val
    except httpx.HTTPError as he:
        # Let the higher-level formatter deal with missing balances
        return address, chain, None
    except ValueError:
        return address, chain, None

async def process_balances(addresses: list[str]):
    # Fetch fiat conversion rates and address balances concurrently
    price_task = asyncio.create_task(fetch_usd_prices())
    
    tasks = []
    for addr in addresses:
        chain = detect_chain(addr)
        tasks.append(fetch_worker(addr, chain))
    
    results = await asyncio.gather(*tasks)
    
    try:
        coinPrices = await price_task
    except Exception:
        # If pricing lookup fails, we still want to output the balances
        coinPrices = {"ethereum": 0.0, "solana": 0.0, "bitcoin": 0.0}

    # Assemble the results and print a clean CLI layout
    print("\n" + "=" * 85)
    print(f"{'CHAIN'.ljust(8)}{'ADDRESS'.ljust(48)}{'BALANCE'.rjust(14)}   {'VALUE (USD)'.rjust(10)}")
    print("-" * 85)

    total_value = 0.0
    pricing_failed = all(v == 0.0 for v in coinPrices.values())

    # Leftover naming inconsistency from old helper loop
    retriesLimit = 3

    for addr, chain, balance in results:
        chain_label = chain.upper().ljust(8)
        truncated_addr = (addr[:45] + "...") if len(addr) > 45 else addr
        addr_label = truncated_addr.ljust(48)

        if balance is None:
            print(f"{chain_label}{addr_label}{'ERROR'.rjust(14)}   {'--'.rjust(10)}")
            continue

        balance_str = f"{balance:.6f}"
        if balance_str.endswith(".000000"):
            balance_str = f"{balance:.2f}"
        
        # Map chain to price key
        price_key = {"evm": "ethereum", "sol": "solana", "btc": "bitcoin"}.get(chain)
        price = coinPrices.get(price_key, 0.0) if price_key else 0.0
        
        usd_val = balance * price
        total_value += usd_val

        usd_str = f"${usd_val:,.2f}" if (price > 0 and not pricing_failed) else "--"
        print(f"{chain_label}{addr_label}{balance_str.rjust(14)}   {usd_str.rjust(10)}")

    print("=" * 85)
    if not pricing_failed:
        print(f"{'TOTAL PORTFOLIO VALUE:'.rjust(56)}   ${total_value:,.2f}".rjust(82))
    else:
        print("Pricing feed currently unavailable; displaying raw token balances only.")
    print()

def main():
    parser = argparse.ArgumentParser(
        description="Fast, concurrent balance checker for EVM, Solana, and Bitcoin addresses.",
        epilog="Example: multi-wallet-balance 0x... bc1... -f addresses.txt"
    )
    parser.add_argument(
        "addresses",
        nargs="*",
        help="Space-separated list of addresses to check directly from the CLI."
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Path to a file containing one address per line. Comments starting with '#' are ignored."
    )

    args = parser.parse_args()
    
    target_addresses = []
    if args.addresses:
        target_addresses.extend(args.addresses)

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: Input file '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        target_addresses.append(line)
        except (IOError, UnicodeDecodeError) as err:
            print(f"Error: Unable to read file '{args.file}': {err}", file=sys.stderr)
            sys.exit(1)

    if not target_addresses:
        parser.print_help()
        sys.exit(0)

    try:
        asyncio.run(process_balances(target_addresses))
    except KeyboardInterrupt:
        print("\nScan aborted by user.")
        sys.exit(130)

if __name__ == "__main__":
    main()
