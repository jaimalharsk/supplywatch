package com.supplywatch.apitests;

import io.restassured.response.Response;
import org.testng.annotations.Test;

import static io.restassured.RestAssured.given;
import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNotNull;
import static org.testng.Assert.assertTrue;

/**
 * Contract tests for GET /health against the live SupplyWatch service.
 */
public class HealthApiTest extends BaseApiTest {

    @Test
    public void healthReturns200WithOkStatusAndVersion() {
        Response response = given()
                .when()
                .get("/health")
                .then()
                .statusCode(200)
                .extract()
                .response();

        assertEquals(response.path("data.status"), "ok", "data.status should be 'ok'");

        String version = response.path("meta.version");
        assertNotNull(version, "meta.version should be present");
        assertTrue(!version.isEmpty(), "meta.version should be non-empty");
    }
}
