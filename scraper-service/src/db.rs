use sqlx::PgPool;

pub struct Product {
    pub id: i32,
    pub name: String,
    pub link: String,
    pub price: f64,
}

pub async fn get_all_products(pool: &PgPool) -> Vec<Product> {
    sqlx::query_as!(
        Product,
        "SELECT id, name, link, price FROM products"
    )
        .fetch_all(pool)
        .await
        .expect("Не вдалось отримати товари")
}

pub async fn update_price(
    pool: &PgPool,
    product_id: i32,
    new_price: f64
) {
    sqlx::query!(
        "UPDATE products SET price = $1 WHERE id = $2",
        new_price,
        product_id
    )
        .execute(pool)
        .await
        .expect("Не вдалось оновити ціну");
}
