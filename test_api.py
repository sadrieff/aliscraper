import requests
import json

API_URL = "http://127.0.0.1:8000/api/v1/parse"
CORRECT_TOKEN = "my_mega_secret_token"

def test_auth():
    url_to_parse = "https://aliexpress.ru/item/1005007188393531.html"
    
    print("--- Тест 1: Без токена ---")
    try:
        r = requests.post(API_URL, json={"url": url_to_parse})
        print(f"Статус: {r.status_code}, Ответ: {r.text}")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n--- Тест 2: Неправильный токен ---")
    try:
        r = requests.post(API_URL, json={"url": url_to_parse}, headers={"X-API-Key": "wrong_one"})
        print(f"Статус: {r.status_code}, Ответ: {r.text}")
    except Exception as e:
        print(f"Ошибка: {e}")

    print("\n--- Тест 3: Правильный токен ---")
    try:
        # Для теста 3 мы не будем ждать полного парсинга (он долгий), нам главное увидеть, что 403 не вылетел
        # Но FastAPI сначала проверяет заголовки, потом пускает в функцию.
        r = requests.post(API_URL, json={"url": url_to_parse}, headers={"X-API-Key": CORRECT_TOKEN}, timeout=5)
        print(f"Статус: {r.status_code} (Если не 403, то авторизация прошла!)")
    except requests.exceptions.Timeout:
        print("Статус: Авторизация прошла (таймаут на парсинге, это нормально)")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    test_auth()
