# Mock Alpha Vantage Setup

This note explains how to run the `Mock_AlphaVantage` server and point notebook API calls to a local base URL instead of the real Alpha Vantage endpoint.

## What This Is

`Mock_AlphaVantage` is a local drop-in replacement for a subset of Alpha Vantage endpoints. It is useful when the real API rate limit becomes a bottleneck during development or notebook testing.

The notebook code should use a configurable base URL:

```python
AV_BASE = os.getenv("ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co")
```

Then build requests like:

```python
requests.get(f"{AV_BASE}/query?function=OVERVIEW&symbol=AAPL&apikey=test")
```

## Local Setup

Clone the repo:

```bash
git clone https://github.com/Phemon/Mock_AlphaVantage.git
cd Mock_AlphaVantage
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
python av_mock_server.py
```

If it starts correctly, it should run on:

```text
http://localhost:2345
```

## Notebook Setup

Set the local base URL before defining tool functions:

```python
import os

os.environ["ALPHAVANTAGE_BASE_URL"] = "http://127.0.0.1:2345"
AV_BASE = os.getenv("ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co")
```

Then update Alpha Vantage-backed tools to use `AV_BASE` instead of the real site:

```python
def get_company_overview(ticker: str) -> dict:
    data = requests.get(
        f"{AV_BASE}/query?function=OVERVIEW&symbol={ticker}&apikey=test",
        timeout=10,
    ).json()
    return data
```

This same pattern applies to:

- `OVERVIEW`
- `MARKET_STATUS`
- `TOP_GAINERS_LOSERS`
- `NEWS_SENTIMENT`

## Quick Smoke Test

Use this to check that the server is responding:

```python
import requests

requests.get(
    "http://127.0.0.1:2345/query?function=OVERVIEW&symbol=AAPL&apikey=test",
    timeout=10,
).json()
```

If the server is running, the call should return JSON instead of a connection error.

## Optional Auto-Start Cell

This notebook cell starts the mock server automatically if port `2345` is not already open:

```python
import os, time, socket, subprocess

def port_open(host="127.0.0.1", port=2345):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

if not port_open():
    subprocess.Popen(
        ["../.venv/bin/python", "av_mock_server.py"],
        cwd="Mock_AlphaVantage",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)

os.environ["ALPHAVANTAGE_BASE_URL"] = "http://127.0.0.1:2345"
AV_BASE = os.getenv("ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co")
```

## Google Colab Setup

In Colab, start the mock server inside the same runtime:

```python
!git clone https://github.com/Phemon/Mock_AlphaVantage.git
%cd Mock_AlphaVantage
!pip install -q -r requirements.txt
```

Start the server in the background:

```python
import os, time, subprocess

mock_server = subprocess.Popen(
    ["python", "av_mock_server.py"],
    cwd="/content/Mock_AlphaVantage",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(3)

os.environ["ALPHAVANTAGE_BASE_URL"] = "http://127.0.0.1:2345"
AV_BASE = os.getenv("ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co")
```

Then verify the endpoint:

```python
import requests

requests.get(
    "http://127.0.0.1:2345/query?function=OVERVIEW&symbol=AAPL&apikey=test",
    timeout=10,
).json()
```

## Common Errors

`Connection refused`

- The mock server is not running.
- Start `python av_mock_server.py` and keep that process alive.

`Missing pe_ratio key`

- The tool likely returned an error dict instead of overview data.
- Print the raw response and check whether the mock server is reachable.

`No overview data`

- The mock server may be up, but its upstream lookup returned an empty result for that ticker.

## Summary

Use the mock server when you want Alpha Vantage-compatible local endpoints during development. The key idea is simple:

1. Run `av_mock_server.py`
2. Set `ALPHAVANTAGE_BASE_URL`
3. Route Alpha Vantage API calls through `AV_BASE`
