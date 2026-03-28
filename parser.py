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

# Words that should NOT trigger as part of incident keywords.
# These appear in unit names, talkgroup names, and dispatch boilerplate.
NON_INCIDENT_FIRE_CONTEXTS = re.compile(
    r"\b(?:engine|ladder|truck|rescue|squad|medic|battalion|chief|captain|"
    r"tanker|tanger|tender|quint|tower|station|apparatus|department|"
    r"fire\s*(?:ground|department|dispatch|station|chief|page|and\s+engine)|"
    r"(?:mfd|rural|city)\s*[-]?\s*(?:disp|dispatch))\b",
    re.IGNORECASE,
)

# Keyword -> incident type mapping (order matters: first match wins)
# "fire" is intentionally NOT here as a standalone — it false-matches on
# unit names like "ENGINE 6" dispatched on "FIRE GROUND 3".
# Specific fire types (structure fire, vehicle fire, etc.) are still matched.
KEYWORD_INCIDENT_MAP = [
    # Accidents / crashes — must be before generic keywords
    ("accident with injury", "Vehicle Crash - Injury"),
    ("accident with fatality", "Vehicle Crash - Fatal"),
    ("accident", "Vehicle Crash"),
    ("injury crash", "Vehicle Crash - Injury"),
    ("fatal crash", "Vehicle Crash - Fatal"),
    ("rollover", "Vehicle Crash - Rollover"),
    ("vehicle crash", "Vehicle Crash"),
    ("vehicle accident", "Vehicle Crash"),
    ("car accident", "Vehicle Crash"),
    ("car crash", "Vehicle Crash"),
    ("head on", "Vehicle Crash - Head On"),
    ("head-on", "Vehicle Crash - Head On"),
    ("mva", "Vehicle Crash"),
    ("mvc", "Vehicle Crash"),
    # Fire — specific types only (no bare "fire")
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
    # Rescue / entrapment
    ("entrapment", "Entrapment/Rescue"),
    ("pin-in", "Entrapment/Rescue"),
    ("pinned in", "Entrapment/Rescue"),
    ("extrication", "Entrapment/Rescue"),
    # Weapons / violence
    ("shots fired", "Shots Fired"),
    ("shooting", "Shooting"),
    ("gunshot", "Shooting"),
    ("gun", "Person with Gun"),
    ("weapon", "Person with Weapon"),
    ("knife", "Person with Weapon"),
    ("stabbing", "Stabbing"),
    ("assault", "Assault"),
    ("battery", "Battery"),
    # Robbery / burglary / theft
    ("armed robbery", "Armed Robbery"),
    ("bank robbery", "Bank Robbery"),
    ("robbery", "Robbery"),
    ("burglary", "Burglary"),
    ("breaking and entering", "Burglary"),
    ("break-in", "Burglary"),
    ("theft", "Theft"),
    ("stolen", "Theft"),
    # Pursuit
    ("pursuit", "Vehicle Pursuit"),
    ("foot chase", "Foot Pursuit"),
    ("foot pursuit", "Foot Pursuit"),
    # Hazmat
    ("hazmat", "HAZMAT Incident"),
    ("haz-mat", "HAZMAT Incident"),
    ("hazardous material", "HAZMAT Incident"),
    ("gas leak", "Gas Leak"),
    ("carbon monoxide", "Carbon Monoxide"),
    # Explosive / bomb
    ("bomb threat", "Bomb Threat"),
    ("suspicious package", "Suspicious Package"),
    ("explosion", "Explosion"),
    # Missing / abduction
    ("missing person", "Missing Person"),
    ("missing child", "Missing Child"),
    ("amber alert", "AMBER Alert"),
    ("silver alert", "Silver Alert"),
    # Water
    ("drowning", "Drowning"),
    ("water rescue", "Water Rescue"),
    ("swift water", "Swift Water Rescue"),
    # EMS / Medical — specific types first
    ("cardiac arrest", "Cardiac Arrest"),
    ("cardiac", "Cardiac Emergency"),
    ("chest pain", "Chest Pain"),
    ("overdose", "Overdose"),
    ("narcan", "Overdose"),
    ("unresponsive", "Unresponsive Person"),
    ("not breathing", "Respiratory Emergency"),
    ("difficulty breathing", "Respiratory Emergency"),
    ("choking", "Choking"),
    ("seizure", "Seizure"),
    ("stroke", "Stroke"),
    ("headache", "Medical Emergency"),
    ("lift assist", "Lift Assist"),
    ("fall victim", "Fall/Injury"),
    ("fall", "Fall/Injury"),
    ("sick person", "Medical Emergency"),
    ("diabetic", "Medical Emergency"),
    ("allergic reaction", "Medical Emergency"),
    ("abdominal pain", "Medical Emergency"),
    ("bleeding", "Medical Emergency"),
    ("medical", "Medical Emergency"),
    ("ems", "EMS Call"),
    ("ambulance", "EMS Call"),
    ("bls transfer", "BLS Transfer"),
    ("als transfer", "ALS Transfer"),
    ("transfer to", "Patient Transfer"),
    # Law enforcement general
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

# Words that should never be treated as street names in intersections
INTERSECTION_BLACKLIST = {
    "fire", "engine", "rescue", "squad", "medic", "ladder", "truck",
    "tanker", "tanger", "tender", "chief", "captain", "battalion",
    "dispatch", "sheriff", "police", "department", "station", "county",
    "tone", "pager", "test", "disregard", "clear", "respond", "page",
    "ems", "als", "bls", "life", "air", "med", "ground", "rural",
    "city", "status", "signal", "copy", "check", "alert", "warning",
    "speed", "location", "facility", "patient", "hospital", "center",
    "regional", "memorial", "in", "on", "at", "to", "the", "and", "for",
    "with", "from", "by", "cross", "of",
}


def is_pager_test(transcript: str) -> bool:
    """Check if the transcript is a pager test / disregard tone."""
    if not transcript:
        return False
    text_lower = transcript.lower()
    return (
        "pager test" in text_lower
        or "disregard tone" in text_lower
        or ("disregard" in text_lower and "test only" in text_lower)
    )


def extract_county(talkgroup_label: str, system_label: str, transcript: str) -> str:
    """
    Extract county from talkgroup label, system label, or transcript.
    Returns "County Co" format or "UNK CNTY" as fallback.
    """
    tg = (talkgroup_label or "").lower()
    sys_lbl = (system_label or "").lower()
    tx = (transcript or "").lower()

    # 1. Check system label for county names (most reliable — "Delaware County Government")
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if county_lower in sys_lbl:
            return f"{county} Co"

    # 2. Check talkgroup label for county names
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if county_lower in tg:
            return f"{county} Co"

    # 3. Check talkgroup/system labels for city names -> map to county
    for city, county in CITY_TO_COUNTY.items():
        if city in tg or city in sys_lbl:
            return f"{county} Co"

    # 4. Check transcript for county mentions (e.g., "DELAWARE COUNTY")
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
    tg_clean = re.sub(r"\b(fire|pd|police|ems|dispatch|sheriff|so|fd|disp|rural)\b", "", tg).strip()
    tg_clean = re.sub(r"\d+[-]?", "", tg_clean).strip()  # Remove numbers like "18-"
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
    # This is the most reliable pattern — requires a street suffix
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
        street_name = re.sub(r"^\d+\s*[-]?\s*", "", street_part).strip()
        block_num = (num // 100) * 100
        return f"{block_num} Block of {street_name.title()}"

    # Pattern 2: "STATE ROAD ##" or "STATE ROUTE ##" or "SR ##" or "US ##" or "CR ##"
    state_road = re.search(
        rf"(?:state\s+road|state\s+route|sr|us|cr|county\s+road)\s+(\d+)",
        text,
        re.IGNORECASE,
    )
    if state_road:
        road_name = state_road.group(0).strip()
        return f"Area of {road_name.title()}"

    # Pattern 3: Number + direction + name (without explicit suffix)
    # Only match if the street name is capitalized and looks real
    pattern2 = (
        rf"(\d{{1,5}})\s*[-]?\s*"
        rf"({DIRECTIONS})\s+"
        rf"([A-Z][a-zA-Z]{{2,}}(?:\s+[A-Z][a-zA-Z]{{2,}})*)"
    )
    match = re.search(pattern2, text)
    if match:
        num = int(match.group(1))
        direction = match.group(2).strip()
        street = match.group(3).strip()
        # Make sure the street name isn't a dispatch keyword
        if street.lower() not in INTERSECTION_BLACKLIST:
            block_num = (num // 100) * 100
            return f"{block_num} Block of {direction.title()} {street.title()}"

    # Pattern 4: Intersection "X and Y" — only if both look like real street names
    # Require at least one side to have a street suffix or direction
    intersection = re.search(
        rf"(?:{DIRECTIONS}\s+)?([A-Z][a-zA-Z]{{2,}}(?:\s+{STREET_SUFFIXES})?)"
        rf"\s+(?:and|&)\s+"
        rf"(?:{DIRECTIONS}\s+)?([A-Z][a-zA-Z]{{2,}}(?:\s+{STREET_SUFFIXES})?)",
        text,
    )
    if intersection:
        street1 = intersection.group(1).strip()
        street2 = intersection.group(2).strip()
        # Both street names must NOT be in the blacklist
        if (
            street1.lower() not in INTERSECTION_BLACKLIST
            and street2.lower() not in INTERSECTION_BLACKLIST
            and len(street1) > 2
            and len(street2) > 2
        ):
            full_match = intersection.group(0).strip()
            return f"Area of {full_match.title()}"

    return "No Address"


def _is_standalone_fire_keyword(transcript: str) -> bool:
    """
    Check if "fire" in the transcript refers to an actual fire incident,
    not just a unit name or talkgroup reference.

    Returns True if "fire" appears to describe an actual fire.
    """
    text_lower = transcript.lower()

    # If "fire" doesn't appear at all, no match
    if "fire" not in text_lower:
        return False

    # Strip out known non-incident fire references (unit names, talkgroups, etc.)
    cleaned = NON_INCIDENT_FIRE_CONTEXTS.sub("", text_lower)
    # Also strip "respond on ... fire ground" patterns
    cleaned = re.sub(r"respond\s+on\s+.*?fire\s+ground\s+\d+", "", cleaned)
    # Strip "X fire" where X is a proper name (department name)
    cleaned = re.sub(r"\b[a-z]+\s+fire\b", "", cleaned)

    # Check if "fire" still remains in the cleaned text
    return bool(re.search(r"\bfire\b", cleaned))


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

    # 4. Check for standalone "fire" only after all specific keywords failed
    # This avoids matching "fire" in unit names like "DUNCAN FIRE AND ENGINE"
    if _is_standalone_fire_keyword(transcript):
        return "Fire"

    # 5. Check alert metadata as last resort
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
    Returns None if the alert should be suppressed (pager test, etc.).
    """
    # Filter out pager tests
    if is_pager_test(transcript):
        return None

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
