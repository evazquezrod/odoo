import time
import base64
import hashlib
import hmac
import logging
import requests
from urllib.parse import urlencode


WALLEE_WEB_API_ENDPOINT = "https://app-wallee.com:443"
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 5
# REQUEST_TIMEOUT = CONNECT_TIMEOUT + READ_TIMEOUT

_logger = logging.getLogger(__name__)

def generate_wallee_signature(version, timestamp, userid, auth_key, http_method, path, params) -> str:
    authentication_message = "|".join(map(str, [
        version,
        userid,
        timestamp,
        http_method,
        "/api" + path + (("?" + urlencode(params)) if params else ""),
    ])).encode('utf-8')
    return base64.b64encode(
        hmac.new(
            base64.b64decode(auth_key), authentication_message, hashlib.sha512,
        ).digest()
    ).decode('utf-8')

def generate_wallee_request_headers(userid, auth_key, http_method, path, params) -> dict:
    version = "1"
    timestamp = str(int(time.time()))
    return {
        'x-mac-version': version,
        'x-mac-timestamp': timestamp,
        'x-mac-userid': userid,
        'x-mac-value': generate_wallee_signature(version, timestamp, userid, auth_key, http_method, path, params),
        # 'x-wallee-logtoken': uuid,
    }

def call_wallee_web_service_api(userid, auth_key, http_method, path, params, payload=None, read_timeout=READ_TIMEOUT) -> dict:
    url = f"{WALLEE_WEB_API_ENDPOINT}/api{path}"
    try:
        headers = generate_wallee_request_headers(userid, auth_key, http_method, path, params)
    except Exception as error:
        _logger.warning("Error while generating wallee mac value: %s", error)
        return {'error': error}

    try:
        print("-------------------- Wallee API request --------------------", url, params, headers, payload)
        if http_method == "GET":
            response = requests.get(url=url, params=params, headers=headers, timeout=(CONNECT_TIMEOUT, read_timeout))
        elif http_method == "POST":
            response = requests.post(url=url, params=params, headers=headers, json=payload, timeout=(CONNECT_TIMEOUT, read_timeout))
        # else:
        #     raise ValueError(f"Unsupported HTTP method: {http_method}")
        #     return {'error': f"Unsupported HTTP method: {http_method}"}
        print("-------------------- Wallee API response --------------------", response.status_code, response.json())
    except requests.exceptions.RequestException as error:
        _logger.warning("An unexpected error occurred: %s", error)
        return {'error': f"An unexpected error occurred: {error}"}
    except requests.exceptions.ConnectionError as error:
        _logger.warning("Connection error occurred: %s", error)
        return {'error': f"Connection error occurred: {error}"}
    except requests.exceptions.ConnectTimeout as error:
        _logger.warning("Connection timed out: %s", error)
        return {'error': f"Connection timed out: Could not connect to Wallee web service: {error}"}
    except requests.exceptions.ReadTimeout as error:
        _logger.warning("Read timed out: Wallee server took too long to respond: %s", error)
        return {'error': f"Read timed out: Wallee server took too long to respond: {error}"}

    try:
        # elif response.get('status_code') in [442, 542] or data.get('message') or (data.get('type') and "ERROR" in data.get('type')):
        #     return {'error': f"{data.get('type')} - {data.get('message')}"}

        # elif response.get('status_code') in [442, 542] or data.get('message'):
        #     return {'error': f"{data.get('type')} - {data.get('message')}"}
        data = response.json() if response.content else None
        response.raise_for_status()
        return data
        # return {
        #     'status_code': response.status_code,
        #     'data': data,
        # }
    except ValueError as error:
        _logger.warning("Cannot parse Wallee response. Error: %s", error)
        return {'error': f"Error while parsing wallee response: {error}"}
    except requests.exceptions.HTTPError as error:
        _logger.warning("HTTP error occurred: %s: %s", error, data.get('message'))
        return {
            'status_code': response.status_code,
            'error': f"HTTP error occurred: {data.get('message', '')}",
        }

# if __name__ == "__main__":
#     headers = get_wallee_common_auth_request_headers(
#         userid="139111",
#         auth_key="nxRSx78U8ZgHaK0AJZlIY2A6TVvy/+y7yzXZq82HPx4=",
#         http_method="GET",
#         path="/payment-processor/all",
#         # params={
#         #     'spaceId': 36188,
#         #     'id': 370606231,
#         # }
#     )
#     print(headers)

#     call_wallee_web_service_api(
#         userid="139111",
#         auth_key="nxRSx78U8ZgHaK0AJZlIY2A6TVvy/+y7yzXZq82HPx4=",
#         http_method="GET",
#         path="/payment/all",
#         params={
#             'spaceId': 36188,
#             'id': 370606231,
#         },
#         read_timeout=0.000001,
#     )
