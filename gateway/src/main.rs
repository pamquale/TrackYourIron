use axum::{
    extract::State,
    routing::{get, post},
    Router,
    Json,
};
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;
use tower_http::trace::TraceLayer;

// App state to hold the NATS client connection
#[derive(Clone)]
struct AppState {
    nats_client: async_nats::Client,
}

// Incoming Telegram data structures
#[derive(Debug, Deserialize)]
struct TelegramUpdate {
    message: Option<Message>,
}

#[derive(Debug, Deserialize)]
struct Message {
    chat: Chat,
    text: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Chat {
    id: i64,
}

// Outgoing event structure for NATS
#[derive(Debug, Serialize)]
struct UserCommandEvent {
    telegram_id: i64,
    command: String,
}

#[tokio::main]
async fn main() {
    // Initialize logger
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    tracing::info!("Connecting to NATS...");
    
    // Connect to NATS (change to your local NATS address later)
    let nats_client = async_nats::connect("demo.nats.io")
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
    let listener = TcpListener::bind("0.0.0.0:3000").await.unwrap();
    tracing::info!("Gateway server is running on http://0.0.0.0:3000");

    axum::serve(listener, app).await.unwrap();
}

// Webhook handler logic
async fn handle_telegram_webhook(
    State(state): State<AppState>,
    Json(update): Json<TelegramUpdate>,
) -> &'static str {
    
    // Check if the update contains a message and text
    if let Some(msg) = update.message {
        let user_id = msg.chat.id;
        
        if let Some(text) = msg.text {
            tracing::info!("Received command: '{}' from user ID: {}", text, user_id);
            
            // 1. Create event
            let event = UserCommandEvent {
                telegram_id: user_id,
                command: text,
            };

            // 2. Serialize event to JSON bytes
            let payload = serde_json::to_vec(&event).unwrap();

            // 3. Publish event to NATS topic
            match state.nats_client.publish("events.user_command", payload.into()).await {
                Ok(_) => tracing::info!("Event successfully published to NATS"),
                Err(e) => tracing::error!("Failed to publish to NATS: {}", e),
            }
        }
    }
    
    // Always return 200 OK to Telegram
    "OK"
}