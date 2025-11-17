import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import Farmerprofile, Soiltest, Farmobservation, Analysisresult
import requests

app = FastAPI(title="AI-Powered Smart Farming Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateProfileRequest(Farmerprofile):
    pass


class ObservationRequest(Farmobservation):
    pass


class SoilTestRequest(Soiltest):
    pass


class AnalysisRequest(BaseModel):
    farmer_id: Optional[str] = None
    target_crop: Optional[str] = None


def collection_name(model_cls) -> str:
    return model_cls.__name__.lower()


@app.get("/")
def read_root():
    return {"message": "Smart Farming Assistant Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["connection_status"] = "Connected"
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:60]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:60]}"

    return response


@app.get("/schema")
def get_schema():
    # Expose schemas so external tools/viewers can read collection definitions
    return {
        "farmerprofile": Farmerprofile.model_json_schema(),
        "soiltest": Soiltest.model_json_schema(),
        "farmobservation": Farmobservation.model_json_schema(),
        "analysisresult": Analysisresult.model_json_schema(),
    }


@app.post("/profiles")
def create_profile(payload: CreateProfileRequest):
    inserted_id = create_document(collection_name(Farmerprofile), payload)
    return {"id": inserted_id}


@app.get("/profiles")
def list_profiles(limit: int = 50):
    docs = get_documents(collection_name(Farmerprofile), {}, limit)
    # Convert ObjectId to string
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"])
    return docs


@app.post("/soiltests")
def create_soiltest(payload: SoilTestRequest):
    inserted_id = create_document(collection_name(Soiltest), payload)
    return {"id": inserted_id}


@app.post("/observations")
def create_observation(payload: ObservationRequest):
    inserted_id = create_document(collection_name(Farmobservation), payload)
    return {"id": inserted_id}


def simple_disease_pest_risk(obs: Farmobservation) -> dict:
    risk = {"disease": {}, "pest": {}}
    # Basic heuristic rules as baseline (can be replaced with ML later)
    if obs.humidity_pct and obs.humidity_pct >= 80:
        risk["disease"]["fungal_general"] = "high"
    elif obs.humidity_pct and obs.humidity_pct >= 60:
        risk["disease"]["fungal_general"] = "medium"
    else:
        risk["disease"]["fungal_general"] = "low"

    if obs.temp_c and obs.temp_c >= 28:
        risk["pest"]["borers_aphids_general"] = "medium"
    if obs.temp_c and obs.temp_c >= 32:
        risk["pest"]["borers_aphids_general"] = "high"

    if obs.rainfall_mm and obs.rainfall_mm > 50:
        risk["disease"]["washout_root_rot"] = "medium"

    if obs.pest_signs and len(obs.pest_signs) > 0:
        risk["pest"]["observed_signs"] = "high"
    if obs.disease_signs and len(obs.disease_signs) > 0:
        risk["disease"]["observed_signs"] = "high"
    return risk


def irrigation_schedule(profile: Optional[Farmerprofile], soil: Optional[Soiltest], obs: Optional[Farmobservation]):
    schedule = {"frequency_days": 3, "amount_mm": 20, "notes": []}
    soil_type = profile.soil_type if profile else None
    if soil_type in ["sandy", "sandy loam", "loamy sand"]:
        schedule["frequency_days"] = 2
        schedule["amount_mm"] = 15
        schedule["notes"].append("Sandy soils drain fast; irrigate more frequently with smaller amounts.")
    elif soil_type in ["loam", "loamy"]:
        schedule["frequency_days"] = 3
        schedule["amount_mm"] = 20
    elif soil_type in ["clay", "clayey", "silty clay"]:
        schedule["frequency_days"] = 4
        schedule["amount_mm"] = 25
        schedule["notes"].append("Clay soils retain water longer; reduce frequency but increase amount.")

    if obs and obs.rainfall_mm and obs.rainfall_mm >= 15:
        schedule["notes"].append("Recent rainfall detected; skip next irrigation if field is moist.")

    if profile and profile.irrigation_method == "drip":
        schedule["notes"].append("Using drip? Split daily in small doses for uniform moisture.")

    return schedule


def climate_advice(profile: Optional[Farmerprofile], obs: Optional[Farmobservation]) -> List[str]:
    tips: List[str] = []
    if profile and profile.surrounding_env and "forest" in profile.surrounding_env:
        tips.append("Watch for wildlife and pest pressure near forest edges; use traps and barriers.")
    if obs and obs.wind_kph and obs.wind_kph > 30:
        tips.append("High winds expected; stake young plants and secure mulches or covers.")
    if obs and obs.temp_c and obs.temp_c > 35:
        tips.append("Heat stress risk; irrigate early morning, add shade nets for seedlings.")
    if obs and obs.temp_c and obs.temp_c < 10:
        tips.append("Cold stress risk; consider row covers or mulches to retain soil heat.")
    tips.append("Adopt mulching to conserve moisture and suppress weeds.")
    tips.append("Use integrated pest management (IPM): monitoring, thresholds, biological controls.")
    return tips


def simple_yield_forecast(profile: Optional[Farmerprofile], soil: Optional[Soiltest], obs: Optional[Farmobservation]):
    # Very rough heuristic baseline per hectare
    base_yields = {
        "wheat": 3500,
        "rice": 4500,
        "maize": 5000,
        "soybean": 2500,
        "cotton": 2200,
        "potato": 20000,
        "tomato": 30000,
    }
    crop = (obs.target_crop if obs and obs.target_crop else (profile.crop_history[-1] if profile and profile.crop_history else "wheat")).lower()
    base = base_yields.get(crop, 3000)

    modifier = 1.0
    if soil and soil.ph and (soil.ph < 5.5 or soil.ph > 8.5):
        modifier -= 0.15
    if soil and soil.organic_matter_pct and soil.organic_matter_pct >= 2.0:
        modifier += 0.05
    if obs and obs.rainfall_mm and obs.rainfall_mm < 10:
        modifier -= 0.1
    if obs and obs.humidity_pct and obs.humidity_pct > 85:
        modifier -= 0.05

    return {"crop": crop, "yield_kg_per_ha": int(base * modifier)}


def rotation_plan(profile: Optional[Farmerprofile]) -> List[str]:
    plan: List[str] = []
    last = profile.crop_history[-1].lower() if profile and profile.crop_history else None
    if last in ["rice", "wheat", "maize"]:
        plan = ["legume (soybean/chickpea)", "oilseed (mustard/sunflower)", "vegetable (tomato/onion)"]
    elif last in ["cotton", "sugarcane"]:
        plan = ["pulse (cowpea/green gram)", "cereal (maize)", "forage (sorghum/berseem)"]
    else:
        plan = ["cereal", "legume", "vegetable"]
    return plan


def market_trends(location_text: Optional[str], crop: Optional[str]) -> List[dict]:
    # Placeholder heuristic with optional fetch to public APIs if available
    trends: List[dict] = []
    try:
        # Example hook for Google/other APIs (keys via env). If not present, we fall back.
        # This is where teams can integrate Google Trends, geocoding, or market-price APIs.
        pass
    except Exception:
        pass

    # Fallback synthetic trend
    sample = [
        {"crop": crop or "wheat", "avg_price": 21.5, "unit": "INR/kg", "demand": "rising", "location": location_text},
        {"crop": "tomato", "avg_price": 14.2, "unit": "INR/kg", "demand": "stable", "location": location_text},
        {"crop": "onion", "avg_price": 18.7, "unit": "INR/kg", "demand": "high", "location": location_text},
    ]
    trends.extend(sample)
    return trends


@app.post("/analyze")
def analyze(req: AnalysisRequest):
    # Load last known profile/soil/obs for the farmer if id provided
    profile_doc = None
    soil_doc = None
    obs_doc = None
    if req.farmer_id:
        try:
            profile_doc = get_documents(collection_name(Farmerprofile), {"_id": {"$exists": True}, "_id": {"$eq": __import__("bson").objectid.ObjectId(req.farmer_id)}}, 1)
            profile_doc = profile_doc[0] if profile_doc else None
        except Exception:
            profile_doc = None
        try:
            soil_doc = get_documents(collection_name(Soiltest), {"farmer_id": req.farmer_id}, 1)
            soil_doc = soil_doc[0] if soil_doc else None
        except Exception:
            soil_doc = None
        try:
            obs_doc = get_documents(collection_name(Farmobservation), {"farmer_id": req.farmer_id}, 1)
            obs_doc = obs_doc[0] if obs_doc else None
        except Exception:
            obs_doc = None

    # Convert dicts to pydantic models (tolerate missing)
    profile = Farmerprofile(**{k: v for k, v in (profile_doc or {}).items() if k in Farmerprofile.model_fields}) if profile_doc else None
    soil = Soiltest(**{k: v for k, v in (soil_doc or {}).items() if k in Soiltest.model_fields}) if soil_doc else None
    obs = Farmobservation(**{k: v for k, v in (obs_doc or {}).items() if k in Farmobservation.model_fields}) if obs_doc else Farmobservation()
    if req.target_crop:
        obs.target_crop = req.target_crop

    risk = simple_disease_pest_risk(obs)
    schedule = irrigation_schedule(profile, soil, obs)
    tips = climate_advice(profile, obs)
    forecast = simple_yield_forecast(profile, soil, obs)
    rotation = rotation_plan(profile)
    trends = market_trends(profile.location_text if profile else None, obs.target_crop if obs else None)

    result = Analysisresult(
        farmer_id=req.farmer_id,
        target_crop=obs.target_crop,
        disease_risk=risk.get("disease", {}),
        pest_risk=risk.get("pest", {}),
        irrigation_schedule=schedule,
        climate_advice=tips,
        yield_forecast=forecast,
        rotation_plan=rotation,
        market_trends=trends,
    )

    inserted_id = create_document(collection_name(Analysisresult), result)
    return {"id": inserted_id, "result": result.model_dump()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
