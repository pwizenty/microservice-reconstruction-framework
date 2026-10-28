package com.example.customercore.application;

import java.util.List;
import java.util.Map;

public class DataLoader {
    private List<Map<String, String>> loadCustomers() {
        return registry.module(schema).readAll();
    }
}
