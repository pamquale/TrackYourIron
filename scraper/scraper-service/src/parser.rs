use scraper::{Html, Selector};

pub struct ProductInfo {
    pub name: String,
    pub price: f64,
    pub old_price: Option<f64>,
    pub discount: Option<String>,
}

pub fn parse_product(html: &str) -> ProductInfo {
    let document = Html::parse_document(html);

    let name_selector = Selector::parse("h1.card-block__title").unwrap();
    let name = document
        .select(&name_selector)
        .next()
        .map(|el| el.text().collect::<String>().trim().to_string())
        .unwrap_or("Невідомо".to_string());

    let price_selector = Selector::parse("div.card-block__price-summ").unwrap();
    let price_text = document
        .select(&price_selector)
        .next()
        .map(|el| el.text().collect::<String>())
        .unwrap_or("0".to_string());

    let old_price_selector = Selector::parse("div.card-block__price-old").unwrap();
    let old_price_text = document
        .select(&old_price_selector)
        .next()
        .map(|el| el.text().collect::<String>());

    let discount_selector = Selector::parse("div.card-block__price-percent").unwrap();
    let discount = document
        .select(&discount_selector)
        .next()
        .map(|el| el.text().collect::<String>().trim().to_string());

    let price = clean_price(&price_text);
    let old_price = old_price_text.map(|t| clean_price(&t));

    ProductInfo { name, price, old_price, discount }
}

fn clean_price(text: &str) -> f64 {
    let clean: String = text
        .chars()
        .filter(|c| c.is_numeric())
        .collect();
    clean.parse().unwrap_or(0.0)
}
