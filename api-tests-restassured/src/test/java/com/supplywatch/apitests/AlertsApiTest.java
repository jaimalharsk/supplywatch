package com.supplywatch.apitests;

import io.restassured.response.Response;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import java.util.List;

import static io.restassured.RestAssured.given;
import static org.testng.Assert.assertNotNull;

/**
 * Contract tests for /alerts endpoints against the live SupplyWatch service.
 */
public class AlertsApiTest extends BaseApiTest {

    private String apiKey;

    @BeforeClass(alwaysRun = true)
    public void setUpApiKey() {
        apiKey = createFreshApiKey("Alerts Test Co");
    }

    @Test
    public void subscribeToAlertReturnsCreatedRecordWithId() {
        Response response = given()
                .header("X-API-Key", apiKey)
                .contentType("application/json")
                .body("{\"material_id\": 1, \"threshold\": 65, \"email\": \"ops@acme.com\"}")
                .when()
                .post("/alerts/subscribe")
                .then()
                .statusCode(200)
                .extract()
                .response();

        Integer id = response.path("data.id");
        assertNotNull(id, "data.id should be present and non-null after subscribing");
    }

    @Test
    public void alertsHistoryReturnsAnArray() {
        // No scoring/alert-evaluation job has run, so an empty array here is
        // expected and correct -- we only assert the shape, not that it's non-empty.
        Response response = given()
                .header("X-API-Key", apiKey)
                .when()
                .get("/alerts/history")
                .then()
                .statusCode(200)
                .extract()
                .response();

        List<Object> data = response.path("data");
        assertNotNull(data, "data should be an array (possibly empty)");
    }
}
