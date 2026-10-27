# Personalized Travel Itinerary Planner
**Skill Wallet Capstone Project 4** — Streamlit travel-planning SaaS prototype.

## Features
- Destination and travel-preference form (vibe, duration, dates, budget, party, pace, interests).
- Destination shortlist based on a demo catalogue, budget fit, and a simple season heuristic.
- Day-by-day itinerary with four sequential time slots, itemized activity estimates, USD/INR conversions, and optional local currencies.
- Lightweight nearest-neighbor geographic ordering when coordinates are available.
- Slot-level swaps and single-day refresh without replacing the rest of the itinerary.
- Session-based trip library and offline PDF export with an emergency-readiness checklist.
- Gemini and Groq API support, with a built-in demo mode.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in the terminal (usually `http://localhost:8501`).

## AI setup
1. Select Gemini or Groq in the sidebar.
2. Turn Demo mode off.
3. Paste an API key into the password field, or set a server-side environment variable:
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`

For Streamlit Community Cloud, add secrets in **App → Settings → Secrets**, for example:

```toml
GEMINI_API_KEY = "your-key-here"
# or
GROQ_API_KEY = "your-key-here"
```

Do not commit real keys to GitHub. The app uses a password field for manually entered keys and does not write them to disk.

## Deploy to Streamlit Community Cloud
1. Create a GitHub repository and upload `app.py`, `requirements.txt`, and `README.md`.
2. In Streamlit Community Cloud, choose the repository and set the main file path to `app.py`.
3. Add your API key through Streamlit Secrets if you want AI mode.
4. Deploy. Demo mode works without an API key.

## Important scope notes
- **Persistence:** saved trips live in Streamlit `session_state`. This avoids an external database dependency, but the history is not durable across restarts/new sessions. It is a prototype of persistence, not cross-user production storage.
- **Geographic optimization:** nearest-neighbor ordering is a lightweight heuristic, not a routing API. It cannot account for traffic, closures, public transit schedules, or road networks.
- **Prices and travel advice:** demo prices, destination data, and recommendations are illustrative and are not live quotes, opening hours, booking inventory, or live weather forecasts. Always verify independently.
- **Currency:** conversion factors are configurable sample rates, not live FX. Update `CURRENCIES` or connect a current exchange-rate provider if live conversion is required.
- **AI response quality:** output is validated and falls back to demo content if the provider errors or returns an unexpected shape.
- **Emergency checklist:** the PDF includes fill-in fields; it does not claim to know local emergency numbers.

## Suggested next steps for a production deployment
- Add tests for itinerary schema normalization and PDF generation.
- Add a routing provider for travel-time-aware ordering.
- Use a persistent database with user authentication for cross-session history.
- Use live exchange rates, weather, destination data, and official travel advisories.
- Add accessibility, dietary/allergy, and travel-document fields.
