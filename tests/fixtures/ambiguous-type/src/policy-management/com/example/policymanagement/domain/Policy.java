package com.example.policymanagement.domain;

import javax.persistence.Entity;
import javax.persistence.Id;

@Entity
public class Policy {
    @Id private CustomerId id;
    private String policyType;
}
