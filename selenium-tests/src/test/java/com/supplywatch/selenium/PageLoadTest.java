package com.supplywatch.selenium;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.time.Duration;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Verifies the real SupplyWatch landing page (landing/index.html, served live by
 * landing/waitlist.py) loads correctly and its key structural sections are present
 * and visible: title, nav bar, hero/waitlist section, stats row, and live signals
 * section. All selectors below were verified directly against landing/index.html
 * before writing these assertions.
 */
public class PageLoadTest extends BaseTest {

    private static final String EXPECTED_TITLE = "SupplyWatch — Critical Mineral Supply Intelligence";

    @BeforeMethod(alwaysRun = true)
    public void loadPage() {
        driver.get(BASE_URL);
    }

    @Test
    public void pageLoadsWithCorrectTitle() {
        new WebDriverWait(driver, Duration.ofSeconds(10)).until(ExpectedConditions.titleIs(EXPECTED_TITLE));
        Assert.assertEquals(driver.getTitle(), EXPECTED_TITLE);
    }

    @Test
    public void navBarWithJoinWaitlistCtaIsVisible() {
        WebElement navCta = new WebDriverWait(driver, Duration.ofSeconds(10))
                .until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector("nav .nav-cta")));

        Assert.assertTrue(navCta.isDisplayed(), "nav-cta link should be visible");
        Assert.assertEquals(navCta.getText().trim(), "JOIN WAITLIST");
        Assert.assertTrue(navCta.getAttribute("href").endsWith("#waitlist"),
                "nav-cta should link to the #waitlist hero section");

        // Rest of the nav links (real anchors from index.html)
        List<WebElement> navLinks = driver.findElements(By.cssSelector("nav .nav-links a"));
        List<String> hrefs = navLinks.stream()
                .map(a -> a.getAttribute("href"))
                .collect(Collectors.toList());
        Assert.assertTrue(hrefs.stream().anyMatch(h -> h.endsWith("#signals")));
        Assert.assertTrue(hrefs.stream().anyMatch(h -> h.endsWith("#how")));
        Assert.assertTrue(hrefs.stream().anyMatch(h -> h.endsWith("#pricing")));
    }

    @Test
    public void heroWaitlistSectionIsVisibleWithForm() {
        WebElement waitlistSection = new WebDriverWait(driver, Duration.ofSeconds(10))
                .until(ExpectedConditions.visibilityOfElementLocated(By.id("waitlist")));
        Assert.assertTrue(waitlistSection.isDisplayed());

        WebElement form = waitlistSection.findElement(By.cssSelector("form.waitlist-form"));
        Assert.assertTrue(form.isDisplayed());
        Assert.assertEquals(form.getAttribute("onsubmit"), "submitWaitlist(event)");

        WebElement emailInput = waitlistSection.findElement(By.id("email-input"));
        Assert.assertTrue(emailInput.isDisplayed());
        Assert.assertEquals(emailInput.getAttribute("type"), "email");

        WebElement submitBtn = waitlistSection.findElement(By.cssSelector(".btn-primary"));
        Assert.assertTrue(submitBtn.isDisplayed());
        Assert.assertEquals(submitBtn.getText().trim(), "GET WEEKLY BRIEF");

        WebElement msg = waitlistSection.findElement(By.id("waitlist-msg"));
        Assert.assertNotNull(msg);
    }

    @Test
    public void statsRowShowsFourRealStats() {
        List<WebElement> stats = new WebDriverWait(driver, Duration.ofSeconds(10))
                .until(ExpectedConditions.numberOfElementsToBe(By.cssSelector(".stats .stat"), 4));

        List<String> values = stats.stream()
                .map(s -> s.findElement(By.cssSelector(".stat-value")).getText().trim())
                .collect(Collectors.toList());
        List<String> labels = stats.stream()
                .map(s -> s.findElement(By.cssSelector(".stat-label")).getText().trim())
                .collect(Collectors.toList());

        Assert.assertEquals(values, List.of("12", "3", "6h", "REST"));
        // .stat-label has `text-transform: uppercase` in index.html's CSS, so Selenium's
        // getText() (which returns rendered/visible text, not raw DOM textContent) reports
        // these in upper case even though the HTML source has mixed case. Asserting the
        // real rendered text here, not the raw markup.
        Assert.assertEquals(labels, List.of(
                "MINERALS TRACKED", "DATA SOURCES", "UPDATE FREQUENCY", "API PROTOCOL"));

        for (WebElement stat : stats) {
            Assert.assertTrue(stat.isDisplayed());
        }
    }

    @Test
    public void signalsSectionShowsRiskSignalCards() {
        WebElement signalsSection = new WebDriverWait(driver, Duration.ofSeconds(10))
                .until(ExpectedConditions.visibilityOfElementLocated(By.id("signals")));
        Assert.assertTrue(signalsSection.isDisplayed());

        List<WebElement> cards = signalsSection.findElements(By.cssSelector(".signal-card"));
        Assert.assertEquals(cards.size(), 3, "index.html defines exactly 3 signal-card entries");

        List<String> names = cards.stream()
                .map(c -> c.findElement(By.cssSelector(".signal-name")).getText().trim())
                .collect(Collectors.toList());
        Assert.assertTrue(names.contains("Gallium (Ga)"));
        Assert.assertTrue(names.contains("Cobalt (Co)"));
        Assert.assertTrue(names.contains("Lithium (Li)"));

        for (WebElement card : cards) {
            Assert.assertTrue(card.isDisplayed());
            WebElement score = card.findElement(By.cssSelector(".signal-score"));
            Assert.assertTrue(score.isDisplayed());
        }
    }
}
