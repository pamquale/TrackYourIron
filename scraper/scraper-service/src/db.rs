use sqlx::PgPool;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct Product {
    pub id: i32,
    pub name: String,
    pub link: String,
    pub price: f64,
}

pub async fn get_all_products(pool: &PgPool) -> Result<Vec<Product>, sqlx::Error> {
    sqlx::query_as::<_, Product>(
        "SELECT id, name, link, price FROM products"
    )
    .fetch_all(pool)
    .await
}

pub async fn add_product(
    pool: &PgPool,
    name: &str,
    link: &str,
    price: f64
) -> Result<i32, sqlx::Error> {
    // Check if product already exists
    let existing: Option<(i32,)> = sqlx::query_as(
        "SELECT id FROM products WHERE link = $1"
    )
    .bind(link)
    .fetch_optional(pool)
    .await?;

    if let Some((id,)) = existing {
        // Update price
        sqlx::query(
            "UPDATE products SET price = $1, name = $2 WHERE id = $3"
        )
        .bind(price)
        .bind(name)
        .bind(id)
        .execute(pool)
        .await?;
        return Ok(id);
    }

    let rec: (i32,) = sqlx::query_as(
        "INSERT INTO products (name, link, price) VALUES ($1, $2, $3) RETURNING id"
    )
    .bind(name)
    .bind(link)
    .bind(price)
    .fetch_one(pool)
    .await?;
    
    Ok(rec.0)
}

pub async fn update_price(
    pool: &PgPool,
    product_id: i32,
    new_price: f64
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "UPDATE products SET price = $1 WHERE id = $2"
    )
    .bind(new_price)
    .bind(product_id)
    .execute(pool)
    .await?;
    
    Ok(())
}
