use async_nats::Client;
use serde::{Serialize, Deserialize};
use serde_json;

#[derive(Serialize, Deserialize)]
pub struct PriceDroppedEvent {
    pub product_id: i32,
    pub new_price: f64,
    pub store_link: String,
}

pub async fn publish_price_dropped(
    client: &Client,
    event: PriceDroppedEvent
) {
    let json = serde_json::to_string(&event)
        .expect("Не вдалось серіалізувати подію");

    client
        .publish("events.price_dropped", json.into())
        .await
        .expect("Не вдалось опублікувати подію");

    println!("✅ Опубліковано подію для товару {}", event.product_id);
}
