# (ↄ) 2017-2022 eli fessler (frozenpandaman), clovervidia
# https://github.com/frozenpandaman/s3s
# License: GPLv3

import base64, datetime, json, re, sys, uuid
import requests
from bs4 import BeautifulSoup

SPLATNET3_URL = "https://api.lp1.av5ja.srv.nintendo.net"
GRAPHQL_URL  = "https://api.lp1.av5ja.srv.nintendo.net/api/graphql"
WEB_VIEW_VERSION = "4.0.0-22ddb0fd" # fallback
S3S_NAMESPACE = uuid.UUID('b3a2dbf5-2c09-4792-b78c-00b548b70aeb')

# SHA256 hash database for SplatNet 3 GraphQL queries
# full list: https://github.com/samuelthomas2774/nxapi/discussions/11#discussioncomment-3614603
translate_rid = {
	'HomeQuery':                         '7dcc64ea27a08e70919893a0d3f70871', # blank vars
	'LatestBattleHistoriesQuery':        '0d90c7576f1916469b2ae69f64292c02', # INK / blank vars - query1
	'RegularBattleHistoriesQuery':       '3baef04b095ad8975ea679d722bc17de', # INK / blank vars - query1
	'BankaraBattleHistoriesQuery':       '0438ea6978ae8bd77c5d1250f4f84803', # INK / blank vars - query1
	'PrivateBattleHistoriesQuery':       '8e5ae78b194264a6c230e262d069bd28', # INK / blank vars - query1
	'XBattleHistoriesQuery':             '6796e3cd5dc3ebd51864dc709d899fc5', # INK / blank vars - query1
	'VsHistoryDetailQuery':              '9ee0099fbe3d8db2a838a75cf42856dd', # INK / req "vsResultId" - query2
	'CoopHistoryQuery':                  '01fb9793ad92f91892ea713410173260', # SR  / blank vars - query1
	'CoopHistoryDetailQuery':            '379f0d9b78b531be53044bcac031b34b', # SR  / req "coopHistoryDetailId" - query2
	'MyOutfitCommonDataEquipmentsQuery': 'd29cd0c2b5e6bac90dd5b817914832f8', # for Lean's seed checker
	'FriendsList':                       'f0a8ebc384cf5fbac01e8085fbd7c898',
	'HistorySummary':                    'd9246baf077b2a29b5f7aac321810a77',
	'TotalQuery':                        'f8ae00773cc412a50dd41a6d9a159ddd',
	'XRankingQuery':                     'd771444f2584d938db8d10055599011d',
	'ScheduleQuery':                     'd1f062c14f74f758658b2703a5799002',
	'StageRecordsQuery':                 'f08a932d533845dde86e674e03bbb7d3',
	'EventBattleHistoriesQuery':         'e7bbaf1fa255305d607351da434b2d0f',
}

def get_web_view_ver():
	'''Find & parse the SplatNet 3 main.js file for the current site version.'''

	splatnet3_home = requests.get(SPLATNET3_URL)
	soup = BeautifulSoup(splatnet3_home.text, "html.parser")

	main_js = soup.select_one("script[src*='static']")
	if not main_js:
		return WEB_VIEW_VERSION

	main_js_url = SPLATNET3_URL + main_js.attrs["src"]
	main_js_body = requests.get(main_js_url)

	match = re.search(r"\b(?P<revision>[0-9a-f]{40})\b.*revision_info_not_set\"\),.*?=\"(?P<version>\d+\.\d+\.\d+)", main_js_body.text)
	if not match:
		return WEB_VIEW_VERSION

	version, revision = match.group("version"), match.group("revision")
	return f"{version}-{revision[:8]}"


def set_noun(which):
	'''Returns the term to be used when referring to the type of results in question.'''

	if which == "both":
		return "battles/jobs"
	elif which == "salmon":
		return "jobs"
	else: # "ink"
		return "battles"


def b64d(string):
	'''Base64 decode a string and cut off the SplatNet prefix.'''

	thing_id = base64.b64decode(string).decode('utf-8')
	thing_id = thing_id.replace("VsStage-", "")
	thing_id = thing_id.replace("VsMode-", "")
	thing_id = thing_id.replace("Weapon-", "")
	thing_id = thing_id.replace("CoopStage-", "")
	thing_id = thing_id.replace("CoopGrade-", "")
	if thing_id[:15] == "VsHistoryDetail" or thing_id[:17] == "CoopHistoryDetail":
		return thing_id # string
	else:
		return int(thing_id) # integer


def epoch_time(time_string):
	'''Converts a playedTime string into an int representing the epoch time.'''

	utc_time = datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%SZ")
	epoch_time = int((utc_time - datetime.datetime(1970, 1, 1)).total_seconds())
	return epoch_time


def gen_graphql_body(sha256hash, varname=None, varvalue=None):
	'''Generates a JSON dictionary, specifying information to retrieve, to send with GraphQL requests.'''
	great_passage = {
		"extensions": {
			"persistedQuery": {
				"sha256Hash": sha256hash,
				"version": 1
			}
		},
		"variables": {}
	}

	if varname is not None and varvalue is not None:
		great_passage["variables"][varname] = varvalue

	return json.dumps(great_passage)


def custom_key_exists(key, config_data, value=True):
	'''Checks if a given custom key exists in config.txt and is set to the specified value (true by default).'''

	# https://github.com/frozenpandaman/s3s/wiki/config-keys
	if key not in ["ignore_private", "app_user_agent", "force_uploads"]:
		print("(!) Checking unexpected custom key")
	return True if key in config_data and config_data[key].lower() == str(value).lower() else False


if __name__ == "__main__":
	print("This program cannot be run alone. See https://github.com/frozenpandaman/s3s")
	sys.exit(0)
