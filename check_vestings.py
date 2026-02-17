import argparse
import os
import sys
from typing import Any, Dict

import pandas as pd
import requests
from tqdm import tqdm
from web3 import Web3

DEFAULT_INPUT_CSV_URL = (
    "https://raw.githubusercontent.com/safe-global/claiming-app-data/"
    "9fbbe2b90a4ca635a0883dd5cb45493695c70c3b/vestings/assets/1/investor_vestings.csv"
)

VESTING_POOL_ADDRESS = "0x96b71e2551915d98d22c448b040a3bc4801ea4ff"

# Minimal ABI for the auto-generated getter of:
#   mapping(bytes32 => Vesting) public vestings;
# Vesting struct fields (in order) come from the verified source on Etherscan.
VESTINGS_GETTER_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "vestings",
        "outputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "uint8", "name": "curveType", "type": "uint8"},
            {"internalType": "bool", "name": "managed", "type": "bool"},
            {"internalType": "uint16", "name": "durationWeeks", "type": "uint16"},
            {"internalType": "uint64", "name": "startDate", "type": "uint64"},
            {"internalType": "uint128", "name": "amount", "type": "uint128"},
            {"internalType": "uint128", "name": "amountClaimed", "type": "uint128"},
            {"internalType": "uint64", "name": "pausingDate", "type": "uint64"},
            {"internalType": "bool", "name": "cancelled", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


def bytes32_from_any(v: Any) -> bytes:
    """
    Accept common representations:
      - '0x' + 64 hex chars (preferred)
      - 64 hex chars (no 0x)
      - bytes-like already length 32
    """
    if isinstance(v, (bytes, bytearray)):
        b = bytes(v)
        if len(b) != 32:
            raise ValueError(f"Expected 32 bytes, got {len(b)}")
        return b

    s = str(v).strip()
    if s.startswith("0x"):
        s_hex = s[2:]
    else:
        s_hex = s

    if len(s_hex) != 64:
        raise ValueError(f"vestingId must be 32 bytes hex (64 chars). Got len={len(s_hex)} value={s}")

    try:
        return bytes.fromhex(s_hex)
    except ValueError as e:
        raise ValueError(f"Invalid hex in vestingId: {s}") from e


def load_input_csv(path_or_url: str) -> pd.DataFrame:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        r = requests.get(path_or_url, timeout=60)
        r.raise_for_status()
        # Let pandas parse from bytes
        from io import BytesIO

        return pd.read_csv(BytesIO(r.content))
    return pd.read_csv(path_or_url)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch VestingPool vestings() results for each row in a CSV.")
    ap.add_argument("--input", default=DEFAULT_INPUT_CSV_URL, help="Input CSV path or URL.")
    ap.add_argument("--output", default="vestings_out.csv", help="Output CSV path.")
    ap.add_argument(
        "--infura-key",
        default=os.getenv("INFURA_API_KEY", ""),
        help="Infura API key (or set env INFURA_API_KEY).",
    )
    ap.add_argument(
        "--rpc-url",
        default="",
        help="Override RPC URL (if set, takes precedence over Infura key).",
    )
    ap.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar.",
    )

    args = ap.parse_args()

    if args.rpc_url:
        rpc_url = args.rpc_url
    else:
        if not args.infura_key:
            print("ERROR: Provide --infura-key or set INFURA_API_KEY, or pass --rpc-url.", file=sys.stderr)
            return 2
        rpc_url = f"https://mainnet.infura.io/v3/{args.infura_key}"

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        print(f"ERROR: Could not connect to RPC: {rpc_url}", file=sys.stderr)
        return 3

    df = load_input_csv(args.input)

    # Expect at least these columns
    for col in ("owner", "vestingId"):
        if col not in df.columns:
            print(f"ERROR: Input CSV missing required column '{col}'. Columns: {list(df.columns)}", file=sys.stderr)
            return 4

    contract = w3.eth.contract(address=Web3.to_checksum_address(VESTING_POOL_ADDRESS), abi=VESTINGS_GETTER_ABI)

    rows: list[Dict[str, Any]] = []
    it = df.itertuples(index=False)
    if not args.no_progress:
        it = tqdm(list(it), desc="Calling vestings()", unit="row")

    for row in it:
        owner = getattr(row, "owner")
        vestingId_raw = getattr(row, "vestingId")

        try:
            vestingId_b32 = bytes32_from_any(vestingId_raw)
            result = contract.functions.vestings(vestingId_b32).call()

            # result matches outputs order in ABI
            account = result[0]
            amount = int(result[5])
            amount_claimed = int(result[6])

            rows.append(
                {
                    "owner": owner,
                    "vestingId": str(vestingId_raw),
                    "account": account,
                    "amount": amount,
                    "amountClaimed": amount_claimed,
                }
            )
        except Exception as e:
            # Keep going, but record failure
            rows.append(
                {
                    "owner": owner,
                    "vestingId": str(vestingId_raw),
                    "account": "",
                    "amount": "",
                    "amountClaimed": "",
                    "error": repr(e),
                }
            )

    out_df = pd.DataFrame(rows)

    # Ensure requested columns are first; include error column if present
    base_cols = ["owner", "vestingId", "account", "amount", "amountClaimed"]
    extra_cols = [c for c in out_df.columns if c not in base_cols]
    out_df = out_df[base_cols + extra_cols]

    out_df.to_csv(args.output, index=False)
    print(f"Wrote {len(out_df)} rows to {args.output}")
    if "error" in out_df.columns:
        n_err = int(out_df["error"].notna().sum())
        if n_err:
            print(f"WARNING: {n_err} rows had errors (see 'error' column).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
