package com.example.customercore.application;

import java.util.List;
import java.util.Map;

public class DataLoader {
    private List<Map<String, String>> loadCustomers() {
        return reader.readerFor(Map.class).with(schema).readValues(file);
    }
}
