import requests
import bs4
import json
import re
import time

#Выполнил: студент ОмГТУ группы ИВТ-254 Конарев И.

class FarmakopeikaParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Referer': 'https://farmakopeika.ru/',
        }
        self.products = []

    def parse_from_web(self, start_page=1, end_page=609, delay=1):
        base_url = "https://farmakopeika.ru/catalog/2440"
        session = requests.Session()
        session.headers.update(self.headers)

        for page_num in range(start_page, end_page + 1):
            page_url = f"{base_url}?page={page_num}" if page_num > 1 else base_url

            try:
                print(f"\n[WEB] Загрузка страницы {page_num}/{end_page}: {page_url}")
                response = session.get(page_url, timeout=30)

                if response.status_code == 200:
                    print(f"[WEB] Успешно ({len(response.text)} байт)")
                    self._parse_page_content(response.text)
                else:
                    print(f"[WEB] Ошибка: статус {response.status_code}")
                    continue

                if delay > 0:
                    time.sleep(delay)

            except Exception as e:
                print(f"[WEB] Ошибка: {e}")
                continue

        return self.products

    def _parse_page_content(self, html_content):
        page_products = 0

        soup = bs4.BeautifulSoup(html_content, 'lxml')

        for tag in soup(['script', 'style', 'svg', 'path']):
            tag.decompose()

        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)

        pattern = r'([А-Яа-яA-Za-z0-9\s/№,\-+.()]+?)\s+от\s+([\d\s.,]+)\s*₽\s+В\s+корзину'

        matches = re.findall(pattern, text, re.IGNORECASE)

        for name, price in matches:
            name = name.strip()
            price_clean = re.sub(r'\s+', '', price).replace(',', '.')

            if name and len(name) > 5 and price_clean and re.match(r'^\d+\.?\d*$', price_clean):
                if 'В корзину' not in name and 'стр' not in name[-10:]:
                    self.products.append({
                        'name': name,
                        'price': price_clean
                    })
                    page_products += 1

        print(f"[WEB] Извлечено с этой страницы: {page_products} товаров")

    def get_products_list(self):
        return self.products

    def save_to_json(self, filename='farmakopeika_products.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVE] Данные сохранены в {filename}")

    def print_summary(self, limit=20):
        print(f"\n{'=' * 80}")
        print(f"Парсинг завершен. Всего товаров: {len(self.products)}")
        print(f"{'=' * 80}\n")

        if not self.products:
            print("Товары не найдены.")
            print("\nПример текста со страницы (первые 1000 символов):")
            return

        print(f"{'№':<4} {'Название':<55} {'Цена (₽)':>12}")
        print(f"{'-' * 80}")

        for i, product in enumerate(self.products[:limit], 1):
            name_display = (product['name'][:52] + '...') if len(product['name']) > 55 else product['name']
            print(f"{i:<4} {name_display:<55} {product['price']:>12}")

        if len(self.products) > limit:
            print(f"\n... и ещё {len(self.products) - limit} товаров")


if __name__ == "__main__":
    parser = FarmakopeikaParser()

    parser.parse_from_web(start_page=1, end_page=609, delay=1)

    parser.print_summary(20)
    parser.save_to_json('farmakopeika_products.json')