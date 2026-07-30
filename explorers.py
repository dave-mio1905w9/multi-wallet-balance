import httpx

# TODO: support batch RPC requests for eth to speed up multi-address queries

async def get_btc_balance(client: httpx.AsyncClient, address: str) -> float:
    """Fetch Bitcoin balance in BTC using blockstream.info with mempool.space fallback."""
    urls = [
        f"https://blockstream.info/api/address/{address}",
        f"https://mempool.space/api/address/{address}"
    ]
    
    last_err = None
    for url in urls:
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            
            chain_stats = data.get("chain_stats", {})
            mempool_stats = data.get("mempool_stats", {})
            
            funded = chain_stats.get("funded_txo_sum", 0) + mempool_stats.get("funded_txo_sum", 0)
            spent = chain_stats.get("spent_txo_sum", 0) + mempool_stats.get("spent_txo_sum", 0)
            
            satoshis = funded - spent
            return satoshis / 100_000_000.0
        except (httpx.HTTPError, ValueError) as e:
            last_err = e
            continue
            
    raise last_err or Exception("Failed to query bitcoin APIs")

async def get_eth_balance(client: httpx.AsyncClient, rpc_url: str, address: str) -> float:
    """Query EVM compatible chains using eth_getBalance JSON-RPC."""
    clean_addr = address.strip()
    if not clean_addr.startswith("0x"):
        clean_addr = f"0x{clean_addr}"
        
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [clean_addr, "latest"],
        "id": 1
    }
    resp = await client.post(rpc_url, json=payload, timeout=12.0)
    resp.raise_for_status()
    result = resp.json()
    
    # print(f"DEBUG eth response: {result}")
    if "error" in result:
        raise ValueError(f"RPC Error: {result['error'].get('message')}")
        
    hex_val = result["result"]
    wei = int(hex_val, 16)
    return wei / 10**18

async def get_sol_balance(client: httpx.AsyncClient, node_endpoint: str, address_str: str) -> float:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address_str.strip()]
    }
    headers = {"Content-Type": "application/json"}
    resp = await client.post(node_endpoint, json=payload, headers=headers, timeout=12.0)
    resp.raise_for_status()
    result = resp.json()
    
    if "error" in result:
        raise ValueError(f"RPC Error: {result['error'].get('message')}")
        
    lamports = result["result"]["value"]
    return lamports / 1_000_000_000.0
