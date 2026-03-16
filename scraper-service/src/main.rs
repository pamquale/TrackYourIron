mod http_client;

use tokio_cron_scheduler::{JobScheduler, Job};

async fn check_prices() {
    println!("\n🕐 Запускаю перевірку цін...");

    // МОК
    let products = vec![
        (1, "https://telemart.ua/ua/products/asus-27-tuf-gaming-vg27aqml5a-90lm0bg0-b02971-black/"),
        (2, "https://telemart.ua/ua/products/hexo-gaming-mainstream-pro-hgmp-7700n5070-32s1twh-white/"),
        (3, "https://telemart.ua/ua/products/dragon-lucky-platinum-powered-by-msi-rtx-5080-r7-7700-black/"),
    ];

    println!("📦 Знайдено {} товарів для перевірки", products.len());
    println!("─────────────────────────────");

    for (id, link) in &products {
        println!("🔍 Перевіряю товар #{}: {}", id, link);

        match http_client::fetch_product(link).await {
            Ok(product) => {
                println!("✅ Назва: {}", product.name);
                println!("💰 Поточна ціна: {} грн", product.price);

                if let Some(old_price) = product.old_price {
                    println!("💰 Оригінальна ціна: {} грн", old_price);

                    if product.price < old_price {
                        println!("🟢 ЦІНА ЗНИЗИЛАСЬ! {} → {}", old_price, product.price);
                        println!(" МОК NATS → PriceDroppedEvent {{");
                        println!("     product_id: {},", id);
                        println!("     new_price: {},", product.price);
                        println!("     old_price: {},", old_price);
                        println!("     store_link: \"{}\"", link);
                        println!("   }}");
                    } else if product.price > old_price {
                        println!("🔴 ЦІНА ЗРОСЛА! {} → {}", old_price, product.price);
                    } else {
                        println!("⚪ Ціна не змінилась: {} грн", product.price);
                    }
                } else {
                    println!("💰 Знижки немає — ціна: {} грн", product.price);
                }
            }
            Err(e) => {
                println!("❌ Помилка: {}", e);
            }
        }
        println!("─────────────────────────────");
    }

    println!("✅ Перевірка завершена");
}

#[tokio::main]
async fn main() {
    println!("🚀 Scraper Service запущено");
    
    check_prices().await;
    
    let scheduler = JobScheduler::new().await.unwrap();

    let job = Job::new_async("0 */15 * * * *", |_, _| {
        Box::pin(async {
            check_prices().await;
        })
    }).unwrap();

    scheduler.add(job).await.unwrap();
    scheduler.start().await.unwrap();

    println!("⏰ Scheduler запущено — перевірка кожні 15 хвилин");

    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
    }
}
