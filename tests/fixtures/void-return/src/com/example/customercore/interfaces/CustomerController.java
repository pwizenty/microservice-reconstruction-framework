package com.example.customercore.interfaces;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CustomerController {
    @DeleteMapping("/customers/{id}")
    public ResponseEntity<Void> deleteCustomer(String id) {
        return null;
    }

    @PostMapping("/customers")
    public void createCustomer(String name) {
    }

    @GetMapping("/customers")
    public String getCustomers(String filter) {
        return null;
    }
}
