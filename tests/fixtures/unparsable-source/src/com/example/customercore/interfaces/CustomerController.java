package com.example.customercore.interfaces;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CustomerController {
    @GetMapping("/customers")
    public String getCustomers(String filter) {
        return null;
    }
}
