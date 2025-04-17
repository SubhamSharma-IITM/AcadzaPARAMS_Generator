# 📦 param_config.py — DOST Parameter Schemas + Defaults (Updated)

# ---------------------------
# ✅ ALLOWED DOSTs + SUBDOSTs
# ---------------------------

allowed_dosts = {
    "Concept Dost": ["concept"],
    "Revision Dost": ["revision"],
    "Formula Dost": ["formula"],
    "Practice Dost": ["practiceAssignment", "practiceTest"],
    "Speed Booster Dost": ["clickingPower", "pickingPower", "speedRace"]
}

# ---------------------------
# ✅ PARAMETER SCHEMA + DEFAULTS
# ---------------------------

def get_param_specs(dost_type: str) -> dict:
    specs = {
        "practiceAssignment": {
            "expected_fields": ["difficulty", "type_split"],
            "defaults": {
                "difficulty": "easy",
                "type_split": {
                    "scq": 20,
                    "mcq": 10,
                    "integerQuestion": 5,
                    "passageQuestion": 0,
                    "matchQuestion": 0
                }
            }
        },
        "practiceTest": {
            "expected_fields": ["difficulty", "duration_minutes"],
            "defaults": {
                "difficulty": "easy",
                "duration_minutes": 60,
            }
        },
        "formula": {
            "expected_fields": [],
            "defaults": {}
        },
        "revision": {
            "expected_fields": [],
            "defaults": {
                "allotedDay": 3,
                "allotedTime": 1,
                "strategy": 1,
                "daywiseTimePerPortion": 60,
                "taskTypes": ["assignment", "test"],
                "importance": None  # Let GPT infer from tone, else skip
            }
        },
        "clickingPower": {
            "expected_fields": [],
            "defaults": {
                "totalQuestions": 10
            }
        },
        "pickingPower": {
            "expected_fields": [],
            "defaults": {}
        },
        "speedRace": {
            "expected_fields": ["rank"],
            "defaults": {
                "rank": 100,
                "opponentType": "bot",
                "scheduledTime": "",
                "duration": ""
            }
        },
        "concept": {
            "expected_fields": [],
            "defaults": {}
        }
    }
    return specs.get(dost_type, {"expected_fields": [], "defaults": {}})

# ---------------------------
# ✅ ACCESSORS
# ---------------------------

def get_allowed_dost_types():
    return [sub for group in allowed_dosts.values() for sub in group]

def get_parent_dost_type(subdost: str):
    for parent, children in allowed_dosts.items():
        if subdost in children:
            return parent
    raise ValueError(f"Unknown subdost type: {subdost}")
