package com.example.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/** The schema URL is an identifier, not an address, and must not become a call. */
@Component
public class ExternalProxy {
    private static final String SCHEMA = "http://www.w3.org/2001/XMLSchema";

    @Value("${exchange.rates.url}")
    private String exchangeRatesUrl;

    @Value("${missing.service.url}")
    private String missingServiceUrl;

    private RestTemplate restTemplate = new RestTemplate();

    public String rates() {
        return restTemplate.getForObject(exchangeRatesUrl, String.class);
    }
}
