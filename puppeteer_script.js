const puppeteer = require('puppeteer');
const UserAgent = require('user-agents');


const args = process.argv.slice(2);
if (args.length == 0) {
    // 没有传入参数，返回错误信息
    console.error('Error: No arguments provided.');
    process.exit(1);
}
const search_query = args.join('+');

// const search_query = "bluetooth headset china booking";

(async () => {
    let results = [];
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--lang=en-US', '--disable-extensions'],
    }); // headless设置为false，以便看到浏览器操作

    const page = await browser.newPage();
    const userAgent = new UserAgent({ deviceCategory: 'desktop' });
    // await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36');

    await page.goto('https://www.bing.com');

    // 输入查询条件
    await page.type('#sb_form_q', search_query);

    // 点击搜索按钮或按回车键
    await page.keyboard.press('Enter');

    // 等待结果加载完成
    await page.waitForSelector('div.b_tpcn', { timeout: 5000 });
    // 获取所有搜索结果链接
    const hrefs = await page.evaluate(() => {
        const divs = document.querySelectorAll('div.b_tpcn a.tilk');
        const hrefs = Array.from(divs, a => a.href);
        return hrefs;
    });


    results = hrefs
    console.log(JSON.stringify(results));
    // 关闭浏览器
    await browser.close();
})();
