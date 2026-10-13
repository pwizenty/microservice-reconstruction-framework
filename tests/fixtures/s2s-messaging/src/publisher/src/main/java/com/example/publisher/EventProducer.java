package com.example.publisher;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jms.core.JmsTemplate;
import org.springframework.stereotype.Component;

@Component
public class EventProducer {
    // The destination is a field, and the field's annotation holds the
    // placeholder - the shape Lakeside Mutual uses.
    @Value("${orders.queueName}")
    private String queueName;

    @Autowired
    private JmsTemplate jmsTemplate;

    public void emit(Object event) {
        jmsTemplate.convertAndSend(queueName, event);
    }

    // A literal destination, read directly.
    public void emitAudit(Object event) {
        jmsTemplate.convertAndSend("audit-queue", event);
    }

    // Built at run time, so the queue cannot be followed.
    public void emitDynamic(String suffix, Object event) {
        jmsTemplate.convertAndSend("events-" + suffix, event);
    }
}
