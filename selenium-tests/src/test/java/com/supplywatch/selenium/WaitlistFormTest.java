package com.supplywatch.selenium;

import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.time.Duration;

/**
 * Exercises the real waitlist form and its submitWaitlist(event) handler
 * (landing/index.html, around line 584).
 *
 * IMPORTANT — network safety: submitWaitlist() calls
 *     fetch('https://formspree.io/f/mvzjggpv', { ... })
 * directly against a real third-party service. Any test that actually
 * triggers a successful submit path installs a JavaScript stub that
 * replaces window.fetch BEFORE clicking submit, so that call is
 * intercepted locally and NEVER reaches formspree.io. See MOCK_FETCH_JS
 * below and its usage in validEmailWithMockedFetchShowsJoiningThenSuccessState().
 *
 * The two native-HTML5-validation tests below never need the mock at all:
 * an empty or malformed email is rejected by the browser's built-in form
 * validation before the 'submit' event (and therefore submitWaitlist())
 * ever fires, so no network call is even attempted in those cases.
 */
public class WaitlistFormTest extends BaseTest {

    // Resolution is deliberately delayed (setTimeout) rather than immediate so the
    // transient "Joining…" UI state set synchronously by submitWaitlist() is reliably
    // observable via WebDriverWait before the mocked call "resolves".
    private static final String MOCK_FETCH_JS =
            "window.fetch = function() {" +
            "  return new Promise(function(resolve) {" +
            "    setTimeout(function() {" +
            "      resolve({ ok: true, json: function() { return Promise.resolve({ ok: true }); } });" +
            "    }, 400);" +
            "  });" +
            "};";

    @BeforeMethod(alwaysRun = true)
    public void loadFreshPage() {
        driver.get(BASE_URL);
        new WebDriverWait(driver, Duration.ofSeconds(10))
                .until(ExpectedConditions.visibilityOfElementLocated(By.id("email-input")));
    }

    @Test
    public void emailInputAndSubmitButtonArePresentAndInteractable() {
        WebElement emailInput = driver.findElement(By.id("email-input"));
        WebElement submitBtn = driver.findElement(By.cssSelector(".waitlist-form .btn-primary"));

        Assert.assertTrue(emailInput.isDisplayed());
        Assert.assertTrue(emailInput.isEnabled());
        Assert.assertTrue(submitBtn.isDisplayed());
        Assert.assertTrue(submitBtn.isEnabled());
        Assert.assertEquals(emailInput.getAttribute("type"), "email");
        Assert.assertEquals(submitBtn.getAttribute("type"), "submit");
    }

    @Test
    public void emptyEmailIsBlockedByNativeHtml5ValidationAndFiresNoSubmit() {
        WebElement emailInput = driver.findElement(By.id("email-input"));
        WebElement submitBtn = driver.findElement(By.cssSelector(".waitlist-form .btn-primary"));
        WebElement msg = driver.findElement(By.id("waitlist-msg"));

        Assert.assertEquals(emailInput.getAttribute("value"), "");
        String msgTextBefore = msg.getText();

        submitBtn.click();

        JavascriptExecutor js = (JavascriptExecutor) driver;
        boolean valid = (boolean) js.executeScript(
                "return document.getElementById('email-input').checkValidity();");
        Assert.assertFalse(valid, "Empty required email input must be reported invalid by native HTML5 validation");

        Assert.assertEquals(msg.getText(), msgTextBefore,
                "#waitlist-msg must stay unchanged: native validation blocks the submit event, "
                        + "so submitWaitlist() never runs and no network call fires");
    }

    @Test
    public void malformedEmailIsBlockedByNativeHtml5Validation() {
        WebElement emailInput = driver.findElement(By.id("email-input"));
        WebElement submitBtn = driver.findElement(By.cssSelector(".waitlist-form .btn-primary"));
        WebElement msg = driver.findElement(By.id("waitlist-msg"));

        emailInput.sendKeys("not-an-email");
        String msgTextBefore = msg.getText();

        submitBtn.click();

        JavascriptExecutor js = (JavascriptExecutor) driver;
        boolean valid = (boolean) js.executeScript(
                "return document.getElementById('email-input').checkValidity();");
        Assert.assertFalse(valid, "Malformed email must fail the input's type=email constraint validation");

        Assert.assertEquals(msg.getText(), msgTextBefore,
                "#waitlist-msg must stay unchanged when native validation blocks submission");
    }

    @Test
    public void validEmailWithMockedFetchShowsJoiningThenSuccessState() {
        JavascriptExecutor js = (JavascriptExecutor) driver;

        // Install the fetch stub BEFORE any submit — this is what prevents the real
        // network call to https://formspree.io/f/mvzjggpv from ever happening.
        js.executeScript(MOCK_FETCH_JS);

        WebElement emailInput = driver.findElement(By.id("email-input"));
        WebElement submitBtn = driver.findElement(By.cssSelector(".waitlist-form .btn-primary"));
        WebElement msg = driver.findElement(By.id("waitlist-msg"));

        emailInput.sendKeys("candidate@example.com");

        boolean validBeforeSubmit = (boolean) js.executeScript(
                "return document.getElementById('email-input').checkValidity();");
        Assert.assertTrue(validBeforeSubmit, "A well-formed email should pass native HTML5 validation");

        submitBtn.click();

        // submitWaitlist() sets msg.textContent = 'Joining…' synchronously, before awaiting fetch().
        new WebDriverWait(driver, Duration.ofSeconds(5))
                .until(d -> "Joining…".equals(msg.getText()));
        Assert.assertEquals(msg.getText(), "Joining…",
                "submitWaitlist() must show the real 'Joining…' state immediately on submit");

        // Once the mocked fetch resolves (~400ms later), the real success branch runs.
        new WebDriverWait(driver, Duration.ofSeconds(5))
                .until(d -> {
                    String cls = msg.getAttribute("class");
                    return cls != null && cls.contains("success");
                });
        Assert.assertTrue(msg.getText().startsWith("✓"),
                "On a mocked-successful response, #waitlist-msg should show the real success copy");
        Assert.assertEquals(emailInput.getAttribute("value"), "",
                "submitWaitlist() clears the email input after a successful submission");
    }
}
