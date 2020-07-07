import csv
import json
import datetime
import sys

FILENAMES = [
    "SCDB_2019_01_caseCentered_Citation.csv",
    "SCDB_Legacy_05_caseCentered_Citation.csv",
]

INTERESTING_PARTIES = {
    "27",  # the United States
    "28",  # a State
}

STATES = {
    "1": "Alabama",
    "2": "Alaska",
    "3": "American Samoa",
    "4": "Arizona",
    "5": "Arkansas",
    "6": "California",
    "7": "Colorado",
    "8": "Connecticut",
    "9": "Delaware",
    "10": "District of Columbia",
    "11": "Federated States of Micronesia",
    "12": "Florida",
    "13": "Georgia",
    "14": "Guam",
    "15": "Hawaii",
    "16": "Idaho",
    "17": "Illinois",
    "18": "Indiana",
    "19": "Iowa",
    "20": "Kansas",
    "21": "Kentucky",
    "22": "Louisiana",
    "23": "Maine",
    "24": "Marshall Islands",
    "25": "Maryland",
    "26": "Massachusetts",
    "27": "Michigan",
    "28": "Minnesota",
    "29": "Mississippi",
    "30": "Missouri",
    "31": "Montana",
    "32": "Nebraska",
    "33": "Nevada",
    "34": "New Hampshire",
    "35": "New Jersey",
    "36": "New Mexico",
    "37": "New York",
    "38": "North Carolina",
    "39": "North Dakota",
    "40": "Northern Mariana Islands",
    "41": "Ohio",
    "42": "Oklahoma",
    "43": "Oregon",
    "44": "Palau",
    "45": "Pennsylvania",
    "46": "Puerto Rico",
    "47": "Rhode Island",
    "48": "South Carolina",
    "49": "South Dakota",
    "50": "Tennessee",
    "51": "Texas",
    "52": "Utah",
    "53": "Vermont",
    "54": "Virgin Islands",
    "55": "Virginia",
    "56": "Washington",
    "57": "West Virginia",
    "58": "Wisconsin",
    "59": "Wyoming",
    "60": "United States",
    "61": "Interstate Compact",
    "62": "Philippines",
    "63": "Indian",
    "64": "Dakota",
}
REVERSE_STATES = {v: k for k, v in STATES.items()}
STATE_ABBRV = {
    "Alabama": "AL",
    "Alaska": "AK",
    "American Samoa": "AS",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Guam": "GU",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Marshall Islands": "MP",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Puerto Rico": "PR",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virgin Islands": "VI",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "United States": "US",
}


MULTIPLE_STATE_CASES = {
    "1990-106-01": (["Oklahoma", "Texas"], ["New Mexico"]),
    "1992-055-01": (["Nebraska"], ["Wyoming", "Colorado"]),
    "1993-010-01": (["Oklahoma", "Texas"], ["New Mexico"]),
    "1994-062-01": (["Nebraska"], ["Wyoming", "Colorado"]),
    "2001-003-01": (["Nebraska"], ["Wyoming", "Colorado"]),
    "2002-056-01": (["Kansas"], ["Nebraska", "Colorado"]),
    "2010-039-01": (["Montana"], ["Wyoming", "North Dakota"]),
    "2014-007-01": (["Kansas"], ["Nebraska", "Colorado"]),
    "2015-073-01": (["Montana"], ["Wyoming", "North Dakota"]),
    "2017-032-01": (["Texas"], ["New Mexico", "Colorado"]),
    "1904-001-01": (["Nebraska"], ["Missouri"]),  # This one is undecided winning
    "1904-003-01": (["Nebraska"], ["Missouri"]),  # This one is Nebraska winning
    "1939-130-01": (["Wisconsin", "Minnesota", "Ohio", "Pennsylvania"], ["Illinois"]),
    "1940-042-01": (["Wisconsin", "Minnesota", "Ohio", "Pennsylvania"], ["Illinois"]),
}


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


def ci_lower_bound(positive, total):
    # https://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    if total == 0:
        return 0
    z = 1.96
    phat = 1.0 * positive / total
    return (phat + z*z/(2*total) - z * ((phat*(1-phat)+z*z/(4*total))/total)**.5)/(1+z*z/total)


def get_name(party_id, party_state):
    if party_id == "27":
        return "United States"
    else:
        return STATES[party_state]


def main():
    results = {}
    for case in interesting_cases():
        if case["docketId"] in MULTIPLE_STATE_CASES:
            petitioner_names, respondent_names = MULTIPLE_STATE_CASES[case["docketId"]]
        else:
            petitioner = case["petitioner"]
            respondent = case["respondent"]
            petitioner_state = case["petitionerState"]
            respondent_state = case["respondentState"]
            petitioner_names = [get_name(petitioner, petitioner_state)]
            respondent_names = [get_name(respondent, respondent_state)]

        winner = case["partyWinning"]

        us_cite = case['usCite']
        if len(us_cite) == 0:
            print(f"Missing US Cite: {case['lexisCite']}", file=sys.stderr)
            continue
        us_cite_bits = [int(x) for x in us_cite.split('U.S.')]

        decided_date = [int(x) for x in case["dateDecision"].split("/")]
        decided_date = datetime.date(decided_date[2], decided_date[0], decided_date[1])

        case_name = case["caseName"].title().replace(' V. ', ' v. ')

        citation_name = f'{case_name}, {us_cite} ({decided_date.year})'
        citation = {"name": citation_name, "us": us_cite_bits}

        result_keys = [
            tuple(sorted((petitioner_name, respondent_name)))
            for petitioner_name in petitioner_names
            for respondent_name in respondent_names
        ]

        for result_key in result_keys:
            if result_key not in results:
                results[result_key] = [[], [], []]

        petitioner_idxes = [
            result_key.index(petitioner_name) if petitioner_name in result_key else None
            for petitioner_name in petitioner_names
            for result_key in result_keys
        ]
        respondent_idxes = [
            result_key.index(respondent_name) if respondent_name in result_key else None
            for respondent_name in respondent_names
            for result_key in result_keys
        ]

        if winner == "0":
            # petitioner lost
            for result_key, respondent_idx in zip(result_keys, respondent_idxes):
                if respondent_idx is None:
                    continue
                results[result_key][respondent_idx].append(citation)
        elif winner == "1":
            # petitioner won
            for result_key, petitioner_idx in zip(result_keys, petitioner_idxes):
                if petitioner_idx is None:
                    continue
                results[result_key][petitioner_idx].append(citation)
        else:
            # inconclusive
            for result_key in result_keys:
                results[result_key][2].append(citation)

    # from pprint import pprint
    # pprint(results)

    # build the json-compatible, denormalized data structure

    json_results = {}
    for state_pair in results:
        state1, state2 = state_pair
        state1_code = STATE_ABBRV[state1]
        state2_code = STATE_ABBRV[state2]

        if state1_code == "DC" or state2_code == "DC":
            continue

        for state in (state1_code, state2_code):
            if state not in json_results:
                json_results[state] = {}
        cases = results[state_pair]
        state1_won, state2_won, undecided = cases

        if state2_code not in json_results[state1_code]:
            json_results[state1_code][state2_code] = {
                "name": state2,
                "wins": [],
                "losses": [],
                "undecided": [],
            }
        if state1_code not in json_results[state2_code]:
            json_results[state2_code][state1_code] = {
                "name": state1,
                "wins": [],
                "losses": [],
                "undecided": [],
            }

        json_results[state1_code][state2_code]["wins"] += state1_won
        json_results[state1_code][state2_code]["losses"] += state2_won
        json_results[state1_code][state2_code]["undecided"] += undecided

        json_results[state2_code][state1_code]["wins"] += state2_won
        json_results[state2_code][state1_code]["losses"] += state1_won
        json_results[state2_code][state1_code]["undecided"] += undecided

    for state1 in json_results:
        for state2 in json_results[state1]:
            state2_obj = json_results[state1][state2]
            win_cnt = len(state2_obj["wins"])
            loss_cnt = len(state2_obj["losses"])
            undecided_cnt = len(state2_obj["undecided"])
            total_cnt = win_cnt + loss_cnt + undecided_cnt

            if win_cnt + loss_cnt == 0:
                win_pct = 0.0
            else:
                win_pct = (win_cnt - loss_cnt) / (win_cnt + loss_cnt)
            win_offset = round((win_pct+1)*127.5)

            state2_obj["win_pct"] = win_pct
            state2_obj["win_offset"] = win_offset
            state2_obj["ci_lower_bound"] = ci_lower_bound(win_cnt, total_cnt)

        for idx, state2 in enumerate(sorted(json_results[state1].items(), key=lambda x: x[1]["ci_lower_bound"], reverse=True)):
            state2[1]["ci_order"] = idx

    return json_results


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
