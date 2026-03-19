use axum::{
    extract::{State, Json},
    http::StatusCode,
    response::IntoResponse,
    routing::post,
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;

use crate::db;
use crate::http_client;

#[derive(Clone)]
pub struct AppState {
    pub pool: PgPool,
}

#[derive(Deserialize)]
pub struct AddProductRequest {
    pub url: String,
}

#[derive(Serialize)]
pub struct AddProductResponse {
    pub id: i32,
    pub current_price: f64,
    pub name: String,
}

pub fn create_router(pool: PgPool) -> Router {
    let state = AppState { pool };
    Router::new()
        .route("/api/products/add", post(add_product))
        .with_state(state)
}

async fn add_product(
    State(state): State<AppState>,
    Json(payload): Json<AddProductRequest>,
) -> impl IntoResponse {
    println!("Received add product request for: {}", payload.url);

    // Fetch product info from Parser Service
    let product_data = match http_client::fetch_product(&payload.url).await {
        Ok(data) => data,
        Err(e) => {
            eprintln!("Failed to fetch product: {}", e);
            return (StatusCode::BAD_REQUEST, format!("Scraper error: {}", e)).into_response();
        }
    };

    // Add to Database (or fetch existing)
    match db::add_product(
        &state.pool,
        &product_data.name,
        &payload.url,
        product_data.price
    ).await {
        Ok(id) => {
            println!("Successfully processed product id: {}", id);
            let response = AddProductResponse {
                id,
                current_price: product_data.price,
                name: product_data.name.clone(),
            };
            (StatusCode::OK, Json(response)).into_response()
        }
        Err(e) => {
            eprintln!("Database error: {}", e);
            (StatusCode::INTERNAL_SERVER_ERROR, format!("Database error: {}", e)).into_response()
        }
    }
}
