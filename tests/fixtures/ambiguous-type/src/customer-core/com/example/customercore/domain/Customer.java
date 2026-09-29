package com.example.customercore.domain;

import javax.persistence.Entity;
import javax.persistence.Id;

@Entity
public class Customer {
    @Id private CustomerId id;
    private String firstname;
}
