"""
Database Schemas for Smart Farming Assistant

Each Pydantic model below corresponds to a MongoDB collection (lowercased class name).
Use these for validating and storing farmer data, observations, and analysis results.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class Farmerprofile(BaseModel):
    """
    Farmer profiles
    Collection name: "farmerprofile"
    """
    name: str = Field(..., description="Farmer's full name")
    phone: Optional[str] = Field(None, description="Contact number")
    location_text: Optional[str] = Field(None, description="Village/City, District, State")
    gps_lat: Optional[float] = Field(None, description="Latitude")
    gps_lng: Optional[float] = Field(None, description="Longitude")
    farm_size_ha: Optional[float] = Field(None, ge=0, description="Farm size in hectares")
    soil_type: Optional[str] = Field(None, description="Soil type: sandy, loamy, clayey, silt, peat, chalky")
    elevation_m: Optional[float] = Field(None, ge=-430, le=9000, description="Elevation in meters")
    irrigation_method: Optional[str] = Field(None, description="drip, sprinkler, flood, furrow, rainfed")
    water_source: Optional[str] = Field(None, description="canal, borewell, rainwater, river, pond, municipal")
    farming_practices: Optional[List[str]] = Field(default_factory=list, description="organic, no-till, mulching, cover crops, IPM, etc.")
    crop_history: Optional[List[str]] = Field(default_factory=list, description="Recent crops grown")
    surrounding_env: Optional[str] = Field(None, description="near waterbody, forest edge, urban area, open field, etc.")


class Soiltest(BaseModel):
    """
    Soil test reports
    Collection name: "soiltest"
    """
    farmer_id: Optional[str] = Field(None, description="Related farmer profile id")
    ph: Optional[float] = Field(None, ge=0, le=14, description="Soil pH")
    nitrogen_ppm: Optional[float] = Field(None, ge=0, description="Nitrogen in ppm")
    phosphorus_ppm: Optional[float] = Field(None, ge=0, description="Phosphorus in ppm")
    potassium_ppm: Optional[float] = Field(None, ge=0, description="Potassium in ppm")
    organic_matter_pct: Optional[float] = Field(None, ge=0, le=100, description="Organic matter percent")
    ec_dS_m: Optional[float] = Field(None, ge=0, description="Electrical conductivity")


class Farmobservation(BaseModel):
    """
    Field observations and weather
    Collection name: "farmobservation"
    """
    farmer_id: Optional[str] = Field(None)
    target_crop: Optional[str] = Field(None, description="Crop being planned or grown now")
    temp_c: Optional[float] = Field(None, description="Air temperature in Celsius")
    humidity_pct: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity percent")
    rainfall_mm: Optional[float] = Field(None, ge=0, description="Recent rainfall in mm (last 24-72h)")
    wind_kph: Optional[float] = Field(None, ge=0, description="Wind speed in kph")
    pest_signs: Optional[List[str]] = Field(default_factory=list, description="Observed pest signs")
    disease_signs: Optional[List[str]] = Field(default_factory=list, description="Observed disease signs")
    notes: Optional[str] = Field(None)


class Analysisresult(BaseModel):
    """
    Results of analyses for a session
    Collection name: "analysisresult"
    """
    farmer_id: Optional[str] = Field(None)
    target_crop: Optional[str] = Field(None)
    disease_risk: dict = Field(default_factory=dict)
    pest_risk: dict = Field(default_factory=dict)
    irrigation_schedule: dict = Field(default_factory=dict)
    climate_advice: List[str] = Field(default_factory=list)
    yield_forecast: dict = Field(default_factory=dict)
    rotation_plan: List[str] = Field(default_factory=list)
    market_trends: List[dict] = Field(default_factory=list)
