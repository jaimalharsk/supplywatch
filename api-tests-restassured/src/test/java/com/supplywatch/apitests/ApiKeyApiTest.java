package com.supplywatch.apitests;

import io.restassured.response.Response;
import org.testng.annotations.Test;

import static io.restassured.RestAssured.given;
import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/**
 * Contract tests for POST /auth/keys against the live SupplyWatch service.
 */
public class ApiKeyApiTest extends BaseApiTest {

    @Test
    public void createKeyWithoutTierDefaultsToFree() {
        Response response = given()
                .contentType("application/json")
                .body("{\"company_name\": \"Acme Corp\"}")
                .when()
                .post("/auth/keys")
                .then()
                .statusCode(200)
                .extract()
                .response();

        String apiKey = response.path("data.api_key");
        assertTrue(apiKey.startsWith("sw_"), "api_key should start with 'sw_' but was: " + apiKey);
        assertEquals(response.path("data.tier").toString(), "free", "tier should default to 'free'");
    }

    @Test
    public void createKeyWithExplicitFreeTierPassesThrough() {
        Response response = given()
                .contentType("application/json")
                .body("{\"company_name\": \"Acme Corp\", \"tier\": \"free\"}")
                .when()
                .post("/auth/keys")
                .then()
                .statusCode(200)
                .extract()
                .response();

        String apiKey = response.path("data.api_key");
        assertTrue(apiKey.startsWith("sw_"), "api_key should start with 'sw_' but was: " + apiKey);
        assertEquals(response.path("data.tier").toString(), "free", "tier should echo back 'free'");
    }
}
