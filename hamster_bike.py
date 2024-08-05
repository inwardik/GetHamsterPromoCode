import json
import logging
import random
import re
import time
from datetime import datetime

import requests

from tokens import APP_TOKEN, PROMO_ID

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class HamsterCode:
    def __init__(self, game_timeout=40):
        self.login_token = None
        self.game_timeout = game_timeout

    @staticmethod
    def _get_random_client_id() -> str:
        dt = str(round(datetime.now().timestamp() * 1000))
        rnd = ''.join([str(random.randint(0, 9)) for _ in range(19)])
        return f'{dt}-{rnd}'

    @staticmethod
    def _generate_uuid():
        def replacer(match):
            char = match.group(0)
            if char == 'x':
                return hex(random.randint(0, 15))[2:]
            elif char == 'y':
                return hex(random.randint(8, 11))[2:]

        pattern = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
        return re.sub(r'[xy]', replacer, pattern)

    def _login(self):
        headers = {
            "content-type": "application/json; charset=utf-8",
        }

        body = {
            "appToken": APP_TOKEN,
            "clientId": self._get_random_client_id(),
            "clientOrigin": "deviceid",
        }
        r = requests.post("https://api.gamepromo.io/promo/login-client", headers=headers, json=body)
        logger.debug(r)
        token = json.loads(r.content).get('clientToken')
        logger.info(token)
        self.login_token = token

    def _register_event(self) -> bool:
        event_id = self._generate_uuid()
        logger.debug(event_id)

        headers = {
            "authorization": f"Bearer {self.login_token}",
            "Content-Type": "application/json; charset=utf-8",
          }

        body = {
            "promoId": PROMO_ID,
            "eventId": event_id,
            "eventOrigin": "undefined",
        }

        time.sleep(self.game_timeout)

        for _ in range(6):
            logger.info("Emulate one game event")
            r = requests.post("https://api.gamepromo.io/promo/register-event", headers=headers, json=body)
            logger.debug(r)
            has_code = json.loads(r.content).get('hasCode')
            logger.debug(f'{has_code=}')
            if has_code:
                logger.info("Got it!")
                return True
            logger.info("Game finished, there is no code as a result. Waiting for the next one...")
            time.sleep(self.game_timeout)
        return False

    def _request_code(self):
        headers = {
            "authorization": f"Bearer {self.login_token}",
            "Content-Type": "application/json; charset=utf-8",
          }

        body = {
            "promoId": PROMO_ID,
        }

        r = requests.post("https://api.gamepromo.io/promo/create-code", headers=headers, json=body)
        logger.debug(r)

        return json.loads(r.content).get('promoCode')

    def get_code(self) -> str:
        self._login()
        if self._register_event():
            return self._request_code()


if __name__ == '__main__':
    for i in range(4):
        code_generator = HamsterCode()
        code = code_generator.get_code()
        print(code)
