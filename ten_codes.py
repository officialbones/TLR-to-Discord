"""Indiana 10-codes and signal codes used by law enforcement."""

import re

# Full Indiana 10-codes
TEN_CODES = {
    "10-0": "Fatality",
    "10-1": "Unable To Copy",
    "10-2": "Signals Good",
    "10-3": "Stop Transmitting",
    "10-4": "Acknowledgment/Status OK",
    "10-5": "Relay",
    "10-6": "Busy, Stand By Unless Urgent",
    "10-7": "Out-Of-Service",
    "10-8": "In Service",
    "10-9": "Repeat",
    "10-10": "Fight In Progress",
    "10-11": "Dog Case",
    "10-12": "Stand By",
    "10-13": "Weather And Road Report",
    "10-14": "Report Of Prowler",
    "10-15": "Civil Disturbance",
    "10-16": "Domestic Trouble",
    "10-17": "Complainant",
    "10-18": "Urgent",
    "10-19": "Go to Station",
    "10-20": "Location",
    "10-21": "Call",
    "10-22": "Disregard",
    "10-23": "Arrived At Scene",
    "10-24": "Assignment Completed",
    "10-25": "Report to/Meet",
    "10-26": "Detaining Subject",
    "10-27": "Drivers License Information",
    "10-28": "Vehicle Registration Info",
    "10-29": "Check Records For Wanted",
    "10-30": "Illegal Use Of Radio",
    "10-31": "Crime In Progress",
    "10-32": "Gun",
    "10-33": "Emergency - Stand By",
    "10-34": "Riot",
    "10-35": "Major Crime Alert",
    "10-36": "Correct Time",
    "10-37": "Investigate Suspicious Vehicle",
    "10-38": "Stopping Suspicious Vehicle",
    "10-39": "Urgent-Use Lights And Siren",
    "10-40": "Silent Run-No Lights Or Siren",
    "10-41": "Start of Shift",
    "10-42": "End of Shift",
    "10-43": "Information",
    "10-44": "Request Permission To Leave Patrol",
    "10-45": "Animal Carcass In Road",
    "10-46": "Assist Motorist",
    "10-47": "Emergency Road Repair",
    "10-48": "Traffic Control",
    "10-49": "Traffic Signal Out",
    "10-50": "Accident",
    "10-50F": "Accident - Fatal",
    "10-50PI": "Accident - Person Injured",
    "10-50PD": "Accident - Property Damage",
    "10-51": "Wrecker Needed",
    "10-52": "Ambulance Needed",
    "10-53": "Road Blocked",
    "10-54": "Livestock on Roadway",
    "10-55": "Intoxicated Driver",
    "10-56": "Intoxicated Pedestrian",
    "10-57": "Hit & Run Accident",
    "10-58": "Direct Traffic",
    "10-59": "Convoy Or Escort",
    "10-60": "Squad in Vicinity",
    "10-61": "Personnel in Vicinity",
    "10-62": "Reply To Message",
    "10-63": "Prepare To Make Written Copy",
    "10-64": "Local Message",
    "10-65": "Net Message",
    "10-66": "Message Cancellation",
    "10-67": "Clear for Net Message",
    "10-68": "Dispatch Information",
    "10-69": "Message Received",
    "10-70": "Fire Alarm",
    "10-71": "Advise Nature of Fire",
    "10-72": "Report Alarm Progress",
    "10-73": "Smoke Report",
    "10-74": "Negative",
    "10-75": "In Contact With",
    "10-76": "En Route",
    "10-77": "ETA",
    "10-78": "Need Assistance",
    "10-79": "Notify Coroner",
    "10-80": "Alarm",
    "10-81": "Breathalyzer Report",
    "10-82": "Reserve Lodging",
    "10-83": "School Crossing Detail",
    "10-84": "ETA",
    "10-85": "Arrival Delayed",
    "10-86": "Operator on Duty",
    "10-87": "Pick Up",
    "10-88": "Advise Telephone Number",
    "10-89": "Bomb Threat",
    "10-90": "Bank Alarm",
    "10-91": "Pick up Subject",
    "10-92": "Illegally Parked Vehicle",
    "10-93": "Blockade",
    "10-94": "Drag Racing",
    "10-95": "Subject in Custody",
    "10-96": "Mental Subject",
    "10-97": "Test Signal",
    "10-98": "Prison Or Jail Break",
    "10-99": "Records Indicated Wanted",
    "10-100": "Emergency - Hold all but Emergency Traffic",
}

# Indiana signal codes
SIGNAL_CODES = {
    "signal 1": "Call Office",
    "signal 2": "Call HQ",
    "signal 3": "Call the Post",
    "signal 4": "Report to HQ",
    "signal 5": "Go to the Post",
    "signal 6": "Call Person/Agency",
    "signal 7": "Emergency",
    "signal 8": "Meet",
    "signal 9": "Disregard",
    "signal 10": "Rush (Lights/Siren)",
    "signal 11": "Confidential Information",
    "signal 12": "Reply by Phone",
    "signal 13": "Army Convoy",
    "signal 14": "Plain Clothes",
    "signal 15": "Cannot Comment on Air",
    "signal 16": "Aircraft Accident",
    "signal 17": "Give Emergency Right of Way",
    "signal 18": "Target Practice",
    "signal 19": "Truck Check",
    "signal 20": "Car Wash",
    "signal 21": "Car Lube",
    "signal 22": "Car Repair",
    "signal 23": "Speeding Vehicle",
    "signal 24": "Vehicle & Occupants Detained",
    "signal 25": "Regular Post Meeting",
    "signal 26": "Bringing Subjects to Court",
    "signal 27": "Traffic Stop",
    "signal 28": "Bank Detail",
    "signal 29": "Post Meeting",
    "signal 30": "Special Patrol Assignment",
    "signal 31": "Traffic Congestion",
    "signal 32": "Check all Records for Subject",
    "signal 33": "Known Burglar",
    "signal 34": "Possible Mental Case",
    "signal 35": "Post Inspection",
    "signal 36": "Advise Work Schedule",
    "signal 37": "Any Messages?",
    "signal 38": "No Messages",
    "signal 39": "Post Inspection",
    "signal 40": "Subject/Item is Wanted",
    "signal 41": "Lie Detector Available?",
    "signal 42": "Breathalyzer Available?",
    "signal 43j1": "Have Personnel",
    "signal 43j2": "Have Property in Possession",
    "signal 43j3": "Have Prisoner in Custody",
    "signal 43j4": "Have Papers in Possession",
    "signal 44": "Advise Traffic Conditions",
    "signal 45": "Give FCC Call Sign",
    "signal 46": "Pursuit in Progress",
    "signal 47": "Escort",
    "signal 48": "Visitors Present?",
    "signal 49": "Platoon Standby Alert",
    "signal 50": "Activate Riot Control Platoon",
    "signal 51": "Running Radar in Area",
    "signal 52": "HAZMAT Incident",
    "signal 54": "Overtime",
    "signal 55": "Activity Report",
    "signal 60": "Drugs",
    "signal 61": "Homicide",
    "signal 63": "Firearm",
    "signal 66": "Requested Service Unavailable",
    "signal 70": "Sex Crime",
    "signal 80": "Not on File/Not Wanted",
    "signal 88": "Microphone Keyed, No Voice",
    "signal 89": "Accidentally Keyed Microphone",
    "signal 100": "Emergency - Hold all but Emergency Traffic",
}

# 10-codes that indicate specific incident types (for classification)
TEN_CODE_INCIDENT_MAP = {
    "10-0": "Fatality",
    "10-10": "Fight In Progress",
    "10-14": "Prowler Report",
    "10-15": "Civil Disturbance",
    "10-16": "Domestic Disturbance",
    "10-31": "Crime In Progress",
    "10-32": "Person with Gun",
    "10-33": "Emergency",
    "10-34": "Riot",
    "10-35": "Major Crime Alert",
    "10-37": "Suspicious Vehicle",
    "10-45": "Animal Carcass In Road",
    "10-46": "Assist Motorist",
    "10-50": "Vehicle Crash",
    "10-50F": "Vehicle Crash - Fatal",
    "10-50PI": "Vehicle Crash - Injury",
    "10-50PD": "Vehicle Crash - Property Damage",
    "10-52": "Ambulance Needed",
    "10-53": "Road Blocked",
    "10-54": "Livestock on Roadway",
    "10-55": "Intoxicated Driver",
    "10-57": "Hit & Run",
    "10-70": "Fire Alarm",
    "10-73": "Smoke Report",
    "10-78": "Need Assistance",
    "10-79": "Notify Coroner",
    "10-89": "Bomb Threat",
    "10-90": "Bank Alarm",
    "10-94": "Drag Racing",
    "10-96": "Mental Subject",
    "10-98": "Prison/Jail Break",
}

SIGNAL_INCIDENT_MAP = {
    "signal 7": "Emergency",
    "signal 16": "Aircraft Accident",
    "signal 23": "Speeding Vehicle",
    "signal 33": "Known Burglar",
    "signal 34": "Possible Mental Case",
    "signal 40": "Subject/Item Wanted",
    "signal 46": "Vehicle Pursuit",
    "signal 52": "HAZMAT Incident",
    "signal 60": "Drug Incident",
    "signal 61": "Homicide",
    "signal 63": "Firearm Incident",
    "signal 70": "Sex Crime",
    "signal 100": "Emergency",
}


def normalize_ten_code(raw: str) -> str | None:
    """
    Normalize a potential 10-code string.
    Handles: '10-50', '1050', '104' -> '10-4', '10 50' -> '10-50'
    Returns the normalized code if valid, None otherwise.
    """
    cleaned = raw.strip().upper()

    # Already has hyphen: "10-50", "10-50PI"
    if re.match(r"^10-\d{1,3}\w{0,2}$", cleaned):
        key = cleaned
        if key in TEN_CODES or key.split("-")[0] + "-" + key.split("-")[1][:2] in TEN_CODES:
            return key if key in TEN_CODES else None
        return key if key in TEN_CODES else None

    # Has space: "10 50"
    if re.match(r"^10\s+\d{1,3}\w{0,2}$", cleaned):
        parts = cleaned.split()
        key = f"10-{parts[1]}"
        return key if key in TEN_CODES else None

    # No separator: "1050", "104", "1050PI"
    if re.match(r"^10\d{1,3}\w{0,2}$", cleaned):
        after_10 = cleaned[2:]
        key = f"10-{after_10}"
        return key if key in TEN_CODES else None

    return None


def lookup_ten_code(code: str) -> str | None:
    """Look up a 10-code and return its description."""
    normalized = normalize_ten_code(code)
    if normalized:
        return TEN_CODES.get(normalized)
    return None


def find_ten_codes_in_text(text: str) -> list[tuple[str, str, str]]:
    """
    Find all potential 10-codes in transcript text.
    Returns list of (raw_match, normalized_code, description).
    """
    results = []

    # Match explicit 10-codes: "10-50", "10-50PI", "10 50"
    for m in re.finditer(r"\b10[-\s](\d{1,3}(?:\s*[A-Za-z]{1,2})?)\b", text, re.IGNORECASE):
        raw = m.group(0)
        normalized = normalize_ten_code(raw)
        if normalized and normalized in TEN_CODES:
            results.append((raw, normalized, TEN_CODES[normalized]))

    # Match bare numbers that could be 10-codes: "104", "1050"
    # Only match 3-4 digit numbers starting with 10
    for m in re.finditer(r"\b(10\d{1,2}(?:[A-Za-z]{1,2})?)\b", text):
        raw = m.group(0)
        # Skip if already caught by explicit pattern
        if any(raw in r[0] for r in results):
            continue
        normalized = normalize_ten_code(raw)
        if normalized and normalized in TEN_CODES:
            # Context check: avoid treating addresses/unit numbers as 10-codes
            # If the number is preceded by "#" or "unit" or "apt", skip it
            start = max(0, m.start() - 15)
            preceding = text[start : m.start()].lower()
            if any(word in preceding for word in ["#", "unit", "apt", "apartment", "suite", "room"]):
                continue
            results.append((raw, normalized, TEN_CODES[normalized]))

    return results


def find_signal_codes_in_text(text: str) -> list[tuple[str, str, str]]:
    """
    Find signal codes in transcript text.
    Returns list of (raw_match, normalized_code, description).
    """
    results = []
    text_lower = text.lower()

    for m in re.finditer(r"\bsignal\s+(\d{1,3}(?:j\d)?)\b", text_lower):
        raw = m.group(0)
        key = raw.strip()
        if key in SIGNAL_CODES:
            results.append((m.group(0), key, SIGNAL_CODES[key]))

    return results
