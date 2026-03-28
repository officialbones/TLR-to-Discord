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
NON_INCIDENT_FIRE_CONTEXTS = re.compile(
    r"\b(?:engine|ladder|truck|rescue|squad|medic|battalion|chief|captain|"
    r"tanker|tanger|tender|quint|tower|station|apparatus|department|"
    r"fire\s*(?:ground|department|dispatch|station|chief|page|and\s+engine)|"
    r"(?:mfd|rural|city)\s*[-]?\s*(?:disp|dispatch))\b",
    re.IGNORECASE,
)

# Keyword -> incident type mapping (order matters: first match wins)
KEYWORD_INCIDENT_MAP = [
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
    ("entrapment", "Entrapment/Rescue"),
    ("pin-in", "Entrapment/Rescue"),
    ("pinned in", "Entrapment/Rescue"),
    ("extrication", "Entrapment/Rescue"),
    ("shots fired", "Shots Fired"),
    ("shooting", "Shooting"),
    ("gunshot", "Shooting"),
    ("gun", "Person with Gun"),
    ("weapon", "Person with Weapon"),
    ("knife", "Person with Weapon"),
    ("stabbing", "Stabbing"),
    ("assault", "Assault"),
    ("battery", "Battery"),
    ("armed robbery", "Armed Robbery"),
    ("bank robbery", "Bank Robbery"),
    ("robbery", "Robbery"),
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
    ("cardiac arrest", "Cardiac Arrest"),
    ("cardiac", "Cardiac Emergency"),
    ("chest pain", "Chest Pain"),
    ("overdose", "Overdose"),
    ("narcan", "Overdose"),
    ("unconscious", "Unconscious Person"),
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

# --- Address abbreviation tables ---
DIRECTION_ABBREV = {
    "north": "N", "south": "S", "east": "E", "west": "W",
    "northeast": "NE", "northwest": "NW", "southeast": "SE", "southwest": "SW",
    "n": "N", "s": "S", "e": "E", "w": "W",
    "n.": "N", "s.": "S", "e.": "E", "w.": "W",
    "ne": "NE", "nw": "NW", "se": "SE", "sw": "SW",
}

SUFFIX_ABBREV = {
    "street": "ST", "avenue": "AVE", "road": "RD", "drive": "DR",
    "boulevard": "BLVD", "lane": "LN", "court": "CT", "place": "PL",
    "pike": "PIKE", "highway": "HWY", "trail": "TRL", "circle": "CIR",
    "parkway": "PKWY", "terrace": "TER", "path": "PATH", "run": "RUN",
    "ridge": "RDG", "crossing": "XING", "loop": "LOOP", "row": "ROW",
    "square": "SQ", "way": "WAY",
    # Already abbreviated forms
    "st": "ST", "ave": "AVE", "rd": "RD", "dr": "DR", "blvd": "BLVD",
    "ln": "LN", "ct": "CT", "pl": "PL", "hwy": "HWY", "trl": "TRL",
    "cir": "CIR", "pkwy": "PKWY", "ter": "TER", "xing": "XING", "sq": "SQ",
}

# Street suffixes for address matching — \b ensures we don't match inside
# words like "DOMESTIC" splitting into "DOME" + "ST"
STREET_SUFFIXES = (
    r"(?:street|avenue|ave|road|rd|drive|dr|boulevard|blvd|"
    r"lane|ln|court|ct|way|place|pl|pike|highway|hwy|trail|trl|"
    r"circle|cir|parkway|pkwy|terrace|ter|path|ridge|"
    r"crossing|xing|loop|row|square|sq)"
)
# "st" is only matched when it's a standalone word (not inside "domestic", "first", etc.)
STREET_SUFFIX_ST = r"(?:\bst\b)"

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
    "with", "from", "by", "cross", "of", "giving", "said", "hours",
    "duncan", "return", "head", "sending",
}

# Unit designation patterns (for extracting responding units)
# Pattern with number: ENGINE 92, MEDIC 5, etc.
UNIT_PATTERN = re.compile(
    r"\b(ENGINE|ENG|LADDER|TRUCK|RESCUE|SQUAD|MEDIC|AMBULANCE|"
    r"BATTALION|CHIEF|CAPTAIN|TANKER|TANGER|TENDER|QUINT|TOWER|"
    r"EVAC|LIFE|CAR|UNIT|WAGON|BRUSH|HAZMAT|AIR|MED)\s*(\d{1,4})\b",
    re.IGNORECASE,
)
# Pattern for named units without numbers: WINCHESTER MEDIC, MUNCIE FIRE, etc.
NAMED_UNIT_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]+)\s+(MEDIC|FIRE|EMS|RESCUE|AMBULANCE|LIFE)\b",
    re.IGNORECASE,
)

# Landmark / location name patterns (places named before the address)
LANDMARK_PATTERN = re.compile(
    r"\b([A-Z][A-Z\s]{2,}?)\s*,\s*\d{1,5}\s",
)


def _abbreviate_address(address_str: str) -> str:
    """Convert a full address to abbreviated uppercase format.
    e.g., "North Nevado Road" -> "N NEVADO RD"
    """
    words = address_str.split()
    result = []
    for word in words:
        w_lower = word.lower().rstrip(".,")
        if w_lower in DIRECTION_ABBREV:
            result.append(DIRECTION_ABBREV[w_lower])
        elif w_lower in SUFFIX_ABBREV:
            result.append(SUFFIX_ABBREV[w_lower])
        else:
            result.append(word.upper())
    return " ".join(result)


def _extract_landmark(transcript: str) -> str | None:
    """
    Try to find a landmark/location name in the transcript.
    Dispatchers often say the location name before the address:
    "MOUNT OLIVE CHURCH, 5000 NORTH NEVADO ROAD"
    "DAILY APARTMENTS, 1204 EAST BUNCH BOULEVARD"
    """
    if not transcript:
        return None

    # Pattern: NAMED PLACE, <number> <street>
    m = re.search(
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4})\s*,\s*\d{1,5}\s",
        transcript,
    )
    if m:
        landmark = m.group(1).strip()
        # Filter out things that aren't landmarks
        landmark_lower = landmark.lower()
        skip_words = {
            "engine", "ladder", "truck", "rescue", "squad", "medic",
            "respond on", "cross of", "cross street",
        }
        if any(s in landmark_lower for s in skip_words):
            return None
        # Filter out if it's just a county name + "county"
        if "county" in landmark_lower:
            return None
        return landmark.upper()

    # Pattern: "RM ###" or "ROOM ###" (room number at a facility)
    rm = re.search(r"\b(?:RM|ROOM)\s+(\d+)\b", transcript, re.IGNORECASE)
    if rm:
        return None  # Room numbers aren't landmarks

    return None


def _extract_units(transcript: str) -> list[str]:
    """Extract responding unit designations from transcript."""
    units = []
    seen = set()

    # Numbered units: ENGINE 92, MEDIC 5, etc.
    for m in UNIT_PATTERN.finditer(transcript):
        unit_type = m.group(1).upper()
        unit_num = m.group(2)
        unit_str = f"{unit_type} {unit_num}"
        if unit_str not in seen:
            units.append(unit_str)
            seen.add(unit_str)

    # Named units without numbers: WINCHESTER MEDIC, etc.
    for m in NAMED_UNIT_PATTERN.finditer(transcript):
        name = m.group(1).upper()
        role = m.group(2).upper()
        unit_str = f"{name} {role}"
        # Skip if the "name" is a blacklisted word or already captured
        if name.lower() in INTERSECTION_BLACKLIST or unit_str in seen:
            continue
        units.append(unit_str)
        seen.add(unit_str)

    return units


def _extract_respond_channel(transcript: str) -> str | None:
    """Extract 'respond on X' channel info from transcript."""
    m = re.search(
        r"respond\s+on\s+([\w\s]+?)(?:\.|$)",
        transcript,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return None


def _build_summary(transcript: str, incident_type: str) -> str:
    """
    Build an intelligent summary from the transcript.
    Extracts units, describes the incident, mentions the channel.
    """
    if not transcript:
        return "(No transcription available)"

    parts = []

    # 1. Responding units
    units = _extract_units(transcript)
    if units:
        parts.append(", ".join(units))

    # 2. Incident description
    # Map incident_type to a short, readable phrase
    incident_phrases = {
        "Vehicle Crash": "a vehicle crash",
        "Vehicle Crash - Injury": "an injury crash",
        "Vehicle Crash - Fatal": "a fatal crash",
        "Vehicle Crash - Rollover": "a rollover crash",
        "Vehicle Crash - Head On": "a head-on crash",
        "Structure Fire": "a structure fire",
        "Vehicle Fire": "a vehicle fire",
        "Grass/Brush Fire": "a grass/brush fire",
        "Wildland Fire": "a wildland fire",
        "Dumpster Fire": "a dumpster fire",
        "Fire": "a fire",
        "Entrapment/Rescue": "an entrapment/rescue",
        "Shooting": "a shooting",
        "Shots Fired": "a shots fired call",
        "Person with Gun": "a person with a gun",
        "Person with Weapon": "a person with a weapon",
        "Stabbing": "a stabbing",
        "Assault": "an assault",
        "Battery": "a battery",
        "Armed Robbery": "an armed robbery",
        "Bank Robbery": "a bank robbery",
        "Robbery": "a robbery",
        "Burglary": "a burglary",
        "Theft": "a theft",
        "Vehicle Pursuit": "a vehicle pursuit",
        "Foot Pursuit": "a foot pursuit",
        "HAZMAT Incident": "a HAZMAT incident",
        "Gas Leak": "a gas leak",
        "Carbon Monoxide": "a carbon monoxide call",
        "Bomb Threat": "a bomb threat",
        "Explosion": "an explosion",
        "Missing Person": "a missing person",
        "Missing Child": "a missing child",
        "Drowning": "a drowning",
        "Water Rescue": "a water rescue",
        "Cardiac Arrest": "a cardiac arrest",
        "Cardiac Emergency": "a cardiac emergency",
        "Chest Pain": "a chest pain call",
        "Overdose": "an overdose",
        "Unconscious Person": "an unconscious person",
        "Unresponsive Person": "an unresponsive person",
        "Respiratory Emergency": "a respiratory emergency",
        "Choking": "a choking call",
        "Seizure": "a seizure",
        "Stroke": "a stroke",
        "Medical Emergency": "a medical emergency",
        "EMS Call": "an EMS call",
        "Lift Assist": "a lift assist",
        "Fall/Injury": "a fall/injury",
        "BLS Transfer": "a BLS transfer",
        "ALS Transfer": "an ALS transfer",
        "Patient Transfer": "a patient transfer",
        "Domestic Disturbance": "a domestic disturbance",
        "Disturbance": "a disturbance",
        "Trespassing": "a trespassing call",
        "Suspicious Person": "a suspicious person",
        "Suspicious Vehicle": "a suspicious vehicle",
        "Welfare Check": "a welfare check",
        "Alarm": "an alarm",
        "Tone Alert": "a tone alert",
        "Keyword Alert": "a dispatch",
        "Dispatch": "a dispatch",
    }

    phrase = incident_phrases.get(incident_type, "a dispatch")

    if units:
        parts.append(f"responding to {phrase}")
    else:
        parts.append(phrase.capitalize())

    # 3. Channel / fire ground
    channel = _extract_respond_channel(transcript)
    if channel:
        parts.append(f"on {channel}")

    return " ".join(parts)


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
    Returns "COUNTY_NAME COUNTY" in all caps. Fallback: "UNK COUNTY".
    """
    tg = (talkgroup_label or "").lower()
    sys_lbl = (system_label or "").lower()
    tx = (transcript or "").lower()

    # 1. Check system label for county names (most reliable)
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if county_lower in sys_lbl:
            return f"{county.upper()} COUNTY"

    # 2. Check talkgroup label for county names
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if county_lower in tg:
            return f"{county.upper()} COUNTY"

    # 3. Check talkgroup/system labels for city names -> map to county
    for city, county in CITY_TO_COUNTY.items():
        if city in tg or city in sys_lbl:
            return f"{county.upper()} COUNTY"

    # 4. Check transcript for county mentions (e.g., "DELAWARE COUNTY")
    for county in INDIANA_COUNTIES:
        county_lower = county.lower()
        if re.search(rf"\b{re.escape(county_lower)}\s+count", tx):
            return f"{county.upper()} COUNTY"

    # 5. Check transcript for city mentions -> map to county
    for city, county in CITY_TO_COUNTY.items():
        if re.search(rf"\b{re.escape(city)}\b", tx):
            return f"{county.upper()} COUNTY"

    # 6. Try to extract city name from talkgroup label as-is
    tg_clean = re.sub(r"\b(fire|pd|police|ems|dispatch|sheriff|so|fd|disp|rural)\b", "", tg).strip()
    tg_clean = re.sub(r"\d+[-]?", "", tg_clean).strip()
    if tg_clean and len(tg_clean) > 2:
        return tg_clean.upper()

    return "UNK COUNTY"


def extract_address(transcript: str) -> str:
    """
    Extract street address from transcript and convert to abbreviated block format.
    Returns "5000 BLK N NEVADO RD (LANDMARK)" or "NO ADDRESS".
    All output is uppercase abbreviated.
    """
    if not transcript:
        return "NO ADDRESS"

    text = transcript
    landmark = _extract_landmark(transcript)

    # Combined suffix pattern: full words OR standalone "st" with word boundary
    _suffix = rf"(?:{STREET_SUFFIXES}\b|{STREET_SUFFIX_ST})"

    # Pattern 1: Number + optional direction + street name + suffix (word-bounded)
    # e.g., "5000 NORTH NEVADO ROAD", "1204 EAST BUNCH BOULEVARD"
    pattern1 = (
        rf"\b(\d{{1,5}})\s+"
        rf"(?:({DIRECTIONS})\s+)?"
        rf"([A-Za-z]{{3,}}(?:\s+[A-Za-z]{{3,}}){{0,3}})"
        rf"\s+{_suffix}"
    )
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        direction = (match.group(2) or "").strip()
        street_name = match.group(3).strip()
        # Get the full match to extract the suffix
        full = match.group(0)
        suffix_match = re.search(rf"{_suffix}\s*$", full, re.IGNORECASE)
        suffix = suffix_match.group(0).strip() if suffix_match else ""
        block_num = (num // 100) * 100

        parts = [str(block_num), "BLK"]
        if direction:
            parts.append(DIRECTION_ABBREV.get(direction.lower().rstrip("."), direction.upper()))
        parts.append(street_name.upper())
        if suffix:
            parts.append(SUFFIX_ABBREV.get(suffix.lower(), suffix.upper()))

        addr = " ".join(parts)
        if landmark:
            addr += f" ({landmark})"
        return addr

    # Pattern 2: "STATE ROAD ##" / "SR ##" / "US ##" / "CR ##"
    state_road = re.search(
        rf"\b(?:state\s+road|state\s+route|sr|us|cr|county\s+road)\s+(\d+)\b",
        text,
        re.IGNORECASE,
    )
    if state_road:
        road_name = state_road.group(0).strip().upper()
        road_name = road_name.replace("STATE ROAD", "SR").replace("STATE ROUTE", "SR").replace("COUNTY ROAD", "CR")
        addr = road_name
        if landmark:
            addr += f" ({landmark})"
        return addr

    # Pattern 3: Number + direction + street name (no suffix required)
    # e.g., "607 NORTH KETTERER", "5000 NORTH NEVADO"
    pattern3 = (
        rf"\b(\d{{1,5}})\s+"
        rf"({DIRECTIONS})\s+"
        rf"([A-Z][a-zA-Z]{{2,}}(?:\s+[A-Z][a-zA-Z]{{2,}}){{0,2}})"
    )
    match = re.search(pattern3, text)
    if match:
        num = int(match.group(1))
        direction = match.group(2).strip()
        street = match.group(3).strip()
        # Filter out dispatch keywords and very short words
        first_word = street.split()[0].lower() if street else ""
        if first_word not in INTERSECTION_BLACKLIST and len(first_word) > 2:
            block_num = (num // 100) * 100
            dir_abbr = DIRECTION_ABBREV.get(direction.lower().rstrip("."), direction.upper())
            addr = f"{block_num} BLK {dir_abbr} {street.upper()}"
            if landmark:
                addr += f" ({landmark})"
            return addr

    # Pattern 4: Number + street name (no direction, no suffix)
    # e.g., "1204 BUNCH" — less reliable, only use if number >= 100
    pattern4 = rf"\b(\d{{3,5}})\s+([A-Z][a-zA-Z]{{3,}}(?:\s+[A-Z][a-zA-Z]{{3,}}){{0,2}})\b"
    match = re.search(pattern4, text)
    if match:
        num = int(match.group(1))
        street = match.group(2).strip()
        first_word = street.split()[0].lower()
        if first_word not in INTERSECTION_BLACKLIST and len(first_word) > 2:
            block_num = (num // 100) * 100
            addr = f"{block_num} BLK {street.upper()}"
            if landmark:
                addr += f" ({landmark})"
            return addr

    # Pattern 5: "ON <street>" pattern — common in radio ("ON LUDIE", "ON MEMORIAL")
    on_street = re.search(
        rf"\bon\s+({DIRECTIONS}\s+)?([A-Z][a-zA-Z]{{3,}}(?:\s+{_suffix})?)\b",
        text,
    )
    if on_street:
        direction = (on_street.group(1) or "").strip()
        street = on_street.group(2).strip()
        if street.lower() not in INTERSECTION_BLACKLIST and len(street) > 3:
            parts = ["AREA OF"]
            if direction:
                parts.append(DIRECTION_ABBREV.get(direction.lower().rstrip("."), direction.upper()))
            parts.append(_abbreviate_address(street))
            return " ".join(parts)

    # Pattern 6: Intersection — only if both look like real street names
    intersection = re.search(
        rf"\b(?:({DIRECTIONS})\s+)?([A-Z][a-zA-Z]{{3,}})"
        rf"\s+(?:and|&)\s+"
        rf"(?:({DIRECTIONS})\s+)?([A-Z][a-zA-Z]{{3,}})\b",
        text,
    )
    if intersection:
        dir1 = (intersection.group(1) or "").strip()
        street1 = intersection.group(2).strip()
        dir2 = (intersection.group(3) or "").strip()
        street2 = intersection.group(4).strip()
        if (
            street1.lower() not in INTERSECTION_BLACKLIST
            and street2.lower() not in INTERSECTION_BLACKLIST
            and len(street1) > 2
            and len(street2) > 2
        ):
            parts = []
            if dir1:
                parts.append(DIRECTION_ABBREV.get(dir1.lower().rstrip("."), dir1.upper()))
            parts.append(street1.upper())
            parts.append("&")
            if dir2:
                parts.append(DIRECTION_ABBREV.get(dir2.lower().rstrip("."), dir2.upper()))
            parts.append(street2.upper())
            return " ".join(parts)

    return "NO ADDRESS"


def _is_standalone_fire_keyword(transcript: str) -> bool:
    """Check if 'fire' refers to an actual fire, not a unit name."""
    text_lower = transcript.lower()
    if "fire" not in text_lower:
        return False
    cleaned = NON_INCIDENT_FIRE_CONTEXTS.sub("", text_lower)
    cleaned = re.sub(r"respond\s+on\s+.*?fire\s+ground\s+\d+", "", cleaned)
    cleaned = re.sub(r"\b[a-z]+\s+fire\b", "", cleaned)
    return bool(re.search(r"\bfire\b", cleaned))


def classify_incident(alert: dict, transcript: str) -> str:
    """Classify the incident type from 10-codes, keywords, and alert metadata."""
    if not transcript:
        if alert.get("toneDetected"):
            return "Tone Alert"
        return "Dispatch"

    text_lower = transcript.lower()

    # 1. 10-codes
    ten_codes = find_ten_codes_in_text(transcript)
    for _raw, code, _desc in ten_codes:
        if code in TEN_CODE_INCIDENT_MAP:
            return TEN_CODE_INCIDENT_MAP[code]

    # 2. Signal codes
    signals = find_signal_codes_in_text(transcript)
    for _raw, code, _desc in signals:
        if code in SIGNAL_INCIDENT_MAP:
            return SIGNAL_INCIDENT_MAP[code]

    # 3. Keyword matching
    for keyword, incident_type in KEYWORD_INCIDENT_MAP:
        if keyword in text_lower:
            return incident_type

    # 4. Standalone "fire" with context check
    if _is_standalone_fire_keyword(transcript):
        return "Fire"

    # 5. Alert metadata fallback
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
    if is_pager_test(transcript):
        return None

    tg_label = alert.get("talkgroupLabel", "") or ""
    sys_label = alert.get("systemLabel", "") or ""

    county = extract_county(tg_label, sys_label, transcript)
    address = extract_address(transcript)
    incident_type = classify_incident(alert, transcript)
    summary = _build_summary(transcript, incident_type)

    formatted = f"{county} | {address} | {incident_type} | {summary}"

    return {
        "county": county,
        "address": address,
        "incident_type": incident_type,
        "summary": summary,
        "formatted": formatted,
    }
