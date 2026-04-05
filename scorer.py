# scorer.py
from haversine import haversine

# Constants
PRIORITY_BONUS = {1: 0.0, 2: 0.1, 3: 0.25, 4: 0.45, 5: 0.70}
ENERGY_PER_KM = 0.05          # Battery % consumed per km
BATTERY_SAFETY_MARGIN = 1.25  # 25% extra battery required for safety

def compute_score(drone, pharmacy, user_lat, user_lon, priority):
    """Calculate distance and final score for one drone-pharmacy pair"""
    d1 = haversine(drone["lat"], drone["lon"], pharmacy["lat"], pharmacy["lon"])
    d2 = haversine(pharmacy["lat"], pharmacy["lon"], user_lat, user_lon)
    total_dist = d1 + d2

    energy_cost = total_dist * ENERGY_PER_KM
    bonus = PRIORITY_BONUS.get(priority, 0.0)

    # Lower score = better assignment
    score = round(total_dist + energy_cost - bonus, 4)

    return score, round(d1, 3), round(d2, 3)


def assign(request, drones, pharmacies):
    """
    Main AI Assignment Function
    request = {"lat": float, "lon": float, "supply": str, "priority": int}
    Returns (best_assignment_dict, status_message)
    """
    user_lat = request["lat"]
    user_lon = request["lon"]
    supply = request["supply"]
    priority = request["priority"]

    # 1. Filter pharmacies that have the supply and are open
    valid_pharmacies = [
        p for p in pharmacies
        if supply in p.get("stock", []) and p.get("open", False)
    ]

    if not valid_pharmacies:
        return None, "no_pharmacy_has_supply"

    # 2. Filter idle drones with enough battery
    valid_drones = []
    for d in drones:
        if d.get("status") != "idle":
            continue

        # Calculate minimum energy needed to this user (via closest pharmacy)
        min_pharm_dist = min(
            haversine(d["lat"], d["lon"], p["lat"], p["lon"])
            for p in valid_pharmacies
        )
        user_dist = haversine(d["lat"], d["lon"], user_lat, user_lon)
        energy_needed = (min_pharm_dist + user_dist) * ENERGY_PER_KM

        if d["battery_pct"] >= energy_needed * BATTERY_SAFETY_MARGIN * 100:
            valid_drones.append(d)

    if not valid_drones:
        return None, "no_drones_available"

    # 3. Find the best drone + pharmacy combination
    best_score = float("inf")
    best = None

    for drone in valid_drones:
        for pharmacy in valid_pharmacies:
            score, d1, d2 = compute_score(drone, pharmacy, user_lat, user_lon, priority)

            if score < best_score:
                best_score = score
                best = {
                    "drone_id": drone["id"],
                    "drone_battery": drone["battery_pct"],
                    "pharmacy_id": pharmacy["id"],
                    "pharmacy_name": pharmacy["name"],
                    "drone_to_pharmacy_km": d1,
                    "pharmacy_to_user_km": d2,
                    "total_distance_km": round(d1 + d2, 3),
                    "score": score,
                    "eta_minutes": round((d1 + d2) / 0.085),   # ~5.1 km/min drone speed
                    "priority": priority,
                    "reason": f"Best overall: short distance + good battery ({drone['battery_pct']}%) + priority bonus"
                }

    return best, "ok"


# ====================== TEST THE AI MODEL ======================
if __name__ == "__main__":
    import json

    # Load your real data
    with open("data/drones.json", encoding="utf-8") as f:
        drones = json.load(f)
    with open("data/pharmacies.json", encoding="utf-8") as f:
        pharmacies = json.load(f)

    # Example user request
    request = {
        "lat": 36.7950,
        "lon": 10.1780,
        "supply": "insulin",
        "priority": 4
    }

    result, status = assign(request, drones, pharmacies)

    print("=== AI ASSIGNMENT RESULT ===")
    if status == "ok":
        print(json.dumps(result, indent=2))
    else:
        print(f"Error: {status}")