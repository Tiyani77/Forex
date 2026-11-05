# Forex Intelligence V3.3 — forward prediction tracking

This update retains the V3.2 dashboard, analysis, backtesting and historical leaderboard, and adds persistent forward prediction storage in Supabase.

## Installation
1. Replace `app.py` and `requirements.txt` in your GitHub repo. Add `prediction_store.py` at repository root.
2. In your **Supabase project**, open **SQL Editor**, paste and run `supabase_setup.sql`.
3. In Streamlit Cloud, go to your app **Manage app → Settings → Secrets** and set:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SERVICE_ROLE_KEY"
```

Use the URL and service role key from your **own** Supabase project settings. Never paste the key into chat, GitHub, source code or a screenshot. It bypasses row-level security; keep it strictly in Streamlit server secrets. If the app is public, consider implementing authentication and per-user access controls before enabling public prediction storage; this prototype shares one research history among all visitors and allows any visitor to save or trigger evaluations. Consider deploying privately for initial testing.

4. Redeploy. Open **Prediction History** and click **Save forward prediction**. Later click **Check and evaluate pending predictions** to retrieve new data and score predictions.

## Definitions and limitations
- A prediction is a **BUY**, **SELL**, or **WAIT** generated on the penultimate downloaded candle. It is stored with model version, timestamp, reference close and horizon.
- A prediction is evaluated against the close of the Nth later bar **only after that candle is no longer the latest available bar**. The target bar timestamp must also be later than the record creation time to prevent retroactive scoring.
- BUY is correct if later close > reference close; SELL if later close < reference close. WAIT is an abstention, excluded from directional accuracy.
- This is **not** trade execution, brokerage P&L, calibrated confidence, guaranteed profit or net return after trading costs.
- This version does **not** have a background scheduler. Users manually click to check outcomes. Yahoo Finance data can be delayed, incomplete, revised or unavailable. Old intraday records can expire from Yahoo history before evaluation; those remain pending.
- The backend uses a **service role key** and database RLS has no public policies. For a public multiuser product, implement user authentication, user-specific permissions, abuse limits, and a trusted scheduled worker before scaling.
