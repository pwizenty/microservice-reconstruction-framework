package com.example.subscriber;

import org.springframework.jms.annotation.JmsListener;
import org.springframework.messaging.Message;

// A listener in test code. It must not become a fact.
public class ConsumerTests {
    @JmsListener(destination = "${orders.queueName}")
    public void receivesInATest(final Message<String> message) {
    }
}
