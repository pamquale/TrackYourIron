use tokio_cron_scheduler::{JobScheduler, Job};

pub async fn start_scheduler() {
    let scheduler = JobScheduler::new()
        .await
        .expect("Не вдалось створити scheduler");

    let job = Job::new_async("0 */15 * * * *", |_, _| {
        Box::pin(async {
            println!("🕐 Запускаю перевірку цін...");
            check_prices().await;
        })
    })
        .expect("Не вдалось створити job");

    scheduler.add(job)
        .await
        .expect("Не вдалось додати job");

    scheduler.start()
        .await
        .expect("Не вдалось запустити scheduler");

    println!("✅ Scheduler запущено");
}

async fn check_prices() {
    println!("Перевіряю ціни...");
}
