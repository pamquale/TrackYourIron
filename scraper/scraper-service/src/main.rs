mod api;
mod db;
mod http_client;
mod publisher;

use std::env;
use std::net::SocketAddr;
use tokio_cron_scheduler::{Job, JobScheduler};
use sqlx::postgres::PgPoolOptions;
use async_nats::Client;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 Scraper Service started");

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL not set");
    let nats_url = env::var("NATS_URL").expect("NATS_URL not set");

    // Init DB
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
        .expect("Failed to connect to Postgres");
    println!("✅ DB Connected");

    // Init NATS
    let nats_client = async_nats::connect(&nats_url).await.expect("Failed to connect to NATS");
    println!("✅ NATS Connected");

    // Start Scheduler
    let sched_pool = pool.clone();
    let sched_nats = nats_client.clone();
    let scheduler = JobScheduler::new().await?;

    let job = Job::new_async("0 */15 * * * *", move |_uuid, _l| {
        let pool = sched_pool.clone();
        let nats = sched_nats.clone();
        Box::pin(async move {
            println!("⏰ Running scheduled price check...");
            if let Err(e) = check_prices(&pool, &nats).await {
                eprintln!("❌ Error checking prices: {}", e);
            }
        })
    })?;

    scheduler.add(job).await?;
    scheduler.start().await?;
    println!("⏰ Scheduler started (every 15 min)");

    // Initial check
    let init_pool = pool.clone();
    let init_nats = nats_client.clone();
    tokio::spawn(async move {
        println!("🚀 Running initial price check...");
        if let Err(e) = check_prices(&init_pool, &init_nats).await {
            eprintln!("❌ Error in initial check: {}", e);
        }
    });

    // Start Axum Server
    let app = api::create_router(pool);
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    println!("🌍 Scraper API listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

async fn check_prices(pool: &sqlx::PgPool, nats_client: &Client) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let products = db::get_all_products(pool).await?;
    println!("📦 Found {} products to check", products.len());
    
    for product in products {
        println!("🔍 Checking product #{}: {}", product.id, product.link);
        match http_client::fetch_product(&product.link).await {
            Ok(parsed) => {
                println!("✅ Parsed: {} - {} UAH", parsed.name, parsed.price);
                
                let old_price = product.price;
                if parsed.price != old_price {
                    println!("💰 Price changed for {}: {} -> {}", product.id, old_price, parsed.price);
                    
                    // Update DB
                    if let Err(e) = db::update_price(pool, product.id, parsed.price).await {
                        eprintln!("❌ Failed to update price in DB: {}", e);
                        continue;
                    }

                    // Publish Event if price dropped
                    if parsed.price < old_price {
                        println!("📉 Price Dropped! Publishing event...");
                        let event = publisher::PriceDroppedEvent {
                            product_id: product.id,
                            new_price: parsed.price,
                            store_link: product.link.clone(),
                        };
                        publisher::publish_price_dropped(nats_client, event).await;
                    }
                } else {
                    println!("⚪ Price didn't change");
                }
            },
            Err(e) => eprintln!("❌ Failed to fetch {}: {}", product.link, e),
        }
    }
    
    Ok(())
}
