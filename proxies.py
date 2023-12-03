import requests
import random
import redis
from bs4 import BeautifulSoup


RETRY_TIMEOUT = 5
MAX_RETRIES = 5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/90.0.4430.78 Mobile/14E5239e Safari/602.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/90.0.818.56",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko"
]
redis_client = redis.StrictRedis(
    host='localhost', port=6379, db=0, decode_responses=True)


def fetch_proxies(url='https://www.sslproxies.org/'):
    proxies = []
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    rows = table.tbody.find_all('tr')
    for row in rows:
        ip = row.find_all('td')[0].text
        port = row.find_all('td')[1].text
        proxies.append(f'http://{ip}:{port}')
    return proxies


def verify_proxies(proxies, test_url='https://www.linkedin.com'):
    working_proxies = []
    for proxy in proxies:
        try:
            response = requests.get(
                test_url, proxies={'http': proxy, 'https': proxy}, timeout=5)
            if response.status_code == 200:
                working_proxies.append(proxy)
                print("Working Proxy:", proxy)
        except requests.exceptions.RequestException as e:
            print(f"Proxy failed: {proxy}, Error: {e}")
    return working_proxies


def get_request_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS)
    }


def fetch_and_verify_proxies():
    print("Hold on! Fetching fresh proxies...")
    proxies = fetch_proxies()
    return verify_proxies(proxies)


def store_verified_proxies(proxies):
    key = 'verified_proxies'
    # Convert list to strings for Redis storage
    proxies_str = [str(proxy) for proxy in proxies]
    redis_client.delete(key)
    if proxies_str:
        redis_client.rpush(key, *proxies_str)


def get_verified_proxies():
    key = 'verified_proxies'
    proxies = redis_client.lrange(key, 0, -1)
    # Since decode_responses=True, no need to decode manually
    return proxies


def is_proxy_refresh_needed():
    return len(get_verified_proxies()) < 5
