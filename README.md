# check_vestings

Fetch current backer vesting status directly from the Safe VestingPool
contract on Ethereum mainnet.

This script:

-   Downloads the `investor_vestings.csv` from the Safe
    claiming-app-data repository (or uses a local CSV)
-   Calls the `vestings(bytes32)` function on the VestingPool contract\
-   Uses Infura (or custom RPC) for on-chain reads
-   Outputs a CSV containing:

```
    owner
    vestingId
    account
    amount
    amountClaimed
```

------------------------------------------------------------------------

## Contract Details

-   **Contract:** `0x96b71e2551915d98d22c448b040a3bc4801ea4ff`
-   **Network:** Ethereum Mainnet
-   **Function called:** `vestings(bytes32)`

------------------------------------------------------------------------

## Requirements

-   Python **3.11 or 3.12** recommended
-   Infura API key (or custom RPC endpoint)

------------------------------------------------------------------------

## Installation

### 1️⃣ Create virtual environment

``` bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2️⃣ Install dependencies

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Configuration

You can provide your Infura key either:

### Option A -- Environment variable (recommended)

``` bash
export INFURA_API_KEY="YOUR_INFURA_KEY"
```

### Option B -- CLI argument

``` bash
--infura-key YOUR_INFURA_KEY
```

### Option C -- Custom RPC

``` bash
--rpc-url https://mainnet.infura.io/v3/YOUR_KEY
```

------------------------------------------------------------------------

## Usage

### Default (uses Safe repo CSV)

``` bash
python check_vestings.py --output vestings_out.csv
```

### With explicit Infura key

``` bash
python check_vestings.py \
  --infura-key YOUR_KEY \
  --output vestings_out.csv
```

### With custom input CSV

``` bash
python check_vestings.py \
  --input ./investor_vestings.csv \
  --output vestings_out.csv
```

### Disable progress bar

``` bash
python check_vestings.py --no-progress
```

------------------------------------------------------------------------

## Output

The script writes a CSV file (default: `vestings_out.csv`) containing:

  Column          Description
  --------------- --------------------------------------
  owner           Owner address from input CSV
  vestingId       Vesting ID (bytes32)
  account         Account stored in contract
  amount          Total vested amount (raw uint128)
  amountClaimed   Already claimed amount (raw uint128)

If any on-chain call fails, an additional `error` column will appear for
affected rows.

------------------------------------------------------------------------

## Notes

-   All contract calls are **read-only**
-   The script processes rows sequentially
-   Runtime depends on RPC latency
-   If installation hangs on `Preparing metadata (pyproject.toml)`, use
    Python 3.11

------------------------------------------------------------------------

## License

This project is licensed under the **GNU General Public License (GPL)**.

See the `LICENSE` file for details.
