import asyncio
import logging
import random
from datetime import datetime
from uuid import uuid4

import aiohttp
from settings import API_URL, GAMES, BOT_TOKEN, CHAT_ID

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class HamsterGame:
    def __init__(self, name, token, promo_id, timeout, max_codes, max_retry):
        self.name = name
        self.token = token
        self.promo_id = promo_id
        self.timeout = timeout
        self.max_codes = max_codes
        self.max_retry = max_retry
        self.codes = set()
        self.last_promo_code = None

    def log(self, msg):
        logger.info(f"({self.name.upper()}) - {msg}")

    @staticmethod
    def get_random_client_id() -> str:
        dt = str(round(datetime.now().timestamp() * 1000))
        rnd = ''.join([str(random.randint(0, 9)) for _ in range(19)])
        return f'{dt}-{rnd}'

    async def authenticate(self, session):
        async with session.post(
                url=f"{API_URL}/login-client",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json={
                    "appToken": self.token,
                    "clientId": self.get_random_client_id(),
                    "clientOrigin": "deviceid",
                }
        ) as response:
            data = await response.json()
            sleep_time = random.randint(*self.timeout)
            self.log(f"Auth is OK. Waiting for {sleep_time} second(s)...")
            await asyncio.sleep(sleep_time)
            return data['clientToken']

    async def get_event_code(self, session, token):
        headers = {
            'Authorization': f'Bearer {token}',
            "Content-Type": "application/json; charset=utf-8",
        }
        body = {
            "promoId": self.promo_id,
        }

        async with session.post(url=f"{API_URL}/create-code", headers=headers, json=body) as response:
            code = await response.json()
            promo_code = code['promoCode']
            self.log(f"Game promo code received: {promo_code}")
            self.codes.add(promo_code)
            self.last_promo_code = promo_code

    async def register_event(self, session, token):
        headers = {
            'Authorization': f'Bearer {token}',
            "Content-Type": "application/json; charset=utf-8",
        }
        body = {
            "promoId": self.promo_id,
            "eventId": str(uuid4()),
            "eventOrigin": "undefined",
        }
        for attempt in range(self.max_retry):
            sleep_time = random.randint(*self.timeout)
            async with session.post(
                    url=f"{API_URL}/register-event",
                    headers=headers,
                    json=body
            ) as response:
                response_json = await response.json()
                if response_json.get('hasCode'):
                    return response_json.get('hasCode')
                else:
                    self.log("No code found. Trying again...")
                if attempt < self.max_retry - 1:
                    self.log(f"Waiting for the next try after {sleep_time} second(s)...")
                    await asyncio.sleep(sleep_time)

    async def start_game(self, session):
        while not len(self.codes) == self.max_codes:
            token = await self.authenticate(session)
            code = await self.register_event(session, token)
            if code not in self.codes:
                await self.get_event_code(session, token)
        self.log(f"Finished search codes: {list(self.codes)}")
        return list(self.codes)


async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [HamsterGame(**game).start_game(session) for game in GAMES]
        game_codes = await asyncio.gather(*tasks)
        for game in game_codes:
            for code in game:
                print(code)

            if BOT_TOKEN and CHAT_ID:
                await session.post(
                    url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": CHAT_ID,
                        "text": '\n\r'.join([f"`{g}`\n\r" for g in game]),
                        "parse_mode": "Markdown"
                    }
                )


if __name__ == "__main__":
    asyncio.run(main())
