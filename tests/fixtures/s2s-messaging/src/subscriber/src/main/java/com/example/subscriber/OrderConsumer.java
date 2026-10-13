package com.example.subscriber;

import org.springframework.jms.annotation.JmsListener;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;

@Component
public class OrderConsumer {
    // Pairs with the publisher: both resolve to orders-queue.
    @JmsListener(destination = "${orders.queueName}")
    public void receiveOrder(final Message<String> message) {
    }

    // Nothing in this system publishes to it.
    @JmsListener(destination = "${reports.queueName}")
    public void receiveReport(final Message<String> message) {
    }
}
