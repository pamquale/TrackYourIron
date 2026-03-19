# Контракты взаимодействия сервисов (Iron Price Monitor)

В этом документе описаны правила обмена сообщениями через брокер **NATS**.
**Строгое правило для всех:** 1. Используем только **JSON**. Никакого Protobuf.
2. Все ключи пишем строго в **snake_case** (например: `new_price`, а не `newPrice`).

---

## 1. Событие: Обнаружено падение цены (PriceDroppedEvent)

Генерируется, когда Scraper Service (Аня) находит цену ниже, чем та, что сохранена в базе.

* **Продюсер:** Scraper Service (Rust)
* **Консьюмер:** Notification Service / Telegram Bot (Python)
* **NATS Топик:** `events.price_dropped`

**Структура JSON:**
```json
{
  "product_id": 105,
  "new_price": 14500.50,
  "store_link": "[https://telemart.ua/item/rtx-5060-ti-example](https://telemart.ua/item/rtx-5060-ti-example)"
}