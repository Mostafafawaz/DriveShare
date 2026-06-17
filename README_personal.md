# DriveShare - My Personal Notes
## CIS 476 Term Project
Last updated: June 17, 2026

---

## What is this project

DriveShare is a peer-to-peer car rental app, similar to Turo.
Car owners can list their vehicles. Renters can browse, watch,
book, and pay for cars. All data lives in memory (no database).
Built in Python 3 with tkinter for the GUI.

This is an individual project (solo, not a team project).

---

## How to run the app

Open a terminal and type:

    python3 main.py

The login screen will open. Use the demo accounts below.

**You need Python 3 and tkinter installed.**
On Mac you can check with:  `python3 -c "import tkinter"`
If it errors, install with:  `brew install python-tk`

---

## Demo accounts

| Account | Email | Password |
|---------|-------|----------|
| Owner | owner@demo.com | pass123 |
| Renter | renter@demo.com | pass123 |

Security question answers for owner: rex / detroit / smith
Security question answers for renter: milo / chicago / jones

---

## How to demo it (for the video)

**Start as owner (owner@demo.com):**
1. Log in - lands on Owner Dashboard
2. Click "Add New Car Listing" - fills in the form using the Builder pattern
3. Save the listing - it appears in the owner dashboard
4. Click "Mark Unavailable" on a car - then click "Mark Available"
   - This triggers the Observer pattern (renter@demo.com will get a notification if they are watching)
5. Click "Lower Price -$5" - also triggers Observer

**Switch to renter (renter@demo.com):**
1. Log in - lands on Browse Cars screen
2. Click "Watch" on a car - attaches an Observer watcher
3. Log back out, log in as owner, lower the price
4. Log back in as renter, click Notifications - the price drop shows up
5. Click "Book" on an available car - goes to BookCarFrame
6. Enter number of days, click Confirm and Pay - uses PaymentProxy to validate, then processes
7. Click "Rental History" - see the booking
8. Click "Messages" - send a message to owner@demo.com

**Show Forgot Password:**
1. Log out, click Forgot Password
2. Enter renter@demo.com
3. Answer: milo / chicago / jones
4. Enter new password - it works

---

## The 6 design patterns and where they are in the code

### 1. Singleton - SessionManager
**Location:** around line 95 in main.py (after Observer section)
**What it does:** Only one user can be logged in at a time.
`SessionManager.get_instance()` always returns the same object.
`_instance` is the class-level variable that holds the one instance.
`__new__` is where the check happens.

**How to explain in the video:**
Show that calling `SessionManager.get_instance()` twice returns
the same object. The login screen calls `.login(user)` and
any other screen can call `.get_current_user()` to know who is logged in.

### 2. Observer - Car watch notifications
**Location:** around line 50 in main.py (CarObserver, RenterWatcher section)
**What it does:** A renter can click "Watch" on a car listing.
This attaches a `RenterWatcher` (ConcreteObserver) to the `CarListing` (Subject).
When the owner changes availability or lowers the price,
`CarListing.notify_watchers()` is called, which calls `update()` on each watcher.
The notification shows up in the renter's Notifications screen.

**GoF roles:**
- Subject: `CarListing` (has `_observers` list, `register_observer()`, `remove_observer()`, `notify_observers()`)
- Observer (abstract): `CarObserver`
- ConcreteObserver: `RenterWatcher`

### 3. Mediator - Screen navigation
**Location:** around line 175 in main.py (AppMediator section)
**What it does:** All screen switching goes through `AppMediator`.
No screen creates or imports another screen. Every frame just calls
`self.mediator.notify(self, "show_X")` and the mediator handles it.

**GoF roles:**
- Mediator (abstract): `AppMediatorBase`
- ConcreteMediator: `AppMediator`
- Colleagues: all the Frame classes

### 4. Builder - Car listing creation
**Location:** around line 120 in main.py (CarListingBuilder section)
**What it does:** When an owner fills out the Add Car form,
each field is set one by one using the builder.
`AddCarFrame` acts as the Director. It calls setter methods in order,
then calls `.build()` to get the finished `CarListing` object.

**GoF roles:**
- AbstractBuilder: `CarListingAbstractBuilder`
- ConcreteBuilder: `CarListingBuilder`
- Director: `AddCarFrame._save()` method
- Product: `CarListing`

### 5. Proxy - Payment validation
**Location:** around line 145 in main.py (PaymentProxy section)
**What it does:** When a renter books a car, the booking screen
does NOT call `RealPaymentService` directly.
It calls `PaymentProxy`, which checks:
- Amount must be > 0
- Renter cannot book their own car
- Renter must have enough balance
Only if those pass does it forward to `RealPaymentService`.

**GoF roles:**
- Subject (abstract): `PaymentService`
- RealSubject: `RealPaymentService`
- Proxy: `PaymentProxy`

### 6. Chain of Responsibility - Password recovery
**Location:** around line 160 in main.py (SecurityHandler section)
**What it does:** To reset a forgotten password, the user must
answer all three security questions they set at registration.
Each question is one handler in the chain. A wrong answer stops the chain
and returns an error. All three must be correct.

**GoF roles:**
- Handler (abstract): `SecurityHandler`
- ConcreteHandlers: `Q1Handler`, `Q2Handler`, `Q3Handler`
- Client: `ForgotPasswordFrame._reset()`

---

## What is done right now

- [x] main.py - full working app with all 6 patterns and 10 screens
- [x] tkinter GUI - Login, Register, Forgot Password, Owner Dashboard,
      Add Car, Renter Dashboard, Book Car, Messages, History, Notifications
- [x] Demo data pre-loaded (2 users, 2 cars)
- [x] All patterns are testable in the running app
- [x] Code is in natural student style, no textbook quoting

---

## What is still missing before submitting

- [ ] **GitHub repository** - needs to be public
      Email professor and TA the link:
      - zwxu@umich.edu (professor)
      - zibapars@umich.edu (TA)
      Files to put in the repo: main.py, README_personal.md or a new README.md,
      any UML diagrams you make

- [ ] **Pre-recorded video** - screen recording of the app demo
      Upload to YouTube or Google Drive and get a shareable link
      Suggested outline (10-15 min):
      1. Briefly explain what DriveShare is (1 min)
      2. Run the app, show the login screen
      3. Log in as owner, add a car (Builder pattern)
      4. Log in as renter, watch a car, then switch to owner and lower price,
         then switch back and show the notification (Observer pattern)
      5. Book a car (Proxy pattern - explain the validation)
      6. Show forgot password with security questions (Chain of Responsibility)
      7. Mention Mediator quickly (all screen switching goes through AppMediator)
      8. Mention Singleton quickly (SessionManager)

- [ ] **Presentation slides (.pptx)** - ask me to make these
      Typical structure:
      - Title slide
      - What is DriveShare (problem it solves)
      - System overview / architecture
      - One slide per pattern (6 slides) with a quick diagram or code snippet
      - Demo summary slide
      - Conclusion

- [ ] **One-page report for Canvas submission**
      Should include: your name, course, GitHub repo URL, video URL
      Short paragraph about what you built and which patterns you used

- [ ] **UML class diagrams (optional but good)**
      One diagram per pattern showing the GoF participant classes
      Can be done in draw.io (free, online) or PowerPoint shapes
      Export as PNG and add to the GitHub repo

- [ ] **Screenshots of each screen** (optional but helps the report)
      Run the app and take a screenshot of each of the 10 screens

---

## How to update this file

At the start of every work session, tell me what you want to do next
and I will update the checkboxes and notes in this file.

When something new is added (GitHub link, video link, slides are done),
update the checkboxes and add the links here.

---

## Files in this folder

| File | What it is |
|------|-----------|
| main.py | The full DriveShare app - run this |
| README_personal.md | This file - your personal notes |
| (add more as you create them) | |

---

## Quick answers to likely questions

**Q: Do I need a database?**
No. The project uses in-memory storage (Python lists and dicts).
All data resets when the app closes. That is fine for this project.

**Q: Can I register a new account in the app?**
Yes. Click "Create Account" on the login screen. You can pick Owner, Renter, or Both.
You will also set three security questions.

**Q: What happens if the renter does not have enough money to book?**
The Proxy blocks the payment and shows an error. The renter's balance starts at $500.

**Q: Where does the Observer notification go?**
It goes into the `NOTIFICATIONS` dictionary under the renter's email.
The Notifications screen reads from there when it opens.
