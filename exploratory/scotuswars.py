import csv
import collections
import itertools
import functools
import re

# "Petitioner" refers to the party who
# petitioned the Supreme Court to review the case. This party is variously known as the
# petitioner or the appellant. "Respondent" refers to the party being sued or tried and is also
# known as the appellee.
# Case names are Petitioner v. Respondent

FILENAMES = ["SCDB_2019_01_caseCentered_Citation.csv", "SCDB_Legacy_05_caseCentered_Citation.csv"]

STATES = [
"Alabama",
"Alaska",
"Arizona",
"Arkansas",
"California",
"Colorado",
"Connecticut",
"Delaware",
"District of Columbia",
"Florida",
"Georgia",
"Hawaii",
"Idaho",
"Illinois",
"Indiana",
"Iowa",
"Kansas",
"Kentucky",
"Louisiana",
"Maine",
"Maryland",
"Massachusetts",
"Michigan",
"Minnesota",
"Mississippi",
"Missouri",
"Montana",
"Nebraska",
"Nevada",
"New Hampshire",
"New Jersey",
"New Mexico",
"New York",
"North Carolina",
"North Dakota",
"Ohio",
"Oklahoma",
"Oregon",
"Pennsylvania",
"Rhode Island",
"South Carolina",
"South Dakota",
"Tennessee",
"Texas",
"Utah",
"Vermont",
"Virginia",
"Washington",
"West Virginia",
"Wisconsin",
"Wyoming",
"American Samoa",
"Guam",
"Northern Mariana Islands",
"Puerto Rico",
"Virgin Islands",
"United States",
]

_states = "|".join([state.replace(" ", "([\s+]|-)") for state in STATES])
STATE_RE = re.compile(_states, flags=re.I)

# Notes:
# multiple capitalizations of ex parte / in re
#   possibly et al?
# BAD_CASE_NAMES

BAD_PREFIX_REGEX = re.compile('^(ex\s+parte|in\s+re)|(ex\s+parte)$', flags=re.I)
BAD_CASE_NAMES = {
        '1951 U.S. LEXIS 2247': 'Niemotko v. Maryland',
        '1965 U.S. LEXIS 2': 'ALBANESE v. N. V. NEDERL. AMERIK STOOMV. MAATS. et al.',
        '1968 U.S. LEXIS 2913': 'INTERNATIONAL TERMINAL OPERATING CO., INC. v. N. V. NEDERL. AMERIK STOOMV. MAATS',
        '1972 U.S. LEXIS 47': 'IVAN V. v. CITY OF NEW YORK',
        '1983 U.S. LEXIS 30': 'VERLINDEN B. V. v. CENTRAL BANK OF NIGERIA',
        # Note that 105 S. Ct. 1676 is glitched and is merged with
        # 'BOARD OF EDUCATION OF OKLAHOMA CITY v. NATIONAL GAY TASK FORCE'
        # 'FUGATE v. NEW MEXICO'
        '1985 U.S. LEXIS 80': 'METROPOLITAN LIFE INSURANCE CO. et al. v. WARD',
        '1987 U.S. LEXIS 4689': 'CHURCH OF SCIENTOLOGY OF CALIFORNIA v. INTERNAL REVENUE SERVICE',
        '1991 U.S. LEXIS 7262': 'HUNTER et al. v. BRYANT',
        '1993 U.S. LEXIS 3126': 'UNITED STATES v. XAVIER V. PADILLA et al.',
        '1994 U.S. LEXIS 1137': 'ERIC J. WEISS v. UNITED STATES',
        '1998 U.S. LEXIS 456': 'FIDELITY FINANCIAL SERVICES, INC. v. RICHARD V. FINK, TRUSTEE',
        '1998 U.S. LEXIS 2963': 'VINCENT EDWARDS, REYNOLDS A. WINTERSMITH, HORACE JOINER, KARL V. FORT, AND JOSEPH TIDWELL v. UNITED STATES',
        '2002 U.S. LEXIS 3787': 'VERIZON MD. INC. v. PUBLIC SERV. COMM\'N OF MD.',
        '2004 U.S. LEXIS 657': 'VERIZON COMMUNICATIONS INC. v. LAW OFFICES OF CURTIS V. TRINKO, LLP',
        '2004 U.S. LEXIS 4030': 'REPUBLIC OF AUSTRIA et al. v. MARIA V. ALTMANN',
        '2005 U.S. LEXIS 5014': 'AURELIO O. GONZALEZ v. JAMES V. CROSBY, JR., SECRETARY, FLORIDA DEPARTMENT OF CORRECTIONS',
        '2007 U.S. LEXIS 1325': 'LORENZO L. JONES v. BARBARA BOCK, WARDEN, et al.',
        '2007 U.S. LEXIS 1324': 'JOHN CUNNINGHAM v. CALIFORNIA',
        '2007 U.S. LEXIS 5901': 'BELL ATLANTIC CORPORATION, et al. v. WILLIAM TWOMBLY, et al.',
        '2012 U.S. LEXIS 4661': 'FEDERAL COMMUNICATIONS COMMISSION, et al., PETITIONERS v. FOX TELEVISION STATIONS, INC., et al.',
        '2015 U.S. LEXIS 612': 'T\x96MOBILE SOUTH, LLC v. CITY OF ROSWELL, GEORGIA.',
        '2016 U.S. LEXIS 1653': 'V. L. v. E. L., et al.',
        '2018 U.S. LEXIS 896': 'CNH INDUSTRIAL N.V. v. REESE',
        '1815 U.S. LEXIS 366': 'TERRETT AND OTHERS v. TAYLOR AND OTHERS',
        # These names aren't bad, I'm just normalizing them for my validation
        # of the petitioner/respondentState fields
        '1904 U.S. LEXIS 640': 'MISSOURI v. NEBRASKA',
        '1904 U.S. LEXIS 678': 'NEBRASKA v. MISSOURI',
}

# Bad spellings
# 1914-204-01
# 1917-128-01
# 1925-010-01
# 1841-030-01
# Many typos of "washingtonn"
# 1902-122-01
# Many typos of "corporationn"

# Has an html entity in the name 1990-106-01

# XXX figure out how to special case 1904-001-01 1904-003-01
#
# two states:
# 2015-073-01
# 2014-007-01
# 2010-039-01
# 2002-056-01
# 2001-003-01
# 1993-010-01
# 1992-055-01
# 1990-106-01
# 1939-130-01
# 1940-042-01


INTERESTING_PARTIES = {
        #'15', # interstate compact
        #'17', # state legislature
        '27', # the United States
        '28', # a State
}

def case_emitter(cases):
    for case in cases:
        if case['lexisCite'] in BAD_CASE_NAMES:
            case_name = BAD_CASE_NAMES[case['lexisCite']]
        else:
            case_name = case['caseName']

        if BAD_PREFIX_REGEX.search(case_name):
            continue
        if ' VERSUS ' in case_name:
            case_name = case_name.replace(' VERSUS ', ' v. ')
        if ' VS. ' in case_name:
            case_name = case_name.replace(' VS. ', ' v. ')
        bits = case_name.split('v.')
        if len(bits) != 2:
            if int(case['term']) < 1946:
                # A bunch of inconsistent names here. I've cleaned them up
                # as much as I can above.
                continue
            print(f"{case['caseId']=} {case['caseName']=}\n{case['lexisCite']=} {case['sctCite']=}")

        petitioner, respondent = bits
        petitioner = petitioner.strip()
        respondent = respondent.strip()
        petitioner_state_re = STATE_RE.search(petitioner)
        respondent_state_re = STATE_RE.search(respondent)

        if case['petitioner'] in INTERESTING_PARTIES and case['respondent'] in INTERESTING_PARTIES:
            print(f"good: {case['caseName']} {petitioner=} {respondent=} {case['docketId']=}")
        #if petitioner_state_re and respondent_state_re:
        #    print(f"good: {case['caseName']} {petitioner=} {respondent=} {case['docketId']=}")

        yield

def main():
    cases = []
    for filename in FILENAMES:
        with open(filename, encoding="ISO-8859-1") as fd:
            reader = csv.DictReader(fd)
            cases += list(reader)

    counter = collections.Counter(itertools.chain.from_iterable(case.keys() for case in cases))
    assert functools.reduce(lambda x, y: y-x, counter.values(), list(counter.values())[0]) == 0

    cases = list(case_emitter(cases))



if __name__ == "__main__":
    main()
