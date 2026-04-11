"""
Audit caseName column in both SCDB CSVs for cases with multiple states
that may need to be added to MULTIPLE_STATE_CASES in scotuswars.py.
"""
import csv
import re
import sys
from scotuswars import FILENAMES, INTERESTING_PARTIES, STATES, MULTIPLE_STATE_CASES

# Build a regex that matches any state name (longest first to avoid prefix issues)
state_names = sorted(STATES.values(), key=len, reverse=True)
_states_pattern = "|".join(re.escape(s) for s in state_names)
STATE_RE = re.compile(_states_pattern, flags=re.IGNORECASE)

# Matches the versus separator in case names
VERSUS_RE = re.compile(r"\bv\.?\s+|\bvs\.?\s+", flags=re.IGNORECASE)


def _normalize_state(name):
    """Normalize a matched state string to its canonical casing."""
    name = name.title()
    for s in state_names:
        if s.lower() == name.lower():
            return s
    return name


def _states_in_text(text):
    """Return list of unique state names found in text, in order of appearance."""
    found = []
    seen = set()
    for m in STATE_RE.finditer(text):
        name = _normalize_state(m.group())
        if name not in seen:
            seen.add(name)
            found.append(name)
    return found


def find_states_in_name(case_name):
    """Return (petitioner_states, respondent_states) by splitting on the versus separator.

    Only states that appear together on the same side count as a multi-state case.
    """
    parts = VERSUS_RE.split(case_name, maxsplit=1)
    if len(parts) == 2:
        petitioner_side, respondent_side = parts
    else:
        petitioner_side, respondent_side = case_name, ""
    return _states_in_text(petitioner_side), _states_in_text(respondent_side)


def cases():
    for filename in FILENAMES:
        with open(filename, encoding="ISO-8859-1") as fd:
            reader = csv.DictReader(fd)
            for row in reader:
                yield row


def interesting_cases():
    for case in cases():
        if (
            case["petitioner"] in INTERESTING_PARTIES
            and case["respondent"] in INTERESTING_PARTIES
        ):
            yield case


def main():
    known = set(MULTIPLE_STATE_CASES.keys())
    detected_multi = {}   # docketId -> (caseName, [states])
    detected_known = {}   # docketId -> (caseName, [states])
    not_detected_known = set()  # docketId in MULTIPLE_STATE_CASES but no multi-state found

    for case in interesting_cases():
        docket_id = case["docketId"]
        case_name = case["caseName"]
        pet_states, resp_states = find_states_in_name(case_name)
        all_states = _states_in_text(case_name)

        if len(pet_states) >= 2 or len(resp_states) >= 2 or len(all_states) >= 3:
            states_found = (pet_states, resp_states)
            if docket_id in known:
                detected_known[docket_id] = (case_name, states_found)
            else:
                detected_multi[docket_id] = (case_name, states_found)

    # Find MULTIPLE_STATE_CASES entries not detected by name scan
    seen_dockets = set(detected_known.keys())
    not_detected_known = known - seen_dockets

    print("=" * 70)
    print("NEW candidates (multiple states in caseName, NOT in MULTIPLE_STATE_CASES)")
    print("=" * 70)
    if detected_multi:
        for docket_id, (case_name, (pet_states, resp_states)) in sorted(detected_multi.items()):
            print(f"  {docket_id}: {case_name}")
            print(f"    Petitioners: {pet_states}  Respondents: {resp_states}")
    else:
        print("  (none)")


if __name__ == "__main__":
    main()
