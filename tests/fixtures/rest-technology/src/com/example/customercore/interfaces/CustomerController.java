package com.example.customercore.interfaces;

import io.swagger.v3.oas.annotations.Operation;
import javax.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.example.customercore.domain.Customer;

@RestController
@RequestMapping("/customers")
public class CustomerController {
    /**
     * A mapping without a path: the operation is addressed by the endpoint of
     * the interface alone. The OpenAPI annotation is no aspect of the
     * technology model and must not be carried over.
     */
    @Operation(summary = "Get all customers")
    @GetMapping
    public String getCustomers(
            @RequestParam(value = "filter", required = false, defaultValue = "") String filter) {
        return null;
    }

    /** A mapping with a path in its "value" element, and a path variable. */
    @GetMapping(value = "/{customerId}")
    public Customer getCustomer(@PathVariable String customerId) {
        return null;
    }

    /** Two aspects on one parameter, and a mapping without a path. */
    @PostMapping
    public Customer createCustomer(@Valid @RequestBody Customer customer) {
        return null;
    }

    /** An aspect of the operation that carries a value of its own. */
    @PreAuthorize("isAuthenticated()")
    @PatchMapping(value = "/{customerId}")
    public Customer updateCustomer(@PathVariable String customerId,
            @RequestBody Customer customer) {
        return null;
    }

    /** A mapping with a path in its "path" element rather than in "value". */
    @DeleteMapping(path = "/{customerId}")
    public void deleteCustomer(@PathVariable String customerId) {
    }
}
