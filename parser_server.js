const { chromium } = require('playwright');
const http = require('http');
const url = require('url');

const server = http.createServer(async (req, res) => {
    const query = url.parse(req.url, true).query;
    const productUrl = query.url;

    if (!productUrl) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: 'url parameter required' }));
        return;
    }

    if (!productUrl.includes('telemart.ua')) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: 'Тільки посилання з telemart.ua' }));
        return;
    }

    console.log(`🔍 Парсю: ${productUrl}`);

    try {
        const browser = await chromium.launch();
        const page = await browser.newPage();

        const response = await page.goto(productUrl);

        if (response.status() === 404) {
            await browser.close();
            res.writeHead(404);
            res.end(JSON.stringify({ error: 'Товар не знайдено' }));
            return;
        }

        await page.waitForTimeout(5000);

        const name = await page.$eval('h1.card-block__title', el => el.textContent.trim()).catch(() => null);
        const price_text = await page.$eval('div.card-block__price-summ', el => el.textContent.replace('₴', '').trim()).catch(() => null);
        const old_price_text = await page.$eval('div.card-block__price-old', el => el.textContent.replace('₴', '').trim()).catch(() => null);
        const discount = await page.$eval('div.card-block__price-percent', el => el.textContent.trim()).catch(() => null);

        await browser.close();

        if (!name || !price_text) {
            res.writeHead(500);
            res.end(JSON.stringify({ error: 'Не вдалось витягнути дані' }));
            return;
        }

        const price = parseFloat(price_text.replace(/\s/g, ''));
        const old_price = old_price_text ? parseFloat(old_price_text.replace(/\s/g, '')) : null;

        const result = { name, price, old_price, discount };
        console.log(`✅ Результат:`, result);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));

    } catch (err) {
        console.log(`❌ Помилка:`, err.message);
        res.writeHead(500);
        res.end(JSON.stringify({ error: err.message }));
    }
});

server.listen(3001, () => {
    console.log('🚀 Parser server запущено на http://localhost:3001');
    console.log('📖 Використання: http://localhost:3001/?url=https://telemart.ua/...');
});