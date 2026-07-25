package com.supplywatch.apitests;

import io.restassured.response.Response;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import java.util.List;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.equalTo;
import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/**
 * Contract tests for /materials endpoints against the live SupplyWatch service.
 */
public class MaterialsApiTest extends BaseApiTest {

    private String apiKey;

    @BeforeClass(alwaysRun = true)
    public void setUpApiKey() {
        apiKey = createFreshApiKey("Materials Test Co");
    }

    @Test
    public void materialsWithoutApiKeyReturns401() {
        given()
                .when()
                .get("/materials")
                .then()
                .statusCode(401)
                .body("detail", equalTo("X-API-Key is required"));
    }

    @Test
    public void materialsWithApiKeyReturnsAllEightSeededMaterials() {
        Response response = given()
                .header("X-API-Key", apiKey)
                .when()
                .get("/materials")
                .then()
                .statusCode(200)
                .extract()
                .response();

        List<String> names = response.path("data.name");
        assertEquals(names.size(), 8, "expected exactly 8 seeded materials");
        assertTrue(names.contains("Gallium"), "Gallium should be present in materials list");
        assertTrue(names.contains("Cobalt"), "Cobalt should be present in materials list");
    }

    @Test
    public void signalForFreshMaterialReturns404() {
        // Fresh DB, no scoring job has run (ENABLE_SCHEDULER=false) -- 404 is expected/correct.
        given()
                .header("X-API-Key", apiKey)
                .when()
                .get("/materials/1/signal")
                .then()
                .statusCode(404)
                .body("detail", equalTo("signal not found"));
    }

    @Test
    public void historyForFreshMaterialReturnsEmptyArray() {
        Response response = given()
                .header("X-API-Key", apiKey)
                .when()
                .get("/materials/1/history")
                .then()
                .statusCode(200)
                .extract()
                .response();

        List<Object> data = response.path("data");
        assertTrue(data.isEmpty(), "data should be an empty array on a fresh DB");
    }
}
