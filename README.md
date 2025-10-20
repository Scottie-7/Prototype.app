# Prototype.app

Streamlit-based stock monitoring dashboard for tracking live market data, charts, order books, alerts, and news from a single page.

## Prerequisites
- Python 3.11+
- Recommended: virtual environment (``python -m venv .venv``)

## Installation
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   The same dependency list is also defined in `Mason/pyproject.toml`, so `pip install .` works if you prefer editable installs.

## Running the app
Launch the Streamlit dashboard from the repository root:
```bash
streamlit run Mason/app.py
```

If you prefer (for example, inside Codespaces where the `Run` button executes a Python file), you can invoke the script directly thanks to the embedded bootstrapper:
```bash
python Mason/app.py
```
Both commands require the dependencies from `requirements.txt` to be installed first.

## Optional configuration
Set the following environment variables before launching the app if you want email/SMS notifications to work:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `SENDGRID_API_KEY`

## Quick validation
To confirm the source files compile:
```bash
python -m py_compile Mason/app.py
```
