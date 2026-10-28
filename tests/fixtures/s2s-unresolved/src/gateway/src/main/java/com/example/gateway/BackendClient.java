package com.example.gateway;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;

/**
 * The base path of the client and the path of a method are joined the way Spring
 * reads them, so the endpoints addressed here are /api/items and
 * /api/items/{id}.
 */
@FeignClient(name = "backend", url = "${backend.baseURL}")
@RequestMapping("/api")
public interface BackendClient {
    @GetMapping(value = "/items")
    String getItems();

    @GetMapping(value = "/items/{id}")
    String getItem(@PathVariable String id);
}
