package com.example.hub;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class Clients {
    @Value("${alpha.baseURL}")
    private String alphaBaseUrl;

    @Value("${beta.baseURL}")
    private String betaBaseUrl;

    private RestTemplate restTemplate = new RestTemplate();
}
