import json
import logging
import random
import time
from datetime import datetime
from uuid import uuid4

import requests

from settings import APP_TOKEN, PROMO_ID, API_URL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class HamsterCode:
    game_timeout = 40
    login_token = None
    tokens = []
    headers = {"Content-Type": "application/json; charset=utf-8"}

    @classmethod
    def _timeout(cls) -> None:
        logger.info(f"Waiting for {cls.game_timeout} seconds...")
        time.sleep(cls.game_timeout)

    @staticmethod
    def _get_random_client_id() -> str:
        dt = str(round(datetime.now().timestamp() * 1000))
        rnd = ''.join([str(random.randint(0, 9)) for _ in range(19)])
        return f'{dt}-{rnd}'

    def _login(self) -> None:
        r = requests.post(
            url=f"{API_URL}/login-client",
            headers=self.headers,
            json={
                "appToken": APP_TOKEN,
                "clientId": self._get_random_client_id(),
                "clientOrigin": "deviceid",
            }
        )
        logger.debug(r)
        token = json.loads(r.content).get('clientToken')
        logger.info(token)
        self.login_token = token
        self.headers.update({"authorization": f"Bearer {self.login_token}"})

    def _register_event(self) -> bool:
        event_id = str(uuid4())
        logger.debug(event_id)

        body = {
            "promoId": PROMO_ID,
            "eventId": event_id,
            "eventOrigin": "undefined",
        }

        self._timeout()

        for _ in range(6):
            logger.info("Emulate one game event")
            r = requests.post(url=f"{API_URL}/register-event", headers=self.headers, json=body)
            logger.debug(r)
            has_code = json.loads(r.content).get('hasCode')
            logger.debug(f'{has_code=}')
            if has_code:
                logger.info("Got it!")
                return True
            logger.info("Game finished, there is no code as a result. Waiting for the next one...")
            self._timeout()
        return False

    def _request_code(self) -> str:
        body = {
            "promoId": PROMO_ID,
        }

        r = requests.post(f"{API_URL}/create-code", headers=self.headers, json=body)
        logger.debug(r)

        return json.loads(r.content).get('promoCode')

    def get_code(self) -> str:
        self._login()
        if self._register_event():
            return self._request_code()


if __name__ == '__main__':
    generated_codes = []
    for i in range(4):
        code_generator = HamsterCode()
        generated_codes.append(code_generator.get_code())
        print(code_generator.tokens)
