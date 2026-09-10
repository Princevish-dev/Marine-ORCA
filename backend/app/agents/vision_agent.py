import json
import math

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to calculate the distance between two points in km."""
    R = 6371.0 # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def vision_anomaly_agent(sar_lat: float, sar_lon: float, ais_database: list) -> str:
    """
    The Dark Vessel Vision Agent.
    
    Accepts a mock Sentinel-1 SAR satellite image coordinate (where a ship wake was detected)
    and an active AIS vessel database. Matches the location against the AIS records.
    If no AIS transponder signal exists within a reasonable proximity threshold, it returns
    a high-severity JSON alert tagged as 'DARK_VESSEL_DETECTED'.
    """
    
    # Define a matching threshold distance in kilometers
    # Assume if an AIS signal is within 1 km of the SAR detection, it's the same vessel.
    MATCH_THRESHOLD_KM = 1.0
    
    match_found = False
    
    for vessel in ais_database:
        vessel_lat = vessel.get("latitude")
        vessel_lon = vessel.get("longitude")
        
        if vessel_lat is None or vessel_lon is None:
            continue
            
        dist = calculate_distance(sar_lat, sar_lon, vessel_lat, vessel_lon)
        if dist <= MATCH_THRESHOLD_KM:
            match_found = True
            break
            
    if not match_found:
        alert_payload = {
            "status": "DARK_VESSEL_DETECTED",
            "severity": "HIGH",
            "coordinates": [sar_lat, sar_lon],
            "message": "Computer vision detected a physical ship wake via SAR, but no corresponding AIS transponder signal was found in the area. Potential illegal or unmonitored vessel.",
            "recommended_action": "Alert coastal authorities for immediate interception."
        }
        return json.dumps(alert_payload)
        
    return json.dumps({
        "status": "NORMAL",
        "message": "SAR detection matched with known AIS broadcasting vessel."
    })
