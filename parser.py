"""Parse dispatch transcripts into structured alert format."""

import re
import logging
from ten_codes import (
    find_ten_codes_in_text,
    find_signal_codes_in_text,
    TEN_CODE_INCIDENT_MAP,
    SIGNAL_INCIDENT_MAP,
)

logger = logging.getLogger(__name__)

# Indiana counties
INDIANA_COUNTIES = [
    "Adams", "Allen", "Bartholomew", "Benton", "Blackford", "Boone", "Brown",
    "Carroll", "Cass", "Clark", "Clay", "Clinton", "Crawford", "Daviess",
    "Dearborn", "Decatur", "DeKalb", "Delaware", "Dubois", "Elkhart",
    "Fayette", "Floyd", "Fountain", "Franklin", "Fulton", "Gibson", "Grant",
    "Greene", "Hamilton", "Hancock", "Harrison", "Hendricks", "Henry",
    "Howard", "Huntington", "Jackson", "Jasper", "Jay", "Jefferson",
    "Jennings", "Johnson", "Knox", "Kosciusko", "LaGrange", "Lake",
    "LaPorte", "Lawrence", "Madison", "Marion", "Marshall", "Martin",
    "Miami", "Monroe", "Montgomery", "Morgan", "Newton", "Noble", "Ohio",
    "Orange", "Owen", "Parke", "Perry", "Pike", "Porter", "Posey",
    "Pulaski", "Putnam", "Randolph", "Ripley", "Rush", "Scott", "Shelby",
    "Spencer", "St. Joseph", "Starke", "Steuben", "Sullivan", "Switzerland",
    "Tippecanoe", "Tipton", "Union", "Vanderburgh", "Vermillion", "Vigo",
    "Wabash", "Warren", "Warrick", "Washington", "Wayne", "Wells", "White",
    "Whitley",
]

# Major Indiana cities -> county mapping
CITY_TO_COUNTY = {
    "indianapolis": "Marion",
    "fort wayne": "Allen",
    "evansville": "Vanderburgh",
    "south bend": "St. Joseph",
    "carmel": "Hamilton",
    "fishers": "Hamilton",
    "bloomington": "Monroe",
    "hammond": "Lake",
    "gary": "Lake",
    "lafayette": "Tippecanoe",
    "west lafayette": "Tippecanoe",
    "muncie": "Delaware",
    "terre haute": "Vigo",
    "kokomo": "Howard",
    "noblesville": "Hamilton",
    "anderson": "Madison",
    "greenwood": "Johnson",
    "elkhart": "Elkhart",
    "mishawaka": "St. Joseph",
    "lawrence": "Marion",
    "jeffersonville": "Clark",
    "new albany": "Floyd",
    "columbus": "Bartholomew",
    "portage": "Porter",
    "valparaiso": "Porter",
    "michigan city": "LaPorte",
    "richmond": "Wayne",
    "goshen": "Elkhart",
    "crown point": "Lake",
    "merrillville": "Lake",
    "plainfield": "Hendricks",
    "avon": "Hendricks",
    "brownsburg": "Hendricks",
    "zionsville": "Boone",
    "westfield": "Hamilton",
    "greenfield": "Hancock",
    "shelbyville": "Shelby",
    "franklin": "Johnson",
    "seymour": "Jackson",
    "bedford": "Lawrence",
    "jasper": "Dubois",
    "vincennes": "Knox",
    "logansport": "Cass",
    "marion": "Grant",
    "peru": "Miami",
    "wabash": "Wabash",
    "huntington": "Huntington",
    "auburn": "DeKalb",
    "warsaw": "Kosciusko",
    "plymouth": "Marshall",
    "connersville": "Fayette",
    "crawfordsville": "Montgomery",
    "lebanon": "Boone",
    "martinsville": "Morgan",
    "mooresville": "Morgan",
    "greencastle": "Putnam",
    "brazil": "Clay",
    "linton": "Greene",
    "washington": "Daviess",
    "scottsburg": "Scott",
    "madison": "Jefferson",
    "batesville": "Ripley",
    "rushville": "Rush",
    "brookville": "Franklin",
    "delphi": "Carroll",
    "monticello": "White",
    "rensselaer": "Jasper",
    "kentland": "Newton",
    "salem": "Washington",
    "paoli": "Orange",
    "tell city": "Perry",
    "princeton": "Gibson",
    "mt. vernon": "Posey",
    "mount vernon": "Posey",
    "sullivan": "Sullivan",
    "spencer": "Owen",
    "rockville": "Parke",
    "newport": "Vermillion",
    "williamsport": "Warren",
    "portland": "Jay",
    "hartford city": "Blackford",
    "bluffton": "Wells",
    "decatur": "Adams",
    "columbia city": "Whitley",
    "albion": "Noble",
    "angola": "Steuben",
    "lagrange": "LaGrange",
    "knox": "Starke",
    "winamac": "Pulaski",
    "rochester": "Fulton",
    "tipton": "Tipton",
    "liberty": "Union",
    "rising sun": "Ohio",
    "vevay": "Switzerland",
    "corydon": "Harrison",
    "english": "Crawford",
    "shoals": "Martin",
    "dale": "Spencer",
    "boonville": "Warrick",
    "newburgh": "Warrick",
}

# Keyword -> incident type mapping (order matters: first match wins)
KEYWORD_INCIDENT_MAP = [
    ("structure fire", "Structure Fire"),
    ("house fire", "Structure Fire"),
    ("building fire", "Structure Fire"),
    ("apartment fire", "Structure Fire"),
    ("commercial fire", "Structure Fire"),
    ("residential fire", "Structure Fire"),
    ("vehicle fire", "Vehicle Fire"),
    ("car fire", "Vehicle Fire"),
    ("truck fire", "Vehicle Fire"),
    ("grass fire", "Grass/Brush Fire"),
    ("brush fire", "Grass/Brush Fire"),
    ("wildland fire", "Wildland Fire"),
    ("dumpster fire", "Dumpster Fire"),
    ("fire", "Fire"),
    ("entrapment", "Entrapment/Rescue"),
    ("pin-in", "Entrapment/Rescue"),
    ("pinned in", "Entrapment/Rescue"),
    ("extrication", "Entrapment/Rescue"),
    ("rollover", "Vehicle Crash - Rollover"),
    ("vehicle crash", "Vehicle Crash"),
    ("vehicle accident", "Vehicle Crash"),
    ("car accident", "Vehicle Crash"),
    ("car crash", "Vehicle Crash"),
    ("head on", "Vehicle Crash - Head On"),
    ("head-on", "Vehicle Crash - Head On"),
    ("mva", "Vehicle Crash"),
    ("mvc", "Vehicle Crash"),
    ("accident", "Vehicle Crash"),
    ("shooting", "Shooting"),
    ("shots fired", "Shots Fired"),
    ("gunshot", "Shooting"),
    ("stabbing", "Stabbing"),
    ("assault", "Assault"),
    ("battery", "Battery"),
    ("robbery", "Robbery"),
    ("armed robbery", "Armed Robbery"),
    ("bank robbery", "Bank Robbery"),
    ("burglary", "Burglary"),
    ("breaking and entering", "Burglary"),
    ("break-in", "Burglary"),
    ("theft", "Theft"),
    ("stolen", "Theft"),
    ("pursuit", "Vehicle Pursuit"),
    ("foot chase", "Foot Pursuit"),
    ("foot pursuit", "Foot Pursuit"),
    ("hazmat", "HAZMAT Incident"),
    ("haz-mat", "HAZMAT Incident"),
    ("hazardous material", "HAZMAT Incident"),
    ("gas leak", "Gas Leak"),
    ("carbon monoxide", "Carbon Monoxide"),
    ("bomb threat", "Bomb Threat"),
    ("suspicious package", "Suspicious Package"),
    ("explosion", "Explosion"),
    ("missing person", "Missing Person"),
    ("missing child", "Missing Child"),
    ("amber alert", "AMBER Alert"),
    ("silver alert", "Silver Alert"),
    ("drowning", "Drowning"),
    ("water rescue", "Water Rescue"),
    ("swift water", "Swift Water Rescue"),
    ("overdose", "Overdose"),
    ("od", "Overdose"),
    ("narcan", "Overdose"),
    ("cardiac arrest", "Cardiac Arrest"),
    ("cardiac", "Cardiac Emergency"),
    ("chest pain", "Chest Pain"),
    ("unresponsive", "Unresponsive Person"),
    ("not breathing", "Respiratory Emergency"),
    ("difficulty breathing", "Respiratory Emergency"),
    ("choking", "Choking"),
    ("seizure", "Seizure"),
    ("stroke", "Stroke"),
    ("fall", "Fall/Injury"),
    ("medical", "Medical Emergency"),
    ("ems", "EMS Call"),
    ("ambulance", "EMS Call"),
    ("domestic", "Domestic Disturbance"),
    ("disturbance", "Disturbance"),
    ("trespassing", "Trespassing"),
    ("trespass", "Trespassing"),
    ("suspicious person", "Suspicious Person"),
    ("suspicious vehicle", "Suspicious Vehicle"),
    ("welfare check", "Welfare Check"),
    ("well-being check", "Welfare Check"),
    ("alarm", "Alarm"),
]

# Street suffixes for address matching
STREET_SUFFIXES = (
    r"(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|"
    r"lane|ln|court|ct|way|place|pl|pike|highway|hwy|trail|trl|"
    r"circle|cir|parkway|pkwy|terrace|ter|path|run|ridge|"
    r"crossing|xing|loop|row|square|sq)"
)

# Directional prefixes
DIRECTIONS = r"(?:north|south|east|west|n\.?|s\.?|e\.?|w\.?|northeast|northwest|southeast|southwest|ne|nw|se|sw)"


def extract_county(talkgroup_label: str, system_label: str, transcript: str) -> str:
    """
    Extract county from talkgroup label, system label, or transcript.
    Returns "County Co" format or "UNK CNTY" as fallback.
    """
    tg = (talkgroup_label or "").lower()
    sys_lbl = (system_label or "").lower()
    tx = (transcript or "").lower()

    # 1. Check talkgroup label for county names
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        # Match "Marion Co", "Marion County", or just the county name in the label
        if county_lower in tg:
            return f"{county} Co"

    # 2. Check system label for county names
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if county_lower in sys_lbl:
            return f"{county} Co"

    # 3. Check talkgroup/system labels for city names -> map to county
    for city, county in CITY_TO_COUNTY.items():
        if city in tg or city in sys_lbl:
            return f"{county} Co"

    # 4. Check transcript for county mentions
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if re.search(rf"\b{re.escape(county_lower)}\s+count", tx):
            return f"{county} Co"

    # 5. Check transcript for city mentions -> map to county
    for city, county in CITY_TO_COUNTY.items():
        if re.search(rf"\b{re.escape(city)}\b", tx):
            return f"{county} Co"

    # 6. Try to extract city name from talkgroup label as-is
    # Many labels are like "City Name Fire" or "City Name PD"
    tg_clean = re.sub(r"\b(fire|pd|police|ems|dispatch|sheriff|so|fd)\b", "", tg).strip()
    if tg_clean and len(tg_clean) > 2:
        return tg_clean.title()

    return "UNK CNTY"


def extract_address(transcript: str) -> str:
    """
    Extract street address from transcript and convert to block format.
    Returns "X00 Block of Street Name" or "No Address".
    """
    if not transcript:
        return "No Address"

    text = transcript

    # Pattern 1: Number + optional direction + street name + suffix
    pattern1 = (
        rf"(\d{{1,5}})\s*[-]?\s*"
        rf"(?:{DIRECTIONS}\s+)?"
        rf"((?:[A-Za-z]+\s?){{1,4}})"
        rf"\s*{STREET_SUFFIXES}"
    )
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        street_part = match.group(0)
        # Extract the street name portion (everything after the number)
        street_name = re.sub(r"^\d+\s*[-]?\s*", "", street_part).strip()
        block_num = (num // 100) * 100
        return f"{block_num} Block of {street_name.title()}"

    # Pattern 2: Number + direction + name (without explicit suffix)
    # e.g., "1917 West Memorial"
    pattern2 = (
        rf"(\d{{1,5}})\s*[-]?\s*"
        rf"({DIRECTIONS})\s+"
        rf"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)"
    )
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        direction = match.group(2).strip()
        street = match.group(3).strip()
        block_num = (num // 100) * 100
        return f"{block_num} Block of {direction.title()} {street.title()}"

    # Pattern 3: Intersection "X and Y" or "X & Y"
    intersection = re.search(
        rf"({DIRECTIONS}\s+)?([A-Z][a-zA-Z]+(?:\s+{STREET_SUFFIXES})?)"
        rf"\s+(?:and|&)\s+"
        rf"({DIRECTIONS}\s+)?([A-Z][a-zA-Z]+(?:\s+{STREET_SUFFIXES})?)",
        text,
        re.IGNORECASE,
    )
    if intersection:
        parts = [g for g in intersection.groups() if g]
        cross = " & ".join(p.strip().title() for p in parts if len(p.strip()) > 1)
        if cross:
            return f"Area of {cross}"

    # Pattern 4: Just a number + street name (common in radio)
    pattern4 = rf"(\d{{2,5}})\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){{0,2}})"
    match = re.search(pattern4, text)
    if match:
        num = int(match.group(1))
        street = match.group(2).strip()
        # Avoid matching things that aren't addresses (unit numbers, etc.)
        if num >= 100 and len(street) > 2:
            block_num = (num // 100) * 100
            return f"{block_num} Block of {street.title()}"

    return "No Address"


def classify_incident(alert: dict, transcript: str) -> str:
    """
    Classify the incident type from 10-codes, keywords, and alert metadata.
    """
    if not transcript:
        if alert.get("toneDetected"):
            return "Tone Alert"
        return "Dispatch"

    text_lower = transcript.lower()

    # 1. Check for 10-codes that map to incident types
    ten_codes = find_ten_codes_in_text(transcript)
    for _raw, code, _desc in ten_codes:
        if code in TEN_CODE_INCIDENT_MAP:
            return TEN_CODE_INCIDENT_MAP[code]

    # 2. Check for signal codes that map to incident types
    signals = find_signal_codes_in_text(transcript)
    for _raw, code, _desc in signals:
        if code in SIGNAL_INCIDENT_MAP:
            return SIGNAL_INCIDENT_MAP[code]

    # 3. Keyword matching (first match wins, list is priority-ordered)
    for keyword, incident_type in KEYWORD_INCIDENT_MAP:
        if keyword in text_lower:
            return incident_type

    # 4. Check alert metadata
    alert_type = (alert.get("alertType") or "").lower()
    if "tone" in alert_type or alert.get("toneDetected"):
        return "Tone Alert"
    if "keyword" in alert_type:
        return "Keyword Alert"

    return "Dispatch"


def parse_alert(alert: dict, transcript: str) -> dict:
    """
    Parse a transcript into structured dispatch format.
    Returns dict with county, address, incident_type, summary, formatted.
    """
    tg_label = alert.get("talkgroupLabel", "") or ""
    sys_label = alert.get("systemLabel", "") or ""

    county = extract_county(tg_label, sys_label, transcript)
    address = extract_address(transcript)
    incident_type = classify_incident(alert, transcript)
    summary = transcript if transcript else "(No transcription available)"

    formatted = f"{county} | {address} | {incident_type} | {summary}"

    return {
        "county": county,
        "address": address,
        "incident_type": incident_type,
        "summary": summary,
        "formatted": formatted,
    }
