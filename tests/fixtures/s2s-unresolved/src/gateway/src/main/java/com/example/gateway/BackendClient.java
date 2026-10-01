package com.example.gateway;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;

@FeignClient(name = "backend", url = "${backend.baseURL}")
public interface BackendClient {
    @GetMapping(value = "/items")
    String getItems();
}
