# Fixture: rest-technology

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. The annotations and the shapes they are written in
are the ones Lakeside Mutual's controllers use, counted over its nineteen
`@RestController` classes, so the fixture covers what that system contains
without copying any of its code.

## What it exercises
The technology information of a REST interface: which annotations the
reconstruction carries over, and which of them is a path rather than an aspect.

| Element | Written as | Exercises |
|---|---|---|
| `CustomerController` | `@RequestMapping("/customers")` | The path of a controller becomes the endpoint of the interface. Shorthand form: the element is unnamed |
| `getCustomers` | `@GetMapping` | A mapping without a path adds no endpoint; the operation is addressed by the interface alone |
| `getCustomers` | `@Operation(summary = …)` | An annotation no aspect of the technology model declares is **not** carried over |
| `getCustomers(filter)` | `@RequestParam(value, required, defaultValue)` | Every named element is read, including `required`, which the technology model does not declare as a property - filtering it is the generator's part, not the reconstruction's |
| `getCustomer` | `@GetMapping(value = "/{customerId}")` | A path in the `value` element |
| `getCustomer(customerId)` | `@PathVariable` | A marker annotation on a parameter |
| `createCustomer(customer)` | `@Valid @RequestBody` | Two aspects on one parameter, in source order |
| `updateCustomer` | `@PreAuthorize("isAuthenticated()")` | An aspect of an operation that carries a value of its own |
| `deleteCustomer` | `@DeleteMapping(path = "/{customerId}")` | A path in the `path` element instead of `value` |
| `deleteCustomer` | `void` return | No outgoing parameter, beside the recovered aspects |

Without the recovery this fixture fails on the first row: the interface carries
no meta-data at all, and no operation carries an endpoint.

## Notes on the expected output
- An endpoint is reported under the reserved meta-data name `Endpoint` with the
  key `address`, not under the name of the annotation it was read from. A path
  is an endpoint address in LEMMA, where the mapping annotations are service
  aspects that declare no properties, so the two cannot share an entry.
- An address is relative to the element above it, exactly as Spring and LEMMA
  both read it. `/customers` on the interface and `/{customerId}` on the
  operation together address `/customers/{customerId}`; nothing concatenates
  them here.
- `required = false` is reported although `spring.technology` declares no such
  property for the `RequestParam` aspect. The reconstruction reports what the
  source states; which of it a technology model can express is decided where
  that model is read.
- The package names are three levels deep (`com.example.customercore`) for the
  same reason as in `minimal-spring`: `match_microservice_interface` needs
  `HIERARCHY_LEVEL` matching parts to link the controller to the service.

Paths in `expected.json` are relative to this fixture directory.
