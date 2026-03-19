use reqwest;

pub struct ParsedProduct {
    pub name: String,
    pub price: f64,
    pub old_price: Option<f64>,
}

pub async fn fetch_product(url: &str) -> Result<ParsedProduct, String> {
    let parser_base = std::env::var("PARSER_URL").unwrap_or_else(|_| "http://localhost:3001".to_string());
    let parser_url = format!(
        "{}/?url={}",
        parser_base,
        url
    );

    let response = reqwest::get(&parser_url)
        .await
        .map_err(|e| format!("Не вдалось зробити запит: {}", e))?;
    
    match response.status().as_u16() {
        200 => {
            let json: serde_json::Value = response
                .json()
                .await
                .map_err(|e| format!("Помилка парсингу JSON: {}", e))?;

            Ok(ParsedProduct {
                name: json["name"].as_str().unwrap_or("").to_string(),
                price: json["price"].as_f64().unwrap_or(0.0),
                old_price: json["old_price"].as_f64(),
            })
        }
        404 => Err("Товар не знайдено на сайті".to_string()),
        400 => Err("Невірне посилання".to_string()),
        500 => Err("Помилка парсингу сторінки".to_string()),
        code => Err(format!("Невідомий статус код: {}", code)),
    }
}