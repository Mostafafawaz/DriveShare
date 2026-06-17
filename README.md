# DriveShare — Peer-to-Peer Car Rental Platform

**CIS 476 – Software Architecture and Design Patterns**
**Student:** Mostafa Mohamed
**University of Michigan – Dearborn**

---

## What is DriveShare

DriveShare is a desktop car rental application modeled after Turo.com.
Car owners can list their vehicles for short-term rental. Renters can browse
available cars, watch listings for price drops, book a car, and pay through
the app. All data is stored in memory — no database is required.

Built with Python 3 and tkinter.

---

## How to Run

```bash
python3 main.py
```

You need Python 3 and tkinter installed.

On Mac, check with:
```bash
python3 -c "import tkinter"
```

If it errors, install with:
```bash
brew install python-tk
```

---

## Demo Accounts

| Role   | Email             | Password |
|--------|-------------------|----------|
| Owner  | owner@demo.com    | pass123  |
| Renter | renter@demo.com   | pass123  |

Security question answers for the owner account: `rex` / `detroit` / `smith`
Security question answers for the renter account: `milo` / `chicago` / `jones`

---

## Design Patterns Implemented

This project uses six GoF design patterns:

### 1. Singleton — SessionManager
Only one user can be logged in at a time. `SessionManager.get_instance()`
always returns the same object. The `_instance` class variable and `__new__`
enforce the single-instance constraint.

### 2. Observer — Car Watch Notifications
`CarListing` is the Subject. When a renter clicks "Watch," a `RenterWatcher`
(ConcreteObserver) is registered with `register_observer()`. When the owner
changes availability or lowers the price, `notify_observers()` is called,
which calls `update()` on every registered observer. Notifications appear
in the renter's notification inbox.

### 3. Mediator — Screen Navigation
`AppMediator` is the ConcreteMediator. All 10 UI frames are Colleagues.
No frame creates or imports another frame. Every navigation event goes
through `self.mediator.notify(self, "show_X")` and the mediator handles it.

### 4. Builder — Car Listing Creation
`AddCarFrame._save()` acts as the Director. It calls setter methods on
`CarListingBuilder` (ConcreteBuilder) one at a time, then calls `build()`
to get the finished `CarListing` (Product).

### 5. Proxy — Payment Validation
`PaymentProxy` sits between the booking screen and `RealPaymentService`.
It validates the payment amount, checks that the renter is not booking
their own car, and checks the renter's balance before forwarding to the
real service.

### 6. Chain of Responsibility — Password Recovery
Three security question handlers (`Q1Handler`, `Q2Handler`, `Q3Handler`)
are chained together. All three answers must be correct to reset the password.
A wrong answer stops the chain and returns an error.

---

## Screens (10 total)

1. Login
2. Register
3. Forgot Password
4. Owner Dashboard
5. Add Car
6. Renter Dashboard (Browse Cars)
7. Book Car
8. Messages
9. Rental History
10. Notifications

---

## Files in This Repository

| File | Description |
|------|-------------|
| `main.py` | Full application — run this file |
| `README.md` | This file |
| `diagrams/` | UML class diagrams for each pattern |
| `slides/` | Presentation slides (.pptx) |
| `screenshots/` | UI screenshots of each screen |

---

## Notes

- No real database is used. All data resets when the app closes.
- No real payment is made. The proxy simulates validation and deducts from an in-memory balance.
- Code is thoroughly commented with GoF role labels on each class.
