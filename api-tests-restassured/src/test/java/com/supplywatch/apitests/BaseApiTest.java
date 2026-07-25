package com.supplywatch.apitests;

import io.restassured.RestAssured;
import org.testng.annotations.BeforeSuite;

/**
 * Shared base class for all SupplyWatch API test classes.
 *
 * <p>Points RestAssured at a live, locally running instance of the SupplyWatch
 * FastAPI service (see api-tests-restassured/README.md for how to start it).
 * No mocking, no stubbed server -- every test in this suite talks to a real
 * process backed by a real Postgres database.</p>
 */
public class BaseApiTest {

    protected static final String BASE_URI = "http://127.0.0.1:8001";

    @BeforeSuite(alwaysRun = true)
    public void configureRestAssured() {
        RestAssured.baseURI = BASE_URI;
    }

    /**
     * Creates a fresh API key against the live service and returns the raw key value.
     * Shared helper so every test class that needs an authenticated call can
     * obtain its own key rather than depending on test execution order.
     */
    protected static String createFreshApiKey(String companyName) {
        return io.restassured.RestAssured.given()
                .contentType("application/json")
                .body("{\"company_name\": \"" + companyName + "\"}")
                .when()
                .post("/auth/keys")
                .then()
                .statusCode(200)
                .extract()
                .path("data.api_key");
    }
}
