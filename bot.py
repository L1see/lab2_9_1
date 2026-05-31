import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import json
import re
import requests
import bs4
import time
from datetime import datetime

#Выполнил: студент ОмГТУ группы ИВТ-254 Конарев И.

VK_TOKEN = 'Стреляй_не_отдам'
GROUP_ID = 239219036
DATA_FILE = 'farmakopeika_products.json'
ADMIN_IDS = [572828819] #мой ID в ВК

PARSER_CONFIG = {
    'base_url': "https://farmakopeika.ru/catalog/2440",
    'start_page': 1,
    'end_page': 609,
    'delay': 0.5,
    'timeout': 30
}


class InternalParser:

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
        self.products = []

    def fetch_and_parse(self):
        session = requests.Session()
        session.headers.update(self.headers)

        for page_num in range(PARSER_CONFIG['start_page'], PARSER_CONFIG['end_page'] + 1):
            page_url = f"{PARSER_CONFIG['base_url']}?page={page_num}" if page_num > 1 else PARSER_CONFIG['base_url']
            try:
                response = session.get(page_url, timeout=PARSER_CONFIG['timeout'])
                if response.status_code == 200:
                    self._parse_page(response.text)
                time.sleep(PARSER_CONFIG['delay'])
            except Exception:
                continue
        return self.products

    def _parse_page(self, html_content):
        soup = bs4.BeautifulSoup(html_content, 'lxml')
        for tag in soup(['script', 'style', 'svg']):
            tag.decompose()

        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)

        pattern = r'([А-Яа-яA-Za-z0-9\s/№,\-+.()]+?)\s+от\s+([\d\s.,]+)\s*₽\s+В\s+корзину'
        matches = re.findall(pattern, text, re.IGNORECASE)

        for name, price in matches:
            name = name.strip()
            price_clean = re.sub(r'\s+', '', price).replace(',', '.')

            if (name and len(name) > 5 and price_clean and
                    re.match(r'^\d+\.?\d*$', price_clean) and
                    'В корзину' not in name and 'стр' not in name[-10:]):
                self.products.append({'name': name, 'price': price_clean})


class FarmakopeikaBot:
    def __init__(self, token, group_id, data_file, admin_ids):
        self.vk = vk_api.VkApi(token=token)
        self.longpoll = VkLongPoll(self.vk)
        self.group_id = group_id
        self.data_file = data_file
        self.admin_ids = admin_ids
        self.products = self._load_products()
        self._is_refreshing = False

    def _load_products(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Файл {self.data_file} не найден. Запустите main.py для создания базы.")
            return []

    def _save_products(self, products):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

    def _search_product(self, query):
        query_lower = query.lower().strip()
        if len(query_lower) < 2:
            return None

        for product in self.products:
            if query_lower in product['name'].lower():
                return product
        return None

    def _format_price(self, price_str):
        try:
            price_float = float(price_str)
            return f"{price_float:,.2f}".replace(',', ' ').replace('.', ',') + ' ₽'
        except ValueError:
            return f"{price_str} ₽"

    def _format_response(self, product, query):
        if not product:
            return (
                f"  Товар «{query}» не найден.\n\n"
                f"  Попробуйте:\n"
                f"- Проверить название (например: «куркумин», «цинк», «омега»)\n"
                f"- Ввести часть названия бренда или препарата"
            )

        return (
            f"Найдено:\n"
            f"{product['name']}\n"
            f"Цена: от {self._format_price(product['price'])}\n\n"
            f"Заказать: https://farmakopeika.ru/catalog/2440"
        )

    def _send_message(self, user_id, text):
        self.vk.method('messages.send', {
            'peer_id': user_id,
            'message': text,
            'random_id': get_random_id()
        })

    def _handle_refresh(self, user_id):
        if user_id not in self.admin_ids:
            self._send_message(user_id, "Доступ запрещён. Команда /refresh только для админов.")
            return

        if self._is_refreshing:
            self._send_message(user_id, "Обновление уже выполняется!")
            return

        self._is_refreshing = True
        self._send_message(user_id, "Запускаю обновление базы данных. Это займет несколько минут.")

        try:
            parser = InternalParser()
            new_products = parser.fetch_and_parse()

            if new_products:
                self.products = new_products
                self._save_products(new_products)
                msg = (
                    f"Обновление завершено!\n"
                    f"Найдено товаров: {len(new_products)}\n"
                    f"Время: {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                msg = "Ошибка: не удалось найти товары при обновлении."

            self._send_message(user_id, msg)

        except Exception as e:
            self._send_message(user_id, f"Ошибка при обновлении: {e}")

        finally:
            self._is_refreshing = False

    def run(self):
        print(f"Бот запущен.")

        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_message = event.text.strip()
                user_id = event.user_id

                # Команда обновления
                if user_message.lower() == '/refresh':
                    self._handle_refresh(user_id)
                    continue

                # Справка
                if user_message.lower() in ['/start', '/help', 'привет']:
                    self._send_message(
                        user_id,
                        "Привет! Я бот парсер лекарств с сайта «Фармакопейка» г.Омск.\n"
                        "Напишите название товара, чтобы узнать цену.\n"
                        "Команды: /help для помощи, /refresh (админ) для обновления БД\n"
                        "Выполнил: Студент ИВТ-254 ОмГТУ К.И."
                    )
                    continue

                # Поиск
                result = self._search_product(user_message)
                response = self._format_response(result, user_message)
                self._send_message(user_id, response)


if __name__ == "__main__":
    bot = FarmakopeikaBot(
        token=VK_TOKEN,
        group_id=GROUP_ID,
        data_file=DATA_FILE,
        admin_ids=ADMIN_IDS
    )
    bot.run()