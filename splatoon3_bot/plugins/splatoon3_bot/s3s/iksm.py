# (ↄ) 2017-2022 eli fessler (frozenpandaman), clovervidia
# https://github.com/frozenpandaman/s3s
# License: GPLv3

from loguru import logger
import base64, hashlib, json, os, re, sys
import requests
from bs4 import BeautifulSoup
from ..utils import BOT_VERSION

session = requests.Session()
S3S_VERSION = "unknown"
NSOAPP_VERSION = "2.6.0"

# functions in this file & call stack:
# get_nsoapp_version()
# log_in() -> get_session_token()
# get_gtoken() -> call_imink_api() -> f
# get_bullet()
# enter_tokens()

# place config.txt in same directory as script (bundled or not)
if getattr(sys, 'frozen', False):
	app_path = os.path.dirname(sys.executable)
elif __file__:
	app_path = os.path.dirname(__file__)
config_path = os.path.join(app_path, "config.txt")

def get_nsoapp_version():
	'''Fetches the current Nintendo Switch Online app version from the Apple App Store.'''

	try:
		page = requests.get("https://apps.apple.com/us/app/nintendo-switch-online/id1234806557")
		soup = BeautifulSoup(page.text, 'html.parser')
		elt = soup.find("p", {"class": "whats-new__latest__version"})
		ver = elt.get_text().replace("Version ", "").strip()
		return ver
	except:
		return NSOAPP_VERSION


def log_in(ver):
	'''Logs in to a Nintendo Account and returns a session_token.'''

	global S3S_VERSION
	S3S_VERSION = ver

	auth_state = base64.urlsafe_b64encode(os.urandom(36))

	auth_code_verifier = base64.urlsafe_b64encode(os.urandom(32))
	auth_cv_hash = hashlib.sha256()
	auth_cv_hash.update(auth_code_verifier.replace(b"=", b""))
	auth_code_challenge = base64.urlsafe_b64encode(auth_cv_hash.digest())

	app_head = {
		'Host':                      'accounts.nintendo.com',
		'Connection':                'keep-alive',
		'Cache-Control':             'max-age=0',
		'Upgrade-Insecure-Requests': '1',
		'User-Agent':                'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Mobile Safari/537.36',
		'Accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8n',
		'DNT':                       '1',
		'Accept-Encoding':           'gzip,deflate,br',
	}

	body = {
		'state':                               auth_state,
		'redirect_uri':                        'npf71b963c1b7b6d119://auth',
		'client_id':                           '71b963c1b7b6d119',
		'scope':                               'openid user user.birthday user.mii user.screenName',
		'response_type':                       'session_token_code',
		'session_token_code_challenge':        auth_code_challenge.replace(b"=", b""),
		'session_token_code_challenge_method': 'S256',
		'theme':                               'login_form'
	}

	url = 'https://accounts.nintendo.com/connect/1.0.0/authorize'
	r = session.get(url, headers=app_head, params=body)

	post_login = r.history[0].url

	logger.info("\nMake sure you have fully read the \"Token generation\" section of the readme before proceeding. To manually input a token instead, enter \"skip\" at the prompt below.")
	logger.info("\nNavigate to this URL in your browser:")
	logger.info(post_login)
	logger.info("Log in, right click the \"Select this account\" button, copy the link address, and paste it below:")
	while True:
		try:
			use_account_url = input("")
			if use_account_url == "skip":
				return "skip"
			session_token_code = re.search('de=(.*)&', use_account_url)
			return get_session_token(session_token_code.group(1), auth_code_verifier)
		except KeyboardInterrupt:
			logger.info("\nBye!")
			return
		except AttributeError:
			logger.error("Malformed URL. Please try again, or press Ctrl+C to exit.")
			logger.error("URL:", end=' ')
		except KeyError: # session_token not found
			logger.error("\nThe URL has expired. Please log out and back into your Nintendo Account and try again.")
			return


def get_session_token(session_token_code, auth_code_verifier):
	'''Helper function for log_in().'''

	nsoapp_version = get_nsoapp_version()

	app_head = {
		'User-Agent':      f'OnlineLounge/{nsoapp_version} NASDKAPI Android',
		'Accept-Language': 'en-US',
		'Accept':          'application/json',
		'Content-Type':    'application/x-www-form-urlencoded',
		'Content-Length':  '540',
		'Host':            'accounts.nintendo.com',
		'Connection':      'Keep-Alive',
		'Accept-Encoding': 'gzip'
	}

	body = {
		'client_id':                   '71b963c1b7b6d119',
		'session_token_code':          session_token_code,
		'session_token_code_verifier': auth_code_verifier.replace(b"=", b"")
	}

	url = 'https://accounts.nintendo.com/connect/1.0.0/api/session_token'

	r = session.post(url, headers=app_head, data=body)
	return json.loads(r.text)["session_token"]


def get_gtoken(f_gen_url, session_token, ver):
	"""Provided the session_token, returns a GameWebToken and account info."""

	nsoapp_version = get_nsoapp_version()

	global S3S_VERSION
	S3S_VERSION = ver

	app_head = {
		'Host':            'accounts.nintendo.com',
		'Accept-Encoding': 'gzip',
		'Content-Type':    'application/json',
		'Content-Length':  '436',
		'Accept':          'application/json',
		'Connection':      'Keep-Alive',
		'User-Agent':      'Dalvik/2.1.0 (Linux; U; Android 7.1.2)'
	}

	body = {
		'client_id':     '71b963c1b7b6d119',
		'session_token': session_token,
		'grant_type':    'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token'
	}

	url = "https://accounts.nintendo.com/connect/1.0.0/api/token"
	r = requests.post(url, headers=app_head, json=body)
	id_response = json.loads(r.text)

	# get user info
	try:
		app_head = {
			'User-Agent':      'NASDKAPI; Android',
			'Content-Type':    'application/json',
			'Accept':          'application/json',
			'Authorization':   f'Bearer {id_response["access_token"]}',
			'Host':            'api.accounts.nintendo.com',
			'Connection':      'Keep-Alive',
			'Accept-Encoding': 'gzip'
		}
	except:
		logger.warning("Not a valid authorization request. Please delete config.txt and try again.")
		logger.warning("Error from Nintendo (in api/token step):")
		logger.warning(json.dumps(id_response, indent=2))
		return

	url = "https://api.accounts.nintendo.com/2.0.0/users/me"
	r = requests.get(url, headers=app_head)
	user_info = json.loads(r.text)

	user_nickname = user_info["nickname"]
	user_lang     = user_info["language"]
	user_country  = user_info["country"]
	user_id       = user_info["id"]

	# get access token
	body = {}
	try:
		id_token = id_response["id_token"]
		f, uuid, timestamp = call_imink_api(id_token, 1, f_gen_url, user_id)

		parameter = {
			'f':          f,
			'language':   user_lang,
			'naBirthday': user_info["birthday"],
			'naCountry':  user_country,
			'naIdToken':  id_token,
			'requestId':  uuid,
			'timestamp':  timestamp
		}
	except SystemExit:
		return
	except:
		logger.warning("Error(s) from Nintendo:")
		logger.warning(json.dumps(id_response, indent=2))
		logger.warning(json.dumps(user_info, indent=2))
		return
	body["parameter"] = parameter

	app_head = {
		'X-Platform':       'Android',
		'X-ProductVersion': nsoapp_version,
		'Content-Type':     'application/json; charset=utf-8',
		'Content-Length':   str(990 + len(f)),
		'Connection':       'Keep-Alive',
		'Accept-Encoding':  'gzip',
		'User-Agent':       f'com.nintendo.znca/{nsoapp_version}(Android/7.1.2)',
	}

	url = "https://api-lp1.znc.srv.nintendo.net/v3/Account/Login"
	r = requests.post(url, headers=app_head, json=body)
	splatoon_token = json.loads(r.text)

	try:
		id_token = splatoon_token["result"]["webApiServerCredential"]["accessToken"]
		coral_user_id = splatoon_token["result"]["user"]["id"]
	except:
		# retry once if 9403/9599 error from nintendo
		try:
			f, uuid, timestamp = call_imink_api(id_token, 1, f_gen_url, user_id)
			body["parameter"]["f"]         = f
			body["parameter"]["requestId"] = uuid
			body["parameter"]["timestamp"] = timestamp
			app_head["Content-Length"]     = str(990 + len(f))
			url = "https://api-lp1.znc.srv.nintendo.net/v3/Account/Login"
			r = requests.post(url, headers=app_head, json=body)
			splatoon_token = json.loads(r.text)
			id_token = splatoon_token["result"]["webApiServerCredential"]["accessToken"]
			coral_user_id = splatoon_token["result"]["user"]["id"]
		except:
			logger.warning("Error from Nintendo (in Account/Login step):")
			logger.warning(json.dumps(splatoon_token, indent=2))
			logger.warning("Re-running the script usually fixes this.")
			return

		f, uuid, timestamp = call_imink_api(id_token, 2, f_gen_url, user_id, coral_user_id=coral_user_id)

	# get web service token
	app_head = {
		'X-Platform':       'Android',
		'X-ProductVersion': nsoapp_version,
		'Authorization':    f'Bearer {id_token}',
		'Content-Type':     'application/json; charset=utf-8',
		'Content-Length':   '391',
		'Accept-Encoding':  'gzip',
		'User-Agent':       f'com.nintendo.znca/{nsoapp_version}(Android/7.1.2)'
	}

	body = {}
	parameter = {
		'f':                 f,
		'id':                4834290508791808,
		'registrationToken': id_token,
		'requestId':         uuid,
		'timestamp':         timestamp
	}
	body["parameter"] = parameter

	url = "https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken"
	r = requests.post(url, headers=app_head, json=body)
	web_service_resp = json.loads(r.text)

	try:
		web_service_token = web_service_resp["result"]["accessToken"]
	except:
		# retry once if 9403/9599 error from nintendo
		try:
			f, uuid, timestamp = call_imink_api(id_token, 2, f_gen_url, user_id, coral_user_id=coral_user_id)
			body["parameter"]["f"]         = f
			body["parameter"]["requestId"] = uuid
			body["parameter"]["timestamp"] = timestamp
			url = "https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken"
			r = requests.post(url, headers=app_head, json=body)
			web_service_resp = json.loads(r.text)
			web_service_token = web_service_resp["result"]["accessToken"]
		except:
			logger.warning("Error from Nintendo (in Game/GetWebServiceToken step):")
			logger.warning(json.dumps(web_service_resp, indent=2))
			return

	return web_service_token, user_nickname, user_lang, user_country


def get_bullet(web_service_token, web_view_ver, app_user_agent, user_lang, user_country):
	'''Returns a bulletToken.'''

	app_head = {
		'Content-Length':   '0',
		'Content-Type':     'application/json',
		'Accept-Language':  user_lang,
		'User-Agent':       app_user_agent,
		'X-Web-View-Ver':   web_view_ver,
		'X-NACOUNTRY':      user_country,
		'Accept':           '*/*',
		'Origin':           'https://api.lp1.av5ja.srv.nintendo.net',
		'X-Requested-With': 'com.nintendo.znca'
	}
	app_cookies = {
		'_gtoken': web_service_token # X-GameWebToken
	}
	url = "https://api.lp1.av5ja.srv.nintendo.net/api/bullet_tokens"
	r = requests.post(url, headers=app_head, cookies=app_cookies)

	if r.status_code == 401:
		logger.error("Unauthorized error (ERROR_INVALID_GAME_WEB_TOKEN). Cannot fetch tokens at this time.")
		return
	elif r.status_code == 403:
		logger.error("Forbidden error (ERROR_OBSOLETE_VERSION). Cannot fetch tokens at this time.")
		return
	elif r.status_code == 204: # No Content, USER_NOT_REGISTERED
		logger.error("Cannot access SplatNet 3 without having played online.")
		return

	try:
		bullet_resp = json.loads(r.text)
		bullet_token = bullet_resp["bulletToken"]
	except (json.decoder.JSONDecodeError, TypeError):
		logger.error("Got non-JSON response from Nintendo (in api/bullet_tokens step:")
		logger.error(bullet_resp)
		return
	except:
		logger.error("Error from Nintendo (in api/bullet_tokens step):")
		logger.error(json.dumps(bullet_resp, indent=2))
		return

	return bullet_token


def call_imink_api(id_token, step, f_gen_url, user_id, coral_user_id=None):
	"""Passes in an naIdToken to the f API and fetches the response (comprised of an f token, UUID, and timestamp)."""

	api_head = {}
	api_body = {}
	api_response = None
	try:
		api_head = {
			'User-Agent':   f'splatoon3_bot/{BOT_VERSION}',
			'Content-Type': 'application/json; charset=utf-8',
			'X-znca-Platform': 'Android',
			'X-znca-Version': NSOAPP_VERSION
		}
		api_body = {
			'token':       id_token,
			'hash_method':  step,
			'na_id':       user_id
		}
		if step == 2 and coral_user_id is not None:
			api_body["coral_user_id"] = str(coral_user_id)

		api_response = requests.post(f_gen_url, data=json.dumps(api_body), headers=api_head)
		resp = json.loads(api_response.text)

		logger.debug(f"get f generation: \n{f_gen_url}\n{json.dumps(api_head)}\n{json.dumps(api_body)}")
		f = resp["f"]
		uuid = resp["request_id"]
		timestamp = resp["timestamp"]
		return f, uuid, timestamp
	except:
		try: # if api_response never gets set
			logger.warning(f"Error during f generation: \n{f_gen_url}\n{json.dumps(api_head)}\n{json.dumps(api_body)}")
			if api_response and api_response.text:
				logger.error(f"Error during f generation:\n{json.dumps(json.loads(api_response.text), indent=2, ensure_ascii=False)}")
			else:
				logger.error(f"Error during f generation: Error {api_response.status_code}.")
		except:
			logger.error(f"Couldn't connect to f generation API ({f_gen_url}). Please try again.")

		return


def enter_tokens():
	'''Prompts the user to enter a gtoken and bulletToken.'''

	print("Go to the page below to find instructions to obtain your gtoken and bulletToken:\nhttps://github.com/frozenpandaman/s3s/wiki/mitmproxy-instructions\n")

	new_gtoken = input("Enter your gtoken: ")
	while len(new_gtoken) != 926:
		new_gtoken = input("Invalid token - length should be 926 characters. Try again.\nEnter your gtoken: ")

	new_bullettoken = input("Enter your bulletToken: ")
	while len(new_bullettoken) != 124:
		if len(new_bullettoken) == 123 and new_bullettoken[-1] != "=":
			new_bullettoken += "=" # add a = to the end, which was probably left off (even though it works without)
		else:
			new_bullettoken = input("Invalid token - length should be 124 characters. Try again.\nEnter your bulletToken: ")

	return new_gtoken, new_bullettoken


if __name__ == "__main__":
	print("This program cannot be run alone. See https://github.com/frozenpandaman/s3s")
	sys.exit(0)
