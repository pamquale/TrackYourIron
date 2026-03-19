use axum::{
    extract::State,
    routing::{get, post},
    Router,
    Json,
};
use serde_json::Value;
use std::env;
use tokio::net::TcpListener;
use tower_http::trace::TraceLayer;

// App state to hold the NATS client connection
#[derive(Clone)]
struct AppState {
    nats_client: async_nats::Client,
}

#[tokio::main]
async fn main() {
    // Initialize logger
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    let nats_url = env::var("NATS_URL").unwrap_or_else(|_| "nats://127.0.0.1:4222".to_string());
    let port = env::var("PORT").unwrap_or_else(|_| "8000".to_string());
    let bind_addr = format!("0.0.0.0:{}", port);

    tracing::info!("Connecting to NATS at {}...", nats_url);

    // Connect to NATS
    let nats_client = async_nats::connect(&nats_url)
        .await
        .expect("Failed to connect to NATS");

    tracing::info!("Successfully connected to NATS broker");

    let state = AppState { nats_client };

    // Setup router and endpoints
    let app = Router::new()
        .route("/ping", get(|| async { "Gateway is alive!" }))
        .route("/webhook", post(handle_telegram_webhook))
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    // Start the server
    tracing::info!("Gateway server is running on http://{}", bind_addr);
    let listener = TcpListener::bind(&bind_addr).await.unwrap();

    axum::serve(listener, app).await.unwrap();
}

// Webhook handler logic
async fn handle_telegram_webhook(
    State(state): State<AppState>,
    Json(update): Json<Value>,
) -> &'static str {
    tracing::info!("Received webhook update");
    
    // Forward the entire raw update to NATS for the bot
    let payload = serde_json::to_vec(&update).unwrap();
    match state.nats_client.publish("events.telegram_update", payload.into()).await {
        Ok(_) => tracing::info!("Update successfully published to NATS"),
        Err(e) => tracing::error!("Failed to publish to NATS: {}", e),
    }

    // Always return 200 OK to Telegram
    "OK"
}
