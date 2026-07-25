# SupplyWatch Selenium UI Tests

Selenium WebDriver + TestNG browser-automation suite that exercises the real
SupplyWatch landing page (`landing/index.html`), served live by the FastAPI
app in `landing/waitlist.py`, in an actual (headless) browser.

This is a genuine UI test suite, not a smoke script: it drives a real
browser against a real running instance of the page and asserts on the
page's real DOM, real CSS selectors, and real client-side JS behavior.

## What it covers

**`PageLoadTest`**
- The page loads and `<title>` matches the real title text.
- The nav bar is present, visible, and its `JOIN WAITLIST` CTA (`.nav-cta`)
  links to `#waitlist`; the other nav links (`#signals`, `#how`, `#pricing`)
  are present.
- The hero/waitlist section (`#waitlist`) is visible and contains the real
  form (`form.waitlist-form`), email input (`#email-input`), submit button
  (`.btn-primary`), and message div (`#waitlist-msg`).
- The stats row (`.stats .stat`) has exactly 4 entries with the real values
  (`12`, `3`, `6h`, `REST`) and labels (`Minerals Tracked`, `Data Sources`,
  `Update Frequency`, `API Protocol`).
- The `#signals` section is visible and contains the real 3 signal cards
  (Gallium, Cobalt, Lithium).

**`WaitlistFormTest`**
- The email input and submit button are present, visible, and interactable.
- Submitting an **empty** email is blocked by native HTML5 constraint
  validation (`required`) — `checkValidity()` is `false`, the browser never
  dispatches the `submit` event, `submitWaitlist()` never runs, and
  `#waitlist-msg` is provably unchanged (i.e. no network call fires).
- Submitting a **malformed** email (`not-an-email`) is blocked the same way
  by the `type="email"` constraint.
- With a well-formed email and `window.fetch` mocked (see below), clicking
  submit drives the real `submitWaitlist(event)` handler through its real
  state machine: `#waitlist-msg` shows `Joining…` synchronously, then (once
  the mocked fetch resolves) flips to the real success copy and the email
  input is cleared — exactly what the real JS does on a real success
  response.

All timing-dependent assertions use an explicit `WebDriverWait` polling a
real condition (never `Thread.sleep`).

## Why `window.fetch` is mocked — read this before assuming a gap

`submitWaitlist(event)` in `index.html` (around line 584) does **not** call
the local FastAPI `/waitlist/subscribe` route. It calls a real third-party
service directly:

```js
fetch('https://formspree.io/f/mvzjggpv', { ... })
```

This suite must never let that call actually complete — not in CI, not on
a developer's machine, not during iteration. So in the one test that drives
a real submit to a "success" outcome
(`validEmailWithMockedFetchShowsJoiningThenSuccessState`), a
`JavascriptExecutor` injects this stub **before** the submit button is
clicked:

```js
window.fetch = function() {
  return new Promise(function(resolve) {
    setTimeout(function() {
      resolve({ ok: true, json: function() { return Promise.resolve({ ok: true }); } });
    }, 400);
  });
};
```

The 400ms delay is deliberate: `submitWaitlist()` sets `#waitlist-msg` to
`Joining…` synchronously, then `await`s the fetch. An instantly-resolved
mock could flip straight to the success state before the test ever gets to
assert the intermediate `Joining…` state. Delaying the mock resolution
makes that real, transient UI state reliably observable via
`WebDriverWait` instead of racing it.

The two native-validation tests (empty / malformed email) never touch the
mock at all, because the browser's own HTML5 constraint validation blocks
the `submit` event before `submitWaitlist()` — and therefore `fetch` — is
ever reached. Those tests assert exactly that: `checkValidity()` is
`false` and `#waitlist-msg` never changes.

**Net result: no test in this suite ever makes a real network call to
`formspree.io`.**

## Browser

Microsoft Edge (Chromium), headless (`--headless=new`), driven via
Selenium 4's `EdgeDriver`/`EdgeOptions`. Edge was used because it's the
browser actually installed on this machine — no Chrome install was found.
Selenium Manager (bundled with Selenium 4.6+) resolves a matching
`msedgedriver` binary automatically; no manual driver download is needed.

## Prerequisites

The landing page must actually be running before you run the tests:

```bash
cd C:/Users/malha/supplywatch
python -m venv .venv-selenium
./.venv-selenium/Scripts/python.exe -m pip install fastapi "uvicorn[standard]"
./.venv-selenium/Scripts/python.exe -m uvicorn landing.waitlist:app --host 127.0.0.1 --port 8010
```

## Running the suite

```bash
export JAVA_HOME="C:/Program Files/Java/jdk-17"
cd C:/Users/malha/supplywatch/selenium-tests
"C:/Users/malha/career-ops/.tools/apache-maven-3.9.16/bin/mvn.cmd" test
```

By default tests target `http://127.0.0.1:8010/`. Override with:

```bash
mvn test -Dsw.baseUrl=http://127.0.0.1:PORT/
```

## Structure

```
selenium-tests/
  pom.xml                 Java 17, selenium-java 4.46.0, TestNG 7.10.2, Surefire 3.2.5
  testng.xml              Suite definition (PageLoadTest, WaitlistFormTest)
  README.md               This file
  src/test/java/com/supplywatch/selenium/
    BaseTest.java          Shared EdgeDriver (headless) setup/teardown
    PageLoadTest.java      Structural / content assertions on the real page
    WaitlistFormTest.java  Form interaction + validation + mocked-submit tests
```
