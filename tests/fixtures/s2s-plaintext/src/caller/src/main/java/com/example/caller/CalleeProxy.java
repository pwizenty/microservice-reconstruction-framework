package com.example.caller;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class CalleeProxy {
    private RestTemplate restTemplate = new RestTemplate();

    public String greet() {
        return restTemplate.getForObject("http://callee:8081/greeting", String.class);
    }
}
