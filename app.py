import json
import math
import os
import re
from datetime import date, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether
)

APP_TITLE = "Personalized Travel Itinerary Planner"
APP_SUBTITLE = "A thoughtful trip, tailored to your kind of wonder."
CURRENCIES = {
    "INR": {"symbol": "₹", "per_usd": 83.5},
    "USD": {"symbol": "$", "per_usd": 1.0},
    "EUR": {"symbol": "€", "per_usd": 0.92},
    "GBP": {"symbol": "£", "per_usd": 0.79},
    "JPY": {"symbol": "¥", "per_usd": 149.0},
    "THB": {"symbol": "฿", "per_usd": 36.5},
    "IDR": {"symbol": "Rp", "per_usd": 15800.0},
    "AED": {"symbol": "د.إ", "per_usd": 3.67},
}
SEASON_HINTS = {
    "Winter": "cool-weather walks, heritage districts and cozy food stops",
    "Spring": "gardens, walking tours and outdoor cafés",
    "Summer": "early starts, shaded attractions and water-side breaks",
    "Monsoon": "flexible indoor alternatives, cafés and scenic viewpoints",
    "Autumn": "comfortable walking weather, markets and cultural sites",
}
VIBES = ["Beach", "Mountains", "Cultural", "Urban", "Foodie", "Nature", "Adventure"]
INTERESTS = ["Food", "Adventure", "History", "Nightlife", "Art & Design", "Nature", "Shopping", "Wellness"]

# Demo catalogue is intentionally small and transparent: these are starter suggestions,
# not live inventory, weather, opening-hour, or booking data.
DESTINATIONS = [
    {"city":"Lisbon, Portugal","vibes":["Urban","Cultural","Foodie"],"budget":"Moderate","season":["Spring","Summer","Autumn"],"tags":["Pastel de nata","Tile art","Sunset viewpoints"],"currency":"EUR","cost_day":105,"lat":38.7223,"lon":-9.1393,"summary":"Colorful lanes, viewpoints, seafood and easy day trips."},
    {"city":"Bali, Indonesia","vibes":["Beach","Nature","Wellness","Adventure"],"budget":"Budget","season":["Spring","Summer","Autumn"],"tags":["Beach reset","Temples","Wellness"],"currency":"IDR","cost_day":55,"lat":-8.4095,"lon":115.1889,"summary":"Beach time, rice terraces, temples and restorative stays."},
    {"city":"Jaipur, India","vibes":["Cultural","Foodie","Urban"],"budget":"Budget","season":["Winter","Autumn"],"tags":["Forts & palaces","Street food","Craft markets"],"currency":"INR","cost_day":35,"lat":26.9124,"lon":75.7873,"summary":"Rose-colored architecture, bazaars and rich Rajasthani food."},
    {"city":"Kyoto, Japan","vibes":["Cultural","Nature","Foodie"],"budget":"Luxury","season":["Spring","Autumn"],"tags":["Temples","Tea culture","Garden walks"],"currency":"JPY","cost_day":175,"lat":35.0116,"lon":135.7681,"summary":"Temple paths, quiet gardens, traditional streets and seasonal food."},
    {"city":"Bangkok, Thailand","vibes":["Urban","Foodie","Nightlife","Cultural"],"budget":"Budget","season":["Winter","Spring"],"tags":["Night markets","Street food","River temples"],"currency":"THB","cost_day":60,"lat":13.7563,"lon":100.5018,"summary":"High-energy markets, river temples and memorable street food."},
    {"city":"Interlaken, Switzerland","vibes":["Mountains","Nature","Adventure"],"budget":"Luxury","season":["Summer","Winter"],"tags":["Alpine views","Hiking","Adventure sports"],"currency":"EUR","cost_day":220,"lat":46.6863,"lon":7.8632,"summary":"Mountain scenery, lake walks and outdoor adventures."},
    {"city":"Udaipur, India","vibes":["Cultural","Foodie","Nature"],"budget":"Moderate","season":["Winter","Autumn"],"tags":["Lake sunsets","Palaces","Rooftop dining"],"currency":"INR","cost_day":48,"lat":24.5854,"lon":73.7125,"summary":"Lake views, palace architecture and relaxed evenings."},
    {"city":"Barcelona, Spain","vibes":["Beach","Urban","Cultural","Foodie","Nightlife"],"budget":"Moderate","season":["Spring","Summer","Autumn"],"tags":["Architecture","Beach break","Tapas"],"currency":"EUR","cost_day":130,"lat":41.3874,"lon":2.1686,"summary":"Distinctive architecture, beach afternoons and lively food culture."},
    {"city":"Queenstown, New Zealand","vibes":["Mountains","Nature","Adventure"],"budget":"Luxury","season":["Summer","Autumn","Winter"],"tags":["Lake views","Hiking","Adrenaline"],"currency":"USD","cost_day":185,"lat":-45.0312,"lon":168.6626,"summary":"A lake-and-mountain base for hikes and adventure activities."},
    {"city":"Mexico City, Mexico","vibes":["Urban","Cultural","Foodie","Art & Design"],"budget":"Moderate","season":["Winter","Spring","Autumn"],"tags":["Museums","Food scene","Design districts"],"currency":"USD","cost_day":90,"lat":19.4326,"lon":-99.1332,"summary":"World-class food, museums, leafy neighborhoods and design."},
]

# Attractions are grouped by neighborhood / coordinates to support a simple nearest-neighbor
# ordering heuristic. Estimates are illustrative and should be verified before travel.
ATTRACTIONS = {
    "Lisbon, Portugal": [
        ("Morning Sightseeing","Alfama lanes & viewpoint","History",38.7139,-9.1335,0, "Walk the old lanes early for quieter viewpoints."),
        ("Lunch Recommendation","Traditional tasca lunch","Food",38.7165,-9.1350,18, "Choose a busy local tasca; ask about daily specials."),
        ("Afternoon Leisure","Praça do Comércio riverside","Nature",38.7075,-9.1364,0, "Take an unhurried riverside stroll."),
        ("Evening Dining & Entertainment","Chiado dinner & live Fado option","Nightlife",38.7108,-9.1417,32, "Reserve ahead if you want a live music venue."),
        ("Morning Sightseeing","Belém Tower exterior & waterfront","History",38.6916,-9.2160,8, "Check access and opening conditions before visiting."),
        ("Lunch Recommendation","Belém bakery stop","Food",38.6975,-9.2065,12, "A classic pastry stop; queues vary."),
        ("Afternoon Leisure","Jerónimos area gardens","Nature",38.6979,-9.2067,5, "A relaxed break near the monuments."),
        ("Evening Dining & Entertainment","Time Out Market food hall","Food",38.7077,-9.1455,28, "A flexible option for groups with varied tastes."),
    ],
    "Jaipur, India": [
        ("Morning Sightseeing","Hawa Mahal area & old city walk","History",26.9239,75.8267,4,"Start early to avoid peak heat and crowds."),
        ("Lunch Recommendation","Rajasthani thali","Food",26.9200,75.8200,8,"Ask for a vegetarian thali if preferred."),
        ("Afternoon Leisure","City Palace area","History",26.9258,75.8237,7,"Allow extra time for museum sections."),
        ("Evening Dining & Entertainment","Johari Bazaar food and shopping walk","Shopping",26.9190,75.8260,10,"Agree on a meeting point in busy lanes."),
        ("Morning Sightseeing","Amber Fort","History",26.9855,75.8513,8,"Confirm ticketing and access details locally."),
        ("Lunch Recommendation","Local café near Amber","Food",26.9870,75.8500,7,"Keep a water break in the plan."),
        ("Afternoon Leisure","Panna Meena ka Kund stepwell","History",26.9890,75.8510,2,"Respect any access restrictions."),
        ("Evening Dining & Entertainment","Nahargarh viewpoint at sunset","Nature",26.9368,75.8150,15,"Check transport back after sunset."),
    ],
    "Bali, Indonesia": [
        ("Morning Sightseeing","Ubud rice terrace visit","Nature",-8.4312,115.2792,8,"Go early and confirm local access fees."),
        ("Lunch Recommendation","Indonesian café lunch","Food",-8.5069,115.2625,10,"Ask about spice level and dietary needs."),
        ("Afternoon Leisure","Ubud art and craft streets","Shopping",-8.5060,115.2620,5,"Browse small galleries and local makers."),
        ("Evening Dining & Entertainment","Ubud relaxed dinner","Food",-8.5068,115.2628,16,"Book ahead in busy seasons."),
        ("Morning Sightseeing","Temple visit (local dress rules apply)","History",-8.5193,115.2588,6,"Check current ceremony access and dress guidance."),
        ("Lunch Recommendation","Vegetarian Indonesian lunch","Food",-8.5170,115.2630,9,"Confirm ingredients directly with the restaurant."),
        ("Afternoon Leisure","Spa or wellness session","Wellness",-8.5060,115.2625,20,"Use a licensed provider and confirm inclusions."),
        ("Evening Dining & Entertainment","Sunset beach walk","Nature",-8.7200,115.1680,0,"Allow for traffic when crossing the island."),
    ],
    "Kyoto, Japan": [
        ("Morning Sightseeing","Fushimi Inari early walk","History",34.9671,135.7727,0,"Early hours are calmer; wear comfortable shoes."),
        ("Lunch Recommendation","Noodle or tofu lunch","Food",34.9750,135.7660,16,"Check dietary requirements and broth ingredients."),
        ("Afternoon Leisure","Higashiyama historic streets","History",34.9990,135.7800,4,"Be considerate in residential lanes."),
        ("Evening Dining & Entertainment","Gion dinner reservation","Food",35.0037,135.7788,38,"Respect privacy and local photography rules."),
        ("Morning Sightseeing","Arashiyama bamboo grove","Nature",35.0170,135.6713,0,"Arrive early to avoid crowds."),
        ("Lunch Recommendation","Riverside lunch in Arashiyama","Food",35.0145,135.6770,20,"Seasonal availability can vary."),
        ("Afternoon Leisure","Tenryu-ji garden area","Nature",35.0157,135.6738,8,"Verify garden and temple entry hours."),
        ("Evening Dining & Entertainment","Pontocho alley dinner","Nightlife",35.0045,135.7700,35,"Reserve popular restaurants in advance."),
    ],
}
GENERIC_ACTIVITIES = [
    ("Morning Sightseeing","Signature local landmark","History",0,0,12,"Verify access and ticket details."),
    ("Lunch Recommendation","Highly rated local lunch spot","Food",0,0,15,"Confirm opening hours and dietary options."),
    ("Afternoon Leisure","Garden, waterfront or neighborhood stroll","Nature",0,0,5,"Keep this slot flexible for weather."),
    ("Evening Dining & Entertainment","Local dinner and cultural experience","Food",0,0,25,"Book ahead where needed."),
]

def current_season(d: date) -> str:
    m = d.month
    if m in (12,1,2): return "Winter"
    if m in (3,4,5): return "Spring"
    if m in (6,7,8): return "Summer"
    if m in (9,10,11): return "Autumn"
    return "Spring"

def money(amount: float, currency: str) -> str:
    symbol = CURRENCIES.get(currency, CURRENCIES["USD"])["symbol"]
    return f"{symbol}{amount:,.0f}"

def to_usd(amount: float, currency: str) -> float:
    return amount / CURRENCIES.get(currency, CURRENCIES["USD"])["per_usd"]

def from_usd(amount: float, currency: str) -> float:
    return amount * CURRENCIES.get(currency, CURRENCIES["USD"])["per_usd"]

def haversine_km(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    if a == (0,0) or b == (0,0): return 999.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0],a[1],b[0],b[1]])
    dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371 * 2 * math.asin(math.sqrt(h))

def nearest_neighbor_order(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Greedy geographic ordering; keeps the first planned item as the anchor."""
    if len(items) < 3 or not all(x.get("lat") is not None and x.get("lon") is not None for x in items):
        return items
    remaining = items[1:]
    ordered = [items[0]]
    while remaining:
        last = ordered[-1]
        idx = min(range(len(remaining)), key=lambda i: haversine_km((last["lat"],last["lon"]), (remaining[i]["lat"],remaining[i]["lon"])))
        ordered.append(remaining.pop(idx))
    return ordered

def get_api_key(provider: str, typed_key: str) -> str:
    if typed_key.strip():
        return typed_key.strip()
    env_name = "GEMINI_API_KEY" if provider == "Gemini" else "GROQ_API_KEY"
    return os.getenv(env_name, "")

def call_llm(provider: str, api_key: str, prompt: str) -> Optional[str]:
    if not api_key:
        return None
    try:
        if provider == "Gemini":
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            response = requests.post(
                url, params={"key": api_key},
                json={"contents":[{"parts":[{"text":prompt}]}],
                      "generationConfig":{"temperature":0.65,"responseMimeType":"application/json"}},
                timeout=35,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        response = requests.post(
            url, headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[
                {"role":"system","content":"Return valid JSON only. No markdown fences."},
                {"role":"user","content":prompt}], "temperature":0.65},
            timeout=35,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.Timeout:
        st.warning("The AI request timed out. The planner will use its built-in demo plan instead.")
    except requests.RequestException as exc:
        st.warning(f"AI provider request failed; using demo content. Details: {exc}")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        st.warning(f"The AI response was not in the expected format; using demo content. Details: {exc}")
    return None

def parse_json_response(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.I|re.M).strip()
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if match:
            try:
                result = json.loads(match.group(0))
                return result if isinstance(result, dict) else None
            except json.JSONDecodeError:
                return None
    return None

def recommend_destinations(vibe: str, budget: str, travel_date: date, party: str, interests: List[str],
                           provider: str, api_key: str, demo_mode: bool) -> List[Dict[str, Any]]:
    season = current_season(travel_date)
    matches = []
    for d in DESTINATIONS:
        score = 0
        if vibe == "Open to anything" or vibe in d["vibes"]: score += 4
        if budget == d["budget"]: score += 2
        elif budget == "Moderate" or d["budget"] == "Moderate": score += 1
        if season in d["season"]: score += 2
        if "Food" in interests and ("Foodie" in d["vibes"] or "Food" in d["tags"]): score += 1
        if "Adventure" in interests and ("Adventure" in d["vibes"] or "Nature" in d["vibes"]): score += 1
        if "History" in interests and "Cultural" in d["vibes"]: score += 1
        if party == "Family" and "Adventure" not in d["vibes"]: score += 0.5
        matches.append((score, d))
    matches.sort(key=lambda x: x[0], reverse=True)
    demo_results = [dict(item) for _, item in matches[:3]]
    if demo_mode:
        return demo_results
    prompt = f"""Recommend exactly 3 destinations for a traveler. Return JSON:
{{"destinations":[{{"city":"City, Country","summary":"one sentence","tags":["tag1","tag2","tag3"],"budget_fit":"Budget|Moderate|Luxury","season_fit":"one sentence"}}]}}
Preferences: vibe={vibe}, budget={budget}, travel_date={travel_date.isoformat()}, season={season}, party={party}, interests={interests}.
Avoid unsupported claims about live weather or current prices. Keep recommendations practical."""
    data = parse_json_response(call_llm(provider, api_key, prompt))
    if data and isinstance(data.get("destinations"), list) and len(data["destinations"]) >= 3:
        by_city = {d["city"]:d for d in DESTINATIONS}
        out = []
        for item in data["destinations"][:3]:
            base = by_city.get(item.get("city"), {})
            out.append({**base, **item, "city":item.get("city","Suggested destination"),
                        "tags":item.get("tags",base.get("tags",["Local culture","Food","Explore"]))})
        return out
    return demo_results

def make_demo_itinerary(destination: str, days: int, start_date: date, currency: str,
                        budget: str, interests: List[str], pace: str, party: str) -> Dict[str, Any]:
    city_data = next((x for x in DESTINATIONS if x["city"].lower() == destination.lower()), None)
    currency = city_data["currency"] if city_data else currency
    budget_factor = {"Budget":0.75,"Moderate":1.0,"Luxury":1.75}.get(budget,1.0)
    pace_factor = {"Relaxed":0.85,"Moderate":1.0,"Fast-Paced":1.15}.get(pace,1.0)
    days_out = []
    local = ATTRACTIONS.get(destination, GENERIC_ACTIVITIES)
    for day_index in range(days):
        chosen = local[(day_index*4) % len(local):((day_index*4) % len(local))+4]
        if len(chosen) < 4:
            chosen += GENERIC_ACTIVITIES[:4-len(chosen)]
        activities = []
        times = ["09:00–11:30","12:00–13:30","14:00–16:30","18:00–20:30"]
        for slot_i, entry in enumerate(chosen):
            slot, name, category, lat, lon, base_cost, note = entry
            if interests and category not in interests and category not in ("Food","History","Nature"):
                note += " Adjust this stop to your interests if desired."
            cost = round(base_cost * budget_factor * pace_factor, 2)
            activities.append({"slot":slot,"time":times[slot_i],"name":name,"category":category,
                               "cost":cost,"currency":currency,"cost_usd":round(to_usd(cost,currency),2),
                               "cost_inr":round(to_usd(cost,currency)*CURRENCIES["INR"]["per_usd"],2),
                               "lat":lat,"lon":lon,"note":note})
        # Optimize only the sightseeing/leisure sequence while preserving meal-time slots.
        fixed_slots = {a["slot"]:a for a in activities}
        movable = [a for a in activities if a["slot"] in ("Morning Sightseeing","Afternoon Leisure")]
        optimized = nearest_neighbor_order(movable)
        for i, item in enumerate(optimized):
            item["slot"] = movable[i]["slot"]
        activities = sorted(activities, key=lambda a: ["Morning Sightseeing","Lunch Recommendation","Afternoon Leisure","Evening Dining & Entertainment"].index(a["slot"]))
        days_out.append({"day":day_index+1,"date":(start_date+timedelta(days=day_index)).isoformat(),"activities":activities})
    total = sum(a["cost_usd"] for d in days_out for a in d["activities"])
    return {"destination":destination,"currency":currency,"days":days_out,"total_usd":round(total,2),
            "total_inr":round(total*CURRENCIES["INR"]["per_usd"],2),"generated_by":"demo"}

def generate_itinerary(destination: str, days: int, start_date: date, currency: str, budget: str,
                       interests: List[str], pace: str, party: str, provider: str, api_key: str,
                       demo_mode: bool) -> Dict[str, Any]:
    if demo_mode:
        return make_demo_itinerary(destination,days,start_date,currency,budget,interests,pace,party)
    prompt = f"""Create a practical day-by-day travel itinerary and return JSON only in this schema:
{{"destination":"City, Country","currency":"ISO currency code","days":[{{"day":1,"date":"YYYY-MM-DD","activities":[{{"slot":"Morning Sightseeing|Lunch Recommendation|Afternoon Leisure|Evening Dining & Entertainment","time":"09:00–11:30","name":"specific place or activity","category":"History","cost":20,"note":"brief practical note","lat":0,"lon":0}}]}}]}}
Destination={destination}; duration={days} days; start date={start_date}; budget={budget}; interests={interests}; pace={pace}; party={party}.
Requirements: exactly {days} days, four sequential slots each day, group nearby attractions to reduce transit/backtracking, estimate costs in the destination's local currency, no fabricated guarantees about opening hours or reservations. Use plausible estimated costs and coordinates where confident; use 0,0 if not confident. Currency must be an ISO code. Output JSON only."""
    data = parse_json_response(call_llm(provider,api_key,prompt))
    if not data or not isinstance(data.get("days"),list) or len(data["days"]) < 1:
        return make_demo_itinerary(destination,days,start_date,currency,budget,interests,pace,party)
    try:
        out_days = []
        for i, day_obj in enumerate(data["days"][:days]):
            acts = day_obj.get("activities", [])
            cleaned = []
            for j, act in enumerate(acts[:4]):
                cur = str(data.get("currency",currency)).upper()
                if cur not in CURRENCIES: cur = currency
                cost = max(0,float(act.get("cost",0)))
                cleaned.append({"slot":act.get("slot",GENERIC_ACTIVITIES[j][0]),"time":act.get("time",["09:00–11:30","12:00–13:30","14:00–16:30","18:00–20:30"][j]),
                    "name":str(act.get("name","Explore locally")),"category":str(act.get("category","Explore")),"cost":cost,
                    "currency":cur,"cost_usd":round(to_usd(cost,cur),2),
                    "cost_inr":round(to_usd(cost,cur)*CURRENCIES["INR"]["per_usd"],2),
                    "lat":float(act.get("lat",0) or 0),"lon":float(act.get("lon",0) or 0),
                    "note":str(act.get("note","Confirm details before visiting."))})
            while len(cleaned) < 4:
                j=len(cleaned); e=GENERIC_ACTIVITIES[j]
                cleaned.append({"slot":e[0],"time":["09:00–11:30","12:00–13:30","14:00–16:30","18:00–20:30"][j],"name":e[1],
                    "category":e[2],"cost":e[5],"currency":currency,"cost_usd":round(to_usd(e[5],currency),2),
                    "cost_inr":round(to_usd(e[5],currency)*CURRENCIES["INR"]["per_usd"],2),"lat":0,"lon":0,"note":e[6]})
            out_days.append({"day":i+1,"date":(start_date+timedelta(days=i)).isoformat(),"activities":cleaned})
        total = sum(a["cost_usd"] for d in out_days for a in d["activities"])
        return {"destination":data.get("destination",destination),"currency":data.get("currency",currency),
                "days":out_days,"total_usd":round(total,2),"total_inr":round(total*CURRENCIES["INR"]["per_usd"],2),
                "generated_by":provider.lower()}
    except (ValueError,TypeError,KeyError) as exc:
        st.warning(f"Could not normalize the AI itinerary; using demo plan. Details: {exc}")
        return make_demo_itinerary(destination,days,start_date,currency,budget,interests,pace,party)

def swap_activity(trip: Dict[str,Any], day_number: int, slot_name: str, instruction: str,
                  provider: str, api_key: str, demo_mode: bool, vegetarian: bool=False) -> Dict[str,Any]:
    day = next(d for d in trip["days"] if d["day"] == day_number)
    old = next(a for a in day["activities"] if a["slot"] == slot_name)
    if not demo_mode:
        prompt = f"""Return JSON for one replacement activity only:
{{"name":"...","category":"...","cost":20,"note":"...","lat":0,"lon":0}}
Destination={trip['destination']}; slot={slot_name}; current activity={old['name']}; user request={instruction}; vegetarian_only={vegetarian}; currency={trip['currency']}.
Estimate cost in local currency, don't claim live availability, and preserve slot intent."""
        data = parse_json_response(call_llm(provider,api_key,prompt))
    else:
        data = None
    if not data:
        req = instruction.lower()
        if vegetarian or "vegetarian" in req:
            name, cat, cost, note = "Vegetarian-friendly local café (verify ingredients)","Food",max(8,old["cost"]),"Ask staff about ingredients and cross-contamination."
        elif any(k in req for k in ("market","bazaar","outdoor")):
            name, cat, cost, note = "Outdoor local market walk","Shopping",max(4,old["cost"]*0.65),"Check market days and keep valuables secure."
        elif any(k in req for k in ("museum","history","indoor")):
            name, cat, cost, note = "Local museum or cultural gallery","History",max(6,old["cost"]*1.1),"Confirm opening hours and ticket costs."
        elif any(k in req for k in ("nature","park","garden","outdoor")):
            name, cat, cost, note = "City garden or scenic outdoor walk","Nature",max(0,old["cost"]*0.4),"Choose a weather-appropriate route."
        else:
            name, cat, cost, note = "Flexible neighborhood discovery walk","Explore",old["cost"],"A flexible alternative based on your travel vibe."
        data = {"name":name,"category":cat,"cost":cost,"note":note,"lat":0,"lon":0}
    cur = trip["currency"]
    cost = max(0,float(data.get("cost",old["cost"])))
    replacement = {**old,"name":str(data.get("name","Alternative local activity")),"category":str(data.get("category","Explore")),
                   "cost":cost,"cost_usd":round(to_usd(cost,cur),2),"cost_inr":round(to_usd(cost,cur)*CURRENCIES["INR"]["per_usd"],2),
                   "note":str(data.get("note","Confirm details locally.")),"lat":float(data.get("lat",0) or 0),"lon":float(data.get("lon",0) or 0)}
    day["activities"] = [replacement if a["slot"] == slot_name else a for a in day["activities"]]
    refresh_totals(trip)
    return trip

def refresh_totals(trip: Dict[str,Any]) -> None:
    total = sum(float(a.get("cost_usd",0)) for d in trip["days"] for a in d["activities"])
    trip["total_usd"] = round(total,2)
    trip["total_inr"] = round(total*CURRENCIES["INR"]["per_usd"],2)

def create_pdf(trip: Dict[str,Any], preferences: Dict[str,Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Hero",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=23,leading=27,textColor=colors.HexColor("#173F35"),alignment=TA_CENTER,spaceAfter=7))
    styles.add(ParagraphStyle(name="SubHero",parent=styles["Normal"],fontSize=10,textColor=colors.HexColor("#64756D"),alignment=TA_CENTER,spaceAfter=18))
    styles.add(ParagraphStyle(name="DayHead",parent=styles["Heading2"],fontSize=15,leading=18,textColor=colors.HexColor("#173F35"),spaceBefore=10,spaceAfter=7))
    styles.add(ParagraphStyle(name="Small",parent=styles["Normal"],fontSize=8.5,leading=11))
    story = [Paragraph("WANDER WELL",styles["Hero"]),Paragraph("YOUR PERSONALIZED TRAVEL GUIDE",styles["SubHero"]),
             Paragraph(trip["destination"],styles["Heading1"]),
             Paragraph(f"{len(trip['days'])} days · {preferences.get('start_date','')} · {preferences.get('budget','Moderate')} budget · {preferences.get('party','Solo')} trip",styles["Normal"]),
             Spacer(1,8*mm),
             Paragraph(f"Estimated activity spend: {money(from_usd(trip['total_usd'],trip.get('currency','USD')),trip.get('currency','USD'))} · ${trip['total_usd']:,.0f} USD · ₹{trip['total_inr']:,.0f} INR",styles["Heading2"]),
             Paragraph("Costs are estimates, not quotes. Verify prices, opening hours, transit, visa rules and safety guidance before departure.",styles["Small"]),Spacer(1,5*mm)]
    for day in trip["days"]:
        story.append(Paragraph(f"Day {day['day']} — {day['date']}",styles["DayHead"]))
        rows = [["Time","Plan","Est. cost","Helpful note"]]
        for a in day["activities"]:
            note = a.get("note","")
            rows.append([a.get("time",""),Paragraph(f"<b>{a.get('slot','')}</b><br/>{a.get('name','')}",styles["Small"]),
                         money(a.get("cost",0),a.get("currency",trip.get("currency","USD"))),
                         Paragraph(note,styles["Small"])])
        table = Table(rows,colWidths=[23*mm,65*mm,24*mm,55*mm],repeatRows=1,hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173F35")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
            ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#DDE6E0")),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F5F8F5")]),
        ]))
        story.extend([table,Spacer(1,4*mm)])
    story.extend([PageBreak(),Paragraph("BEFORE YOU GO",styles["DayHead"]),
        Paragraph("Emergency & readiness checklist",styles["Heading2"])])
    checklist = [
        "[ ] Save local emergency number and nearest hospital",
        "[ ] Share itinerary and accommodation details with a trusted contact",
        "[ ] Keep passport/ID copies stored separately from originals",
        "[ ] Confirm travel insurance, medication and accessibility needs",
        "[ ] Check official travel advisories, entry rules and local transport",
        "[ ] Download offline maps, tickets and key addresses",
        "[ ] Confirm dietary requirements and allergies directly with venues",
        "[ ] Keep a charged phone, power bank and backup payment method",
    ]
    for item in checklist:
        story.append(Paragraph(item,styles["Normal"])); story.append(Spacer(1,2*mm))
    story.extend([Spacer(1,6*mm),Paragraph("Useful numbers to fill in before departure",styles["Heading2"]),
                  Paragraph("Local emergency: ____________________ &nbsp;&nbsp; Accommodation: ____________________",styles["Normal"]),
                  Paragraph("Travel insurer: _______________________ &nbsp;&nbsp; Trusted contact: ____________________",styles["Normal"]),
                  Spacer(1,8*mm),Paragraph("Made with Personalized Travel Itinerary Planner · Verify all information before relying on it.",styles["Small"])])
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DDE6E0")); canvas.line(16*mm,12*mm,A4[0]-16*mm,12*mm)
        canvas.setFont("Helvetica",8); canvas.setFillColor(colors.HexColor("#64756D"))
        canvas.drawString(16*mm,7*mm,"Wander Well · Personal trip planner")
        canvas.drawRightString(A4[0]-16*mm,7*mm,f"Page {doc.page}")
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
    :root { --forest:#173f35; --sage:#dfe9df; --cream:#f7f6f0; --coral:#d77d61; }
    .stApp { background: linear-gradient(180deg,#f8f7f1 0%,#f3f6f0 100%); color:#24352e; font-family:'DM Sans',sans-serif; }
    .block-container { max-width: 1200px; padding-top:1.7rem; padding-bottom:3rem; }
    h1,h2,h3 { font-family:'Playfair Display',serif !important; color:var(--forest) !important; }
    .hero { background:linear-gradient(120deg,#173f35 0%,#2f6653 65%,#70947c 100%); color:white; padding:2.3rem 2.2rem; border-radius:24px; margin-bottom:1.2rem; box-shadow:0 14px 38px rgba(23,63,53,.12); }
    .hero .eyebrow { letter-spacing:.18em; font-size:.72rem; font-weight:700; opacity:.8; }
    .hero h1 { color:white !important; font-size:2.6rem; line-height:1.12; margin:.45rem 0; }
    .hero p { color:#e6eee7; max-width:660px; margin-bottom:0; }
    .mini-card { background:rgba(255,255,255,.82); border:1px solid #e2e8df; border-radius:18px; padding:1.05rem 1.1rem; height:100%; }
    .tag { display:inline-block; background:#e7eee5; color:#315849; border-radius:999px; padding:.25rem .6rem; font-size:.76rem; margin:.18rem .15rem .1rem 0; }
    .muted { color:#6e7e73; font-size:.9rem; }
    div[data-testid="stMetric"] { background:#fff; border:1px solid #e2e8df; border-radius:15px; padding:12px 16px; }
    .stButton>button { border-radius:999px; font-weight:600; border:1px solid #c7d7c9; }
    .stButton>button[kind="primary"] { background:#173f35; border-color:#173f35; }
    div[data-testid="stTabs"] button { font-weight:600; }
    div[data-testid="stExpander"] { border:1px solid #e1e8df; border-radius:14px; background:rgba(255,255,255,.65); }
    [data-testid="stSidebar"] { background:#edf2e9; }
    </style>
    """, unsafe_allow_html=True)

def init_state():
    defaults = {"saved_trips": [], "active_trip": None, "preferences": {}, "destination_results": []}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def render_activity(activity: Dict[str,Any], currency: str):
    col1,col2 = st.columns([5,1.3])
    with col1:
        st.markdown(f"**{activity['time']} · {activity['slot']}**")
        st.markdown(f"### {activity['name']}")
        st.caption(f"{activity.get('category','Explore')} · {activity.get('note','')}")
    with col2:
        st.metric("Estimate",money(activity.get("cost",0),activity.get("currency",currency)))
        st.caption(f"${activity.get('cost_usd',0):,.0f} · ₹{activity.get('cost_inr',0):,.0f}")
    st.divider()

def main():
    st.set_page_config(page_title=APP_TITLE,page_icon="🧭",layout="wide",initial_sidebar_state="expanded")
    inject_css(); init_state()
    st.markdown(f"""<div class="hero"><div class="eyebrow">SKILL WALLET · CAPSTONE PROJECT 4</div>
    <h1>Personalized Travel<br/>Itinerary Planner</h1>
    <p>{APP_SUBTITLE} Find a destination that fits your mood, build a day-wise plan, and keep your trip guide ready offline.</p></div>""",unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## Trip studio")
        provider = st.selectbox("AI provider",["Gemini","Groq"])
        api_key_input = st.text_input("API key",type="password",help="Stored only in this Streamlit session. For deployment, use Streamlit Secrets or environment variables.")
        demo_mode = st.toggle("Demo mode",value=True,help="Uses built-in destination examples and deterministic demo activities. No API key is needed.")
        st.caption("Tip: turn Demo mode off to use your provider key. Set GEMINI_API_KEY or GROQ_API_KEY in Streamlit secrets/environment for deployment.")
        st.divider()
        st.markdown("**Privacy note**")
        st.caption("This demo keeps saved trips in session memory. They may be lost when the session restarts; no external database is used.")
    api_key = get_api_key(provider,api_key_input)
    if not demo_mode and not api_key:
        st.sidebar.warning("Enter a key or configure a server-side secret. Demo content remains available.")

    tab1,tab2,tab3,tab4 = st.tabs(["✦ Discover","▦ Itinerary","↻ Customize","⇩ Trip library"])

    with tab1:
        st.subheader("Tell us what kind of trip you want")
        st.write("Leave the destination open and discover places that match your budget, season and travel mood.")
        with st.form("preferences_form"):
            c1,c2,c3 = st.columns(3)
            with c1:
                destination_mode = st.radio("Destination",["I have a destination","Recommend one"],horizontal=False)
                destination_options = ["Lisbon, Portugal","Bali, Indonesia","Jaipur, India","Kyoto, Japan","Bangkok, Thailand","Interlaken, Switzerland","Udaipur, India","Barcelona, Spain","Queenstown, New Zealand","Mexico City, Mexico"]
                destination = st.selectbox("Destination or starting point",destination_options) if destination_mode == "I have a destination" else "Open to anything"
                vibe = st.selectbox("Travel vibe",["Open to anything"]+VIBES)
            with c2:
                duration = st.number_input("Trip duration (days)",min_value=1,max_value=21,value=4,step=1)
                start_date = st.date_input("Start date",value=date.today()+timedelta(days=30),min_value=date.today())
                budget = st.selectbox("Budget level",["Budget","Moderate","Luxury"],index=1)
            with c3:
                party = st.selectbox("Travel party",["Solo","Couple","Family","Friends"])
                pace = st.selectbox("Pace",["Relaxed","Moderate","Fast-Paced"],index=1)
                interests = st.multiselect("Interests",INTERESTS,default=["Food","History"])
            submitted = st.form_submit_button("Find my travel match",type="primary",use_container_width=True)
        if submitted:
            prefs = {"destination":destination,"vibe":vibe,"duration":int(duration),"start_date":start_date.isoformat(),
                     "budget":budget,"party":party,"pace":pace,"interests":interests,"currency":"INR"}
            st.session_state.preferences = prefs
            if destination == "Open to anything":
                st.session_state.destination_results = recommend_destinations(vibe,budget,start_date,party,interests,provider,api_key,demo_mode)
                st.success("Your destination shortlist is ready.")
            else:
                st.session_state.destination_results = []
                trip = generate_itinerary(destination,int(duration),start_date,"INR",budget,interests,pace,party,provider,api_key,demo_mode)
                st.session_state.active_trip = trip
                st.success("Your itinerary draft is ready. Open the Itinerary tab to explore it.")
        if st.session_state.destination_results:
            st.markdown("### Your top 3 destination matches")
            cols = st.columns(3)
            for i,item in enumerate(st.session_state.destination_results[:3]):
                with cols[i]:
                    tags = item.get("tags",[])
                    st.markdown(f"""<div class="mini-card"><div class="muted">MATCH {i+1}</div>
                    <h3>{item.get('city','Destination')}</h3><p>{item.get('summary',item.get('summary','A memorable place to explore.'))}</p>
                    <p>{''.join(f'<span class="tag">{t}</span>' for t in tags[:4])}</p>
                    <p class="muted">Budget fit: {item.get('budget_fit',item.get('budget','Flexible'))}</p></div>""",unsafe_allow_html=True)
                    if st.button(f"Plan this trip",key=f"choose_{i}",use_container_width=True):
                        prefs = st.session_state.preferences.copy()
                        prefs["destination"] = item["city"]
                        st.session_state.preferences = prefs
                        st.session_state.active_trip = generate_itinerary(item["city"],prefs["duration"],date.fromisoformat(prefs["start_date"]),
                            item.get("currency","INR"),prefs["budget"],prefs["interests"],prefs["pace"],prefs["party"],provider,api_key,demo_mode)
                        st.toast(f"Draft created for {item['city']}. Open Itinerary.")
        st.caption("Destination matches use a small demo catalogue and seasonal heuristics; they are not live weather forecasts or real-time travel advice.")

    with tab2:
        st.subheader("Your day-by-day plan")
        trip = st.session_state.active_trip
        if not trip:
            st.info("Create a plan in Discover first, then come back here.")
        else:
            prefs = st.session_state.preferences
            m1,m2,m3 = st.columns(3)
            m1.metric("Destination",trip["destination"])
            m2.metric("Estimated activity spend",f"${trip['total_usd']:,.0f} USD")
            m3.metric("Approx. INR",f"₹{trip['total_inr']:,.0f}")
            st.caption(f"Plan source: {trip.get('generated_by','demo')} · Local currency: {trip.get('currency','USD')}. Estimates exclude flights, lodging, insurance and unlisted transport.")
            for day in trip["days"]:
                with st.expander(f"Day {day['day']} · {day['date']}",expanded=(day["day"]==1)):
                    for activity in day["activities"]:
                        render_activity(activity,trip.get("currency","USD"))
                    day_total = sum(a.get("cost_usd",0) for a in day["activities"])
                    st.markdown(f"**Day total:** ${day_total:,.0f} USD · ₹{day_total*CURRENCIES['INR']['per_usd']:,.0f} INR")
            st.markdown("### Budget snapshot")
            st.progress(min(1.0,trip["total_usd"]/max(1,trip["total_usd"]*1.2)))
            st.caption(f"Activity estimate: ${trip['total_usd']:,.0f} USD / ₹{trip['total_inr']:,.0f} INR. Use the Customize tab to swap a slot and update the running total.")
            with st.expander("How geographic clustering works"):
                st.write("When coordinates are available, the planner uses a nearest-neighbor distance heuristic to order eligible sightseeing/leisure stops. It is a lightweight heuristic—not a live routing engine—and it does not account for traffic, transit timetables, closures, or road conditions.")
            if st.button("Save this trip to Trip library",type="primary"):
                snapshot = {"id":f"trip-{date.today().isoformat()}-{len(st.session_state.saved_trips)+1}",
                            "saved_at":date.today().isoformat(),"trip":json.loads(json.dumps(trip)),
                            "preferences":json.loads(json.dumps(prefs,default=str))}
                st.session_state.saved_trips.insert(0,snapshot)
                st.toast("Trip saved in this session.")

    with tab3:
        st.subheader("Make it feel more like you")
        trip = st.session_state.active_trip
        if not trip:
            st.info("Create an itinerary first to customize an individual activity.")
        else:
            day_num = st.selectbox("Choose a day",options=[d["day"] for d in trip["days"]],format_func=lambda x:f"Day {x}")
            selected_day = next(d for d in trip["days"] if d["day"]==day_num)
            slot_options = [a["slot"] for a in selected_day["activities"]]
            slot = st.selectbox("Which time slot?",slot_options)
            current = next(a for a in selected_day["activities"] if a["slot"]==slot)
            st.info(f"Current plan: **{current['name']}** · estimate {money(current['cost'],current['currency'])}")
            with st.form("swap_form"):
                instruction = st.text_input("What would you prefer?",placeholder="e.g. swap museum for outdoor market")
                vegetarian = st.checkbox("Prefer a vegetarian-friendly food option")
                regenerate_day = st.checkbox("Regenerate all four slots for this day",value=False)
                do_swap = st.form_submit_button("Update my plan",type="primary")
            if do_swap:
                if regenerate_day:
                    # Regenerate only the selected day by rotating its activities; other days stay intact.
                    old_activities = selected_day["activities"]
                    rotated = old_activities[1:] + old_activities[:1]
                    for i,a in enumerate(rotated):
                        a["note"] = (a.get("note","") + " Day refreshed; verify details locally.").strip()
                    selected_day["activities"] = rotated
                    refresh_totals(trip)
                    st.success(f"Day {day_num} refreshed. Other days were preserved.")
                else:
                    st.session_state.active_trip = swap_activity(trip,day_num,slot,instruction or "find a fresh alternative",
                        provider,api_key,demo_mode,vegetarian)
                    st.success("Only the selected slot was updated; the rest of your itinerary is unchanged.")
                st.rerun()
            st.markdown("### Current day")
            for a in selected_day["activities"]:
                with st.container(border=True):
                    st.markdown(f"**{a['time']} · {a['slot']}** — {a['name']}")
                    st.caption(f"{money(a['cost'],a['currency'])} · {a['note']}")

    with tab4:
        st.subheader("Trip library & offline guide")
        st.write("Save multiple drafts during this session, revisit trip history, and export a printable PDF.")
        trip = st.session_state.active_trip
        if trip:
            st.markdown("#### Export current itinerary")
            if st.button("Prepare offline PDF guide",type="primary"):
                try:
                    pdf = create_pdf(trip,st.session_state.preferences)
                    st.session_state["latest_pdf"] = pdf
                    st.success("Your PDF guide is ready.")
                except Exception as exc:
                    st.error(f"PDF export failed: {exc}")
            if st.session_state.get("latest_pdf"):
                st.download_button("⬇ Download itinerary PDF",data=st.session_state["latest_pdf"],
                    file_name=f"travel-itinerary-{re.sub(r'[^a-z0-9]+','-',trip['destination'].lower()).strip('-')}.pdf",
                    mime="application/pdf",use_container_width=True)
        else:
            st.info("Create an itinerary to export a PDF guide.")
        st.divider()
        st.markdown("#### Saved trip history")
        if not st.session_state.saved_trips:
            st.caption("No saved trips yet. Save a plan from the Itinerary tab.")
        else:
            for i,saved in enumerate(st.session_state.saved_trips):
                saved_trip = saved["trip"]
                with st.expander(f"{saved_trip['destination']} · {len(saved_trip['days'])} days · saved {saved['saved_at']}"):
                    st.caption(f"Estimated spend: ${saved_trip['total_usd']:,.0f} USD · {saved_trip['generated_by']}")
                    if st.button("Restore this trip",key=f"restore_{i}"):
                        st.session_state.active_trip = saved_trip
                        st.session_state.preferences = saved.get("preferences",{})
                        st.success("Trip restored.")
                        st.rerun()
                    if st.button("Export this saved trip",key=f"export_{i}"):
                        try:
                            pdf = create_pdf(saved_trip,saved.get("preferences",{}))
                            st.download_button("Download saved trip PDF",data=pdf,
                                file_name=f"travel-itinerary-{i+1}.pdf",mime="application/pdf",key=f"download_saved_{i}")
                        except Exception as exc:
                            st.error(f"Could not export this trip: {exc}")
        st.caption("Persistence is simulated with Streamlit session state, as requested. For durable history across sessions, add a hosted database or object store in a future version.")

    st.markdown("---")
    st.caption("Travel responsibly · Costs and destination details are indicative only. Verify official advisories, local rules, accessibility, dietary needs, weather, and all bookings independently.")

if __name__ == "__main__":
    main()
