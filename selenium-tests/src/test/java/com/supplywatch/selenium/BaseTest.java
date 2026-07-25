package com.supplywatch.selenium;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.edge.EdgeDriver;
import org.openqa.selenium.edge.EdgeOptions;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;

/**
 * Shared WebDriver lifecycle for all Selenium tests in this suite.
 *
 * Browser: Microsoft Edge (Chromium), run headless via "--headless=new".
 * Edge was chosen because it is the browser actually present on this machine
 * (no Google Chrome install was found). Selenium Manager (bundled with
 * Selenium 4.6+) resolves a matching msedgedriver automatically — no manual
 * driver download is required.
 *
 * Target URL: a real, live instance of the SupplyWatch landing page served
 * by landing/waitlist.py (FastAPI + StaticFiles), started separately via
 * uvicorn on 127.0.0.1:8010. Override with -Dsw.baseUrl=... if needed.
 */
public abstract class BaseTest {

    protected static final String BASE_URL = System.getProperty("sw.baseUrl", "http://127.0.0.1:8010/");

    protected WebDriver driver;

    @BeforeClass(alwaysRun = true)
    public void setUpDriver() {
        EdgeOptions options = new EdgeOptions();
        options.addArguments("--headless=new");
        options.addArguments("--disable-gpu");
        options.addArguments("--window-size=1440,1000");
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        driver = new EdgeDriver(options);
    }

    @AfterClass(alwaysRun = true)
    public void tearDownDriver() {
        if (driver != null) {
            driver.quit();
        }
    }
}
