package com.example.service;

import org.springframework.web.client.RestTemplate;

/** Test code is excluded, so this plaintext URL creates no call. */
public class ExternalProxyTest {
    private RestTemplate restTemplate = new RestTemplate();

    public String stub() {
        return restTemplate.getForObject("http://localhost:9999/stub", String.class);
    }
}
