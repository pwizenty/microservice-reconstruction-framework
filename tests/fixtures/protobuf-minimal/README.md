# Fixture: protobuf-minimal

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. The shapes are the ones Lakeside Mutual's
`risk-management-server/riskmanagement.proto` uses, plus the proto3 constructs it
does not, so the fixture covers the language rather than one file.

Compared by `tests/test_protobuf_plugin.py` against `expected_protobuf.json`.
The name differs from `expected.json` on purpose: the fixtures of
`test_golden.py` are found by that name and run the Java and Spring plugins,
which have nothing to reconstruct here.

## What it exercises
The shape of a service contract: one file describing a service, its operations
and the data they exchange.

| Element | Exercises |
|---|---|
| `package com.example.orders` + `service OrderQuery` | the qualified name of the context and of the microservice, `com.example.orders.OrderQuery` |
| `rpc GetOrder (GetOrderRequest) returns (Order)` | an operation with an incoming and a result parameter, both typed |
| `rpc WatchOrders (WatchRequest) returns (stream Order)` | a stream, which is a sequence rather than one value, so the parameter is asynchronous |
| `message WatchRequest {}` | a structure with no field, which proto3 allows |
| `repeated OrderLine lines` | a collection beside the structure, which the field refers to |
| `message OrderLine` nested in `Order` | the structure is named `Order_OrderLine`, because a dot in the name would be read as the context by the LEMMA side, and a structure's name is a single identifier there |
| the reference `OrderLine` from inside `Order` | proto3 refers to a nested type by its simple name, which has to resolve to the structure declared under the joined one |
| `enum Status` and the field that refers to it | the field's type is marked as an enumeration, not as a structure: the generator branches on the kind and would otherwise reference a structure that was never declared |
