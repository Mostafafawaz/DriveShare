"""
CIS 476 - Software Architecture and Design Patterns
Term Project - DriveShare: Peer-to-Peer Car Rental Platform
Student: Mostafa Mohamed

This program is a car rental platform where car owners can list
their vehicles and renters can search, book, and pay for them.
The idea is based on how Turo.com works.

Six design patterns are used:
    1. Singleton             - SessionManager (one active session)
    2. Observer              - Car watch list notifications
    3. Mediator              - Screen navigation between UI frames
    4. Builder               - Building car listing objects step by step
    5. Proxy                 - Payment validation before processing
    6. Chain of Responsibility - Password recovery with 3 security questions

Language: Python 3  (tkinter for the GUI)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from abc import ABC, abstractmethod
import datetime


# ============================================================
# Data classes - User, CarListing, Booking, Message
# ============================================================
# No database is used. Everything is stored in memory.
# USERS, CARS, MESSAGES, and NOTIFICATIONS are global lists/dicts
# that hold all data while the program is running.

class User:
    def __init__(self, email, password, name, role,
                 q1, a1, q2, a2, q3, a3):
        self.email = email
        self.password = password
        self.name = name
        self.role = role           # "owner", "renter", or "both"
        self.questions = [q1, q2, q3]
        self.answers = [a1, a2, a3]
        self.balance = 500.0       # starting money for payment demo
        self.rental_history = []   # list of Booking objects


class CarListing:
    # This class also acts as the Subject in the Observer pattern.
    # When availability or price changes, it notifies all observers.
    # GoF Subject methods: register_observer, remove_observer, notify_observers

    _next_id = 1

    def __init__(self):
        self.listing_id = CarListing._next_id
        CarListing._next_id += 1
        self.owner = None
        self.make = ""
        self.model = ""
        self.year = ""
        self.mileage = ""
        self.location = ""
        self.price_per_day = 0.0
        self.available = True
        self._observers = []   # list of CarObserver objects (Observer pattern)

    def register_observer(self, observer):
        # GoF role: Subject.registerObserver()
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer):
        # GoF role: Subject.removeObserver()
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, event_msg):
        # GoF role: Subject.notifyObservers()
        for obs in self._observers:
            obs.update(self, event_msg)

    def set_available(self, value):
        old = self.available
        self.available = value
        if not old and value:
            self.notify_observers("Car is now available for booking.")

    def set_price(self, new_price):
        if new_price < self.price_per_day:
            self.price_per_day = new_price
            self.notify_observers("Price dropped to $" + str(new_price) + "/day.")
        else:
            self.price_per_day = new_price

    def __str__(self):
        status = "Available" if self.available else "Not Available"
        return ("[#" + str(self.listing_id) + "] " + self.year + " " +
                self.make + " " + self.model + " | " + self.location +
                " | $" + str(self.price_per_day) + "/day | " + status)


class Booking:
    _next_id = 1

    def __init__(self, car, renter, days):
        self.booking_id = Booking._next_id
        Booking._next_id += 1
        self.car = car
        self.renter = renter
        self.days = days
        self.total = car.price_per_day * days
        self.date = datetime.date.today().isoformat()

    def __str__(self):
        return ("Booking #" + str(self.booking_id) + ": " +
                self.car.year + " " + self.car.make + " " + self.car.model +
                " | " + str(self.days) + " day(s) | Total: $" +
                str(round(self.total, 2)) + " | Date: " + self.date)


class Message:
    def __init__(self, sender_email, receiver_email, text):
        self.sender_email = sender_email
        self.receiver_email = receiver_email
        self.text = text
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# Global data stores
USERS = {}          # email -> User
CARS = []           # list of CarListing
MESSAGES = []       # list of Message
NOTIFICATIONS = {}  # email -> list of strings


# ============================================================
# Pattern 2: Observer - Car watch notifications
# ============================================================
# GoF: Observer (Behavioral)
# When a renter clicks "Watch" on a car, a RenterWatcher (ConcreteObserver)
# is registered on that CarListing (Subject). If the owner later makes the car
# available again or lowers the price, the Subject calls notify_observers(),
# which calls update() on every registered observer.

class CarObserver(ABC):
    @abstractmethod
    def update(self, car, event_msg):
        pass


class RenterWatcher(CarObserver):
    def __init__(self, renter_email):
        self.renter_email = renter_email
        self.notifications = NOTIFICATIONS.setdefault(renter_email, [])

    def update(self, car, event_msg):
        note = ("[Car #" + str(car.listing_id) + "] " +
                car.year + " " + car.make + " " + car.model +
                ": " + event_msg)
        self.notifications.append(note)


def get_or_create_watcher(renter_email, car):
    # Check if an observer already exists for this renter on this car.
    for obs in car._observers:
        if isinstance(obs, RenterWatcher) and obs.renter_email == renter_email:
            return obs
    # No observer found, create one and register it with the car (Subject).
    new_watcher = RenterWatcher(renter_email)
    car.register_observer(new_watcher)
    return new_watcher


# ============================================================
# Pattern 1: Singleton - SessionManager
# ============================================================
# GoF: Singleton (Creational)
# Only one user can be logged in at a time in one session.
# The SessionManager holds who that user is and gives access
# to that user from anywhere in the program.

class SessionManager:

    _instance = None   # the one and only instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_user = None
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def login(self, user):
        self._current_user = user

    def logout(self):
        self._current_user = None

    def get_current_user(self):
        return self._current_user

    def is_logged_in(self):
        return self._current_user is not None


# ============================================================
# Pattern 4: Builder - CarListingBuilder
# ============================================================
# GoF: Builder (Creational)
# Instead of passing a lot of arguments to a constructor,
# the owner fills in each field one at a time through the form.
# The AddCarFrame acts as the Director. It calls each setter
# in order and then calls build() to get the finished car object.

class CarListingAbstractBuilder(ABC):
    @abstractmethod
    def set_owner(self, owner): pass
    @abstractmethod
    def set_make(self, make): pass
    @abstractmethod
    def set_model(self, model): pass
    @abstractmethod
    def set_year(self, year): pass
    @abstractmethod
    def set_mileage(self, mileage): pass
    @abstractmethod
    def set_location(self, location): pass
    @abstractmethod
    def set_price(self, price): pass
    @abstractmethod
    def build(self): pass


class CarListingBuilder(CarListingAbstractBuilder):

    def __init__(self):
        self._car = CarListing()

    def set_owner(self, owner):
        self._car.owner = owner
        return self

    def set_make(self, make):
        self._car.make = make
        return self

    def set_model(self, model):
        self._car.model = model
        return self

    def set_year(self, year):
        self._car.year = year
        return self

    def set_mileage(self, mileage):
        self._car.mileage = mileage
        return self

    def set_location(self, location):
        self._car.location = location
        return self

    def set_price(self, price):
        self._car.price_per_day = float(price)
        return self

    def build(self):
        # Return the finished car and reset for the next build.
        finished_car = self._car
        self._car = CarListing()
        return finished_car


# ============================================================
# Pattern 5: Proxy - Payment
# ============================================================
# GoF: Proxy (Structural)
# PaymentProxy checks the transaction before passing it to the
# real payment service. The renter never talks to the real
# service directly. The proxy blocks bad requests early.

class PaymentService(ABC):
    @abstractmethod
    def process_payment(self, amount, payer, payee, booking):
        pass


class RealPaymentService(PaymentService):
    def process_payment(self, amount, payer, payee, booking):
        payer.balance = payer.balance - amount
        payee.balance = payee.balance + amount
        payer.rental_history.append(booking)
        return True, ("Payment of $" + str(round(amount, 2)) + " processed.\n" +
                      payer.name + " paid " + payee.name + ".\n" +
                      "Your new balance: $" + str(round(payer.balance, 2)))


class PaymentProxy(PaymentService):

    def __init__(self):
        self._real = RealPaymentService()

    def process_payment(self, amount, payer, payee, booking):
        # Validate before passing to the real service
        if amount <= 0:
            return False, "Invalid payment amount."
        if payer.email == payee.email:
            return False, "You cannot book your own car."
        if payer.balance < amount:
            return False, ("Not enough balance.\n" +
                           "Your balance: $" + str(round(payer.balance, 2)) + "\n" +
                           "Amount needed: $" + str(round(amount, 2)))
        return self._real.process_payment(amount, payer, payee, booking)


# ============================================================
# Pattern 6: Chain of Responsibility - Password recovery
# ============================================================
# GoF: Chain of Responsibility (Behavioral)
# To reset a forgotten password, the user has to answer all
# three security questions they set when they registered.
# Each question is one handler in the chain. All three must
# be answered correctly or the password is not reset.

class SecurityHandler(ABC):
    def __init__(self, index):
        self.index = index
        self._next = None

    def set_next(self, handler):
        self._next = handler
        return handler

    @abstractmethod
    def handle(self, user, answers):
        pass


class Q1Handler(SecurityHandler):
    def __init__(self):
        super().__init__(0)

    def handle(self, user, answers):
        if answers[0].strip().lower() != user.answers[0].strip().lower():
            return False, "Answer to question 1 is wrong."
        if self._next:
            return self._next.handle(user, answers)
        return True, "All answers correct."


class Q2Handler(SecurityHandler):
    def __init__(self):
        super().__init__(1)

    def handle(self, user, answers):
        if answers[1].strip().lower() != user.answers[1].strip().lower():
            return False, "Answer to question 2 is wrong."
        if self._next:
            return self._next.handle(user, answers)
        return True, "All answers correct."


class Q3Handler(SecurityHandler):
    def __init__(self):
        super().__init__(2)

    def handle(self, user, answers):
        if answers[2].strip().lower() != user.answers[2].strip().lower():
            return False, "Answer to question 3 is wrong."
        if self._next:
            return self._next.handle(user, answers)
        return True, "All answers correct."


def build_recovery_chain():
    q1 = Q1Handler()
    q2 = Q2Handler()
    q3 = Q3Handler()
    q1.set_next(q2)
    q2.set_next(q3)
    return q1   # head of the chain


# ============================================================
# Pattern 3: Mediator - AppMediator
# ============================================================
# GoF: Mediator (Behavioral)
# All navigation between screens goes through the AppMediator.
# No screen creates or references another screen directly.
# When a screen needs to go somewhere, it calls:
#     self.mediator.notify(self, "show_X")
# The mediator handles the rest.

class AppMediatorBase(ABC):
    @abstractmethod
    def notify(self, sender, event, data=None):
        pass


class AppMediator(AppMediatorBase):

    def __init__(self, root):
        self.root = root
        self._frames = {}

    def register_frame(self, name, frame):
        self._frames[name] = frame

    def show_frame(self, name):
        for f in self._frames.values():
            f.pack_forget()
        self._frames[name].pack(fill="both", expand=True)
        if hasattr(self._frames[name], "on_show"):
            self._frames[name].on_show()

    def notify(self, sender, event, data=None):
        if event == "show_login":
            self.show_frame("login")
        elif event == "show_register":
            self.show_frame("register")
        elif event == "show_forgot":
            self.show_frame("forgot")
        elif event == "show_owner_dash":
            self.show_frame("owner_dash")
        elif event == "show_add_car":
            self.show_frame("add_car")
        elif event == "show_renter_dash":
            self.show_frame("renter_dash")
        elif event == "show_book_car":
            self.show_frame("book_car")
            if data:
                self._frames["book_car"].set_car(data)
        elif event == "show_messages":
            self.show_frame("messages")
            if data:
                self._frames["messages"].set_partner(data)
        elif event == "show_history":
            self.show_frame("history")
        elif event == "show_notifications":
            self.show_frame("notifications")


# ============================================================
# Shared colors and helpers
# ============================================================

BG        = "#f0f2f5"   # app background
NAV_BG    = "#1a73e8"   # nav bar / primary buttons
NAV_DARK  = "#1558c0"   # darker nav shade
WHITE     = "white"
CARD_BG   = "white"
TEXT      = "#1c1c2e"
MUTED     = "#5f6368"
GREEN     = "#2e7d32"
AMBER     = "#e65100"
RED_FG    = "#c62828"


def _nav_btn(parent, text, command, side="right"):
    """Small white button for nav bars."""
    b = tk.Button(parent, text=text, font=("Arial", 10, "bold"),
                  bg=NAV_DARK, fg=WHITE, bd=0, padx=12, pady=6,
                  relief="flat", cursor="hand2", command=command)
    b.pack(side=side, padx=6, pady=8)
    return b


def _big_btn(parent, text, command, bg=NAV_BG, fg=WHITE, width=22):
    """Large primary action button."""
    return tk.Button(parent, text=text, font=("Arial", 12, "bold"),
                     bg=bg, fg=fg, bd=0, padx=16, pady=10,
                     width=width, relief="flat", cursor="hand2",
                     command=command)


def _link_btn(parent, text, command):
    """Flat text link button."""
    return tk.Button(parent, text=text, font=("Arial", 11),
                     bg=BG, fg=NAV_BG, bd=0, padx=8, pady=6,
                     relief="flat", cursor="hand2", command=command)


def _scrollable(parent, bg=BG):
    """
    Returns (outer_frame, inner_frame, canvas).
    Pack or grid outer_frame. Add widgets to inner_frame.
    The inner_frame auto-fills the canvas width.
    Mousewheel scroll is bound automatically.
    """
    outer = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=bg)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_resize(e):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_resize(e):
        canvas.itemconfig(win_id, width=e.width)

    def _on_wheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    inner.bind("<Configure>", _on_inner_resize)
    canvas.bind("<Configure>", _on_canvas_resize)
    canvas.bind_all("<MouseWheel>", _on_wheel)
    return outer, inner, canvas


# ============================================================
# Base frame - parent class for all screens
# ============================================================

class BaseFrame(tk.Frame):
    def __init__(self, parent, mediator):
        super().__init__(parent, bg=BG)
        self.mediator = mediator


# ============================================================
# LoginFrame
# ============================================================

class LoginFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Vertical centering wrapper
        wrapper = tk.Frame(self, bg=BG)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # App title
        tk.Label(wrapper, text="DriveShare",
                 font=("Arial", 34, "bold"), bg=BG, fg=NAV_BG).pack(pady=(0, 4))
        tk.Label(wrapper, text="Peer-to-Peer Car Rental",
                 font=("Arial", 13), bg=BG, fg=MUTED).pack(pady=(0, 24))

        # White card
        card = tk.Frame(wrapper, bg=WHITE, bd=1, relief="groove")
        card.pack(ipadx=30, ipady=20)

        tk.Label(card, text="Email", font=("Arial", 11),
                 bg=WHITE, fg=TEXT, anchor="w").pack(fill="x", padx=24, pady=(18, 2))
        self.email_var = tk.StringVar()
        tk.Entry(card, textvariable=self.email_var,
                 font=("Arial", 12), width=30,
                 relief="solid", bd=1).pack(padx=24, pady=(0, 10), ipady=5)

        tk.Label(card, text="Password", font=("Arial", 11),
                 bg=WHITE, fg=TEXT, anchor="w").pack(fill="x", padx=24, pady=(4, 2))
        self.pass_var = tk.StringVar()
        tk.Entry(card, textvariable=self.pass_var,
                 font=("Arial", 12), width=30, show="*",
                 relief="solid", bd=1).pack(padx=24, pady=(0, 6), ipady=5)

        self.msg = tk.Label(card, text="", font=("Arial", 10),
                            bg=WHITE, fg=RED_FG)
        self.msg.pack(pady=(2, 8))

        btn = _big_btn(card, "Log In", self._login)
        btn.pack(padx=24, pady=(0, 18), fill="x")

        # Separator
        tk.Frame(wrapper, bg="#ddd", height=1).pack(fill="x", pady=12)

        # Secondary actions - clearly spaced
        _link_btn(wrapper, "Create a new account",
                  lambda: self.mediator.notify(self, "show_register")).pack(pady=4)
        _link_btn(wrapper, "Forgot password?",
                  lambda: self.mediator.notify(self, "show_forgot")).pack(pady=2)

        tk.Label(wrapper,
                 text="Demo:  owner@demo.com / pass123     renter@demo.com / pass123",
                 font=("Arial", 9), bg=BG, fg="#bbb").pack(pady=(20, 0))

    def _login(self):
        email = self.email_var.get().strip().lower()
        pw = self.pass_var.get()
        user = USERS.get(email)

        if user is None or user.password != pw:
            self.msg.config(text="Wrong email or password.")
            return

        # Use the Singleton SessionManager to log in
        SessionManager.get_instance().login(user)
        self.msg.config(text="")
        self.email_var.set("")
        self.pass_var.set("")

        if user.role in ("owner", "both"):
            self.mediator.notify(self, "show_owner_dash")
        else:
            self.mediator.notify(self, "show_renter_dash")


# ============================================================
# RegisterFrame
# ============================================================

class RegisterFrame(BaseFrame):

    QUESTIONS = [
        "What is the name of your first pet?",
        "What city were you born in?",
        "What is your mother's maiden name?"
    ]

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Create Account", font=("Arial", 14, "bold"),
                 bg=NAV_BG, fg=WHITE).pack(side="left", padx=18, pady=12)
        _nav_btn(hdr, "Back to Login",
                 lambda: self.mediator.notify(self, "show_login"), side="right")

        # Scrollable body
        outer, inner, _ = _scrollable(self, bg=BG)
        outer.pack(fill="both", expand=True)

        self.name_var  = tk.StringVar()
        self.email_var = tk.StringVar()
        self.pass_var  = tk.StringVar()
        self.role_var  = tk.StringVar(value="renter")
        self.a_vars    = [tk.StringVar(), tk.StringVar(), tk.StringVar()]

        pad = {"padx": 40}

        def field(label_text, var, show=""):
            tk.Label(inner, text=label_text, font=("Arial", 11),
                     bg=BG, fg=TEXT, anchor="w").pack(fill="x", pady=(12, 2), **pad)
            e = tk.Entry(inner, textvariable=var, font=("Arial", 12),
                         width=36, show=show, relief="solid", bd=1)
            e.pack(fill="x", ipady=5, pady=(0, 2), **pad)

        field("Full Name", self.name_var)
        field("Email Address", self.email_var)
        field("Password", self.pass_var, show="*")

        # Role selector
        tk.Label(inner, text="Account Type", font=("Arial", 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(18, 6), **pad)
        role_box = tk.Frame(inner, bg=WHITE, bd=1, relief="groove")
        role_box.pack(fill="x", pady=(0, 4), **pad)
        for val, txt in [("renter", "Renter  —  I want to rent cars"),
                         ("owner",  "Owner  —  I want to list my car"),
                         ("both",   "Both  —  I want to list and rent")]:
            tk.Radiobutton(role_box, text=txt, variable=self.role_var,
                           value=val, font=("Arial", 11),
                           bg=WHITE, activebackground=WHITE,
                           pady=8, padx=14).pack(anchor="w")

        # Security questions
        tk.Label(inner, text="Security Questions  (for password recovery)",
                 font=("Arial", 11, "bold"), bg=BG, fg=TEXT).pack(
            anchor="w", pady=(18, 4), **pad)

        for i, q in enumerate(self.QUESTIONS):
            tk.Label(inner, text="Q" + str(i + 1) + ": " + q,
                     font=("Arial", 10), bg=BG, fg=MUTED,
                     wraplength=520, justify="left").pack(
                anchor="w", pady=(8, 2), **pad)
            tk.Entry(inner, textvariable=self.a_vars[i],
                     font=("Arial", 12), width=36,
                     relief="solid", bd=1).pack(
                fill="x", ipady=5, pady=(0, 2), **pad)

        self.msg = tk.Label(inner, text="", font=("Arial", 10),
                            bg=BG, fg=RED_FG)
        self.msg.pack(pady=(10, 4))

        _big_btn(inner, "Create Account", self._register).pack(
            pady=(4, 6), **pad, fill="x")
        tk.Frame(inner, bg=BG, height=20).pack()  # bottom spacer

    def _register(self):
        name    = self.name_var.get().strip()
        email   = self.email_var.get().strip().lower()
        pw      = self.pass_var.get()
        role    = self.role_var.get()
        answers = [v.get().strip() for v in self.a_vars]

        if not name or not email or not pw:
            self.msg.config(text="Name, email, and password are required.")
            return
        if "@" not in email:
            self.msg.config(text="Enter a valid email address.")
            return
        if email in USERS:
            self.msg.config(text="An account with this email already exists.")
            return
        if any(a == "" for a in answers):
            self.msg.config(text="Please answer all three security questions.")
            return

        q = self.QUESTIONS
        new_user = User(email, pw, name, role,
                        q[0], answers[0],
                        q[1], answers[1],
                        q[2], answers[2])
        USERS[email] = new_user
        NOTIFICATIONS.setdefault(email, [])
        messagebox.showinfo("Done", "Account created. You can now log in.")
        self.mediator.notify(self, "show_login")


# ============================================================
# ForgotPasswordFrame
# ============================================================
# Uses the Chain of Responsibility (Pattern 6) to check the
# three security answers before allowing a password reset.

class ForgotPasswordFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Password Recovery", font=("Arial", 14, "bold"),
                 bg=NAV_BG, fg=WHITE).pack(side="left", padx=18, pady=12)
        _nav_btn(hdr, "Back to Login",
                 lambda: self.mediator.notify(self, "show_login"), side="right")

        # Scrollable body
        outer, inner, _ = _scrollable(self, bg=BG)
        outer.pack(fill="both", expand=True)

        tk.Label(inner,
                 text="Answer all three security questions exactly as you entered them at registration.",
                 font=("Arial", 11), bg=BG, fg=MUTED,
                 wraplength=540, justify="left").pack(
            anchor="w", padx=40, pady=(20, 4))

        pad = {"padx": 40}

        self.email_var   = tk.StringVar()
        self.a_vars      = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.new_pass_var = tk.StringVar()

        def field(label_text, var, show=""):
            tk.Label(inner, text=label_text, font=("Arial", 11),
                     bg=BG, fg=TEXT, anchor="w",
                     wraplength=520, justify="left").pack(
                fill="x", pady=(10, 2), **pad)
            tk.Entry(inner, textvariable=var, font=("Arial", 12),
                     width=36, show=show, relief="solid", bd=1).pack(
                fill="x", ipady=5, pady=(0, 2), **pad)

        field("Email Address", self.email_var)
        for i, q in enumerate(RegisterFrame.QUESTIONS):
            field("Q" + str(i + 1) + ": " + q, self.a_vars[i])
        field("New Password", self.new_pass_var, show="*")

        self.msg = tk.Label(inner, text="", font=("Arial", 10),
                            bg=BG, fg=RED_FG)
        self.msg.pack(pady=(10, 4))

        _big_btn(inner, "Reset Password", self._reset).pack(
            pady=(4, 6), fill="x", **pad)
        tk.Frame(inner, bg=BG, height=20).pack()

    def _reset(self):
        email  = self.email_var.get().strip().lower()
        answers = [v.get().strip() for v in self.a_vars]
        new_pw = self.new_pass_var.get()

        user = USERS.get(email)
        if user is None:
            self.msg.config(text="No account found with that email.")
            return
        if not new_pw:
            self.msg.config(text="Please enter a new password.")
            return

        # Build the chain and run the answers through it
        chain = build_recovery_chain()
        ok, result_msg = chain.handle(user, answers)

        if ok:
            user.password = new_pw
            messagebox.showinfo("Done", "Password reset. You can now log in.")
            self.mediator.notify(self, "show_login")
        else:
            self.msg.config(text=result_msg)


# ============================================================
# OwnerDashFrame
# ============================================================

class OwnerDashFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Nav bar
        nav = tk.Frame(self, bg=NAV_BG)
        nav.pack(fill="x")
        tk.Label(nav, text="DriveShare  —  Owner Dashboard",
                 font=("Arial", 13, "bold"),
                 bg=NAV_BG, fg=WHITE).pack(side="left", padx=16, pady=10)
        _nav_btn(nav, "Logout",   self._logout)
        _nav_btn(nav, "Messages", lambda: self.mediator.notify(self, "show_messages"))

        # Welcome bar
        self.info = tk.Label(self, text="", font=("Arial", 11),
                             bg=BG, fg=TEXT)
        self.info.pack(anchor="w", padx=20, pady=(10, 2))

        # Add car button
        _big_btn(self, "+ Add New Car Listing",
                 lambda: self.mediator.notify(self, "show_add_car"),
                 bg=GREEN, width=26).pack(anchor="w", padx=20, pady=(4, 8))

        tk.Label(self, text="Your Listings", font=("Arial", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=20, pady=(0, 4))

        # Scrollable car list
        outer, self.car_frame, _ = _scrollable(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def on_show(self):
        for w in self.car_frame.winfo_children():
            w.destroy()

        user = SessionManager.get_instance().get_current_user()
        self.info.config(text="Welcome, " + user.name +
                              "   |   Balance: $" + str(round(user.balance, 2)))

        my_cars = [c for c in CARS if c.owner and c.owner.email == user.email]

        if not my_cars:
            tk.Label(self.car_frame,
                     text="No listings yet. Click + Add New Car Listing above.",
                     font=("Arial", 11), bg=BG, fg=MUTED).pack(pady=24)
            return

        for car in my_cars:
            card = tk.Frame(self.car_frame, bg=WHITE, bd=1, relief="solid")
            card.pack(fill="x", pady=6, ipady=8)

            # Car info (left side)
            info_col = tk.Frame(card, bg=WHITE)
            info_col.pack(side="left", padx=12, pady=4, fill="x", expand=True)

            status_color = GREEN if car.available else "#b71c1c"
            status_text  = "Available" if car.available else "Not Available"

            tk.Label(info_col,
                     text=car.year + " " + car.make + " " + car.model,
                     font=("Arial", 12, "bold"), bg=WHITE, fg=TEXT).pack(anchor="w")
            tk.Label(info_col,
                     text="Location: " + car.location + "   |   Mileage: " + car.mileage,
                     font=("Arial", 10), bg=WHITE, fg=MUTED).pack(anchor="w", pady=1)
            tk.Label(info_col,
                     text="$" + str(car.price_per_day) + "/day   |   " + status_text,
                     font=("Arial", 10, "bold"), bg=WHITE, fg=status_color).pack(anchor="w")

            # Action buttons (right side)
            btn_col = tk.Frame(card, bg=WHITE)
            btn_col.pack(side="right", padx=12, pady=4)

            avail_label = "Mark Unavailable" if car.available else "Mark Available"
            avail_bg    = "#e53935" if car.available else GREEN

            def toggle_avail(c=car):
                # Toggle availability - this fires Observer notify_observers()
                c.set_available(not c.available)
                self.on_show()

            tk.Button(btn_col, text=avail_label,
                      font=("Arial", 10), bg=avail_bg, fg=WHITE,
                      bd=0, padx=10, pady=6, cursor="hand2",
                      command=toggle_avail).pack(fill="x", pady=3)

            def drop_price(c=car):
                # Lower price by $5 - also fires Observer notify_observers()
                if c.price_per_day > 5:
                    c.set_price(c.price_per_day - 5)
                    self.on_show()

            tk.Button(btn_col, text="Lower Price  -$5",
                      font=("Arial", 10), bg=AMBER, fg=WHITE,
                      bd=0, padx=10, pady=6, cursor="hand2",
                      command=drop_price).pack(fill="x", pady=3)

    def _logout(self):
        SessionManager.get_instance().logout()
        self.mediator.notify(self, "show_login")


# ============================================================
# AddCarFrame - Director in the Builder pattern
# ============================================================

class AddCarFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Add New Car Listing",
                 font=("Arial", 14, "bold"), bg=NAV_BG, fg=WHITE).pack(
            side="left", padx=16, pady=12)
        _nav_btn(hdr, "Cancel",
                 lambda: self.mediator.notify(self, "show_owner_dash"))

        # White form card
        card = tk.Frame(self, bg=WHITE, bd=1, relief="groove")
        card.place(relx=0.5, rely=0.52, anchor="center", width=500)

        pad = {"padx": 30}

        fields_cfg = [
            ("Make  (e.g. Toyota)",    "make"),
            ("Model  (e.g. Camry)",    "model"),
            ("Year  (e.g. 2021)",      "year"),
            ("Mileage  (e.g. 30,000 mi)", "mileage"),
            ("Pickup Location",        "location"),
            ("Price per Day  ($)",     "price"),
        ]

        self.fields = {}
        for label_text, key in fields_cfg:
            tk.Label(card, text=label_text, font=("Arial", 11),
                     bg=WHITE, fg=TEXT, anchor="w").pack(
                fill="x", pady=(14, 2), **pad)
            var = tk.StringVar()
            self.fields[key] = var
            tk.Entry(card, textvariable=var, font=("Arial", 12),
                     width=36, relief="solid", bd=1).pack(
                fill="x", ipady=5, pady=(0, 2), **pad)

        self.msg = tk.Label(card, text="", font=("Arial", 10),
                            bg=WHITE, fg=RED_FG)
        self.msg.pack(pady=(8, 4))

        _big_btn(card, "Save Listing", self._save).pack(
            pady=(0, 20), fill="x", **pad)

    def _save(self):
        make     = self.fields["make"].get().strip()
        model    = self.fields["model"].get().strip()
        year     = self.fields["year"].get().strip()
        mileage  = self.fields["mileage"].get().strip()
        location = self.fields["location"].get().strip()
        price_str= self.fields["price"].get().strip()

        if not make or not model or not year or not location or not price_str:
            self.msg.config(text="Make, model, year, location, and price are required.")
            return

        try:
            price = float(price_str)
            if price <= 0:
                raise ValueError
        except ValueError:
            self.msg.config(text="Price must be a number greater than zero.")
            return

        user = SessionManager.get_instance().get_current_user()

        # Director role: call builder steps in order, then build()
        builder = CarListingBuilder()
        builder.set_owner(user)
        builder.set_make(make)
        builder.set_model(model)
        builder.set_year(year)
        builder.set_mileage(mileage if mileage else "N/A")
        builder.set_location(location)
        builder.set_price(price)
        car = builder.build()

        CARS.append(car)

        for key in self.fields:
            self.fields[key].set("")
        self.msg.config(text="")
        messagebox.showinfo("Saved",
                            "Listing saved: " + car.year + " " + car.make + " " + car.model)
        self.mediator.notify(self, "show_owner_dash")


# ============================================================
# RenterDashFrame
# ============================================================

class RenterDashFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Nav bar
        nav = tk.Frame(self, bg=NAV_BG)
        nav.pack(fill="x")
        tk.Label(nav, text="DriveShare  —  Browse Cars",
                 font=("Arial", 13, "bold"),
                 bg=NAV_BG, fg=WHITE).pack(side="left", padx=16, pady=10)
        _nav_btn(nav, "Logout",         self._logout)
        _nav_btn(nav, "Notifications",  lambda: self.mediator.notify(self, "show_notifications"))
        _nav_btn(nav, "Rental History", lambda: self.mediator.notify(self, "show_history"))
        _nav_btn(nav, "Messages",       lambda: self.mediator.notify(self, "show_messages"))

        # Welcome + search bar
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=20, pady=10)
        self.info = tk.Label(top, text="", font=("Arial", 11), bg=BG, fg=TEXT)
        self.info.pack(side="left")

        search_bar = tk.Frame(self, bg=WHITE, bd=1, relief="groove")
        search_bar.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(search_bar, text="Filter by location:",
                 font=("Arial", 11), bg=WHITE, fg=MUTED).pack(side="left", padx=12, pady=8)
        self.search_var = tk.StringVar()
        tk.Entry(search_bar, textvariable=self.search_var,
                 font=("Arial", 11), width=22,
                 relief="solid", bd=1).pack(side="left", padx=4, pady=8, ipady=4)
        tk.Button(search_bar, text="Search",
                  font=("Arial", 11), bg=NAV_BG, fg=WHITE, bd=0,
                  padx=12, pady=4, cursor="hand2",
                  command=self.on_show).pack(side="left", padx=6, pady=8)
        tk.Button(search_bar, text="Clear",
                  font=("Arial", 11), bg=BG, fg=NAV_BG, bd=0,
                  padx=8, pady=4, cursor="hand2",
                  command=lambda: [self.search_var.set(""), self.on_show()]).pack(
            side="left", padx=2)

        tk.Label(self, text="Available Cars", font=("Arial", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=20, pady=(4, 4))

        # Scrollable car list
        outer, self.car_frame, _ = _scrollable(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def on_show(self):
        for w in self.car_frame.winfo_children():
            w.destroy()

        user = SessionManager.get_instance().get_current_user()
        self.info.config(text="Welcome, " + user.name +
                              "   |   Balance: $" + str(round(user.balance, 2)))

        query = self.search_var.get().strip().lower()
        results = [c for c in CARS if not query or query in c.location.lower()]

        if not results:
            tk.Label(self.car_frame, text="No cars match your search.",
                     font=("Arial", 11), bg=BG, fg=MUTED).pack(pady=24)
            return

        for car in results:
            card = tk.Frame(self.car_frame, bg=WHITE, bd=1, relief="solid")
            card.pack(fill="x", pady=6, ipady=8)

            # Info left column
            info_col = tk.Frame(card, bg=WHITE)
            info_col.pack(side="left", padx=12, pady=4, fill="x", expand=True)

            avail_color = GREEN if car.available else "#b71c1c"
            avail_text  = "Available" if car.available else "Not Available"

            tk.Label(info_col,
                     text=car.year + " " + car.make + " " + car.model,
                     font=("Arial", 12, "bold"), bg=WHITE, fg=TEXT).pack(anchor="w")
            tk.Label(info_col,
                     text="Location: " + car.location + "   |   Mileage: " + car.mileage,
                     font=("Arial", 10), bg=WHITE, fg=MUTED).pack(anchor="w", pady=1)
            tk.Label(info_col,
                     text="$" + str(car.price_per_day) + "/day   |   " + avail_text,
                     font=("Arial", 10, "bold"), bg=WHITE, fg=avail_color).pack(anchor="w")

            # Buttons right column
            btn_col = tk.Frame(card, bg=WHITE)
            btn_col.pack(side="right", padx=12, pady=4)

            if car.available and (not car.owner or car.owner.email != user.email):
                tk.Button(btn_col, text="Book Now",
                          font=("Arial", 10, "bold"), bg=GREEN, fg=WHITE,
                          bd=0, padx=12, pady=6, cursor="hand2",
                          command=lambda c=car: self.mediator.notify(
                              self, "show_book_car", c)).pack(fill="x", pady=3)

            # Watch - registers an Observer on this car (Pattern 2)
            tk.Button(btn_col, text="Watch",
                      font=("Arial", 10), bg=AMBER, fg=WHITE,
                      bd=0, padx=12, pady=6, cursor="hand2",
                      command=lambda c=car: self._watch(c)).pack(fill="x", pady=3)

            if car.owner and car.owner.email != user.email:
                tk.Button(btn_col, text="Message Owner",
                          font=("Arial", 10), bg="#546e7a", fg=WHITE,
                          bd=0, padx=12, pady=6, cursor="hand2",
                          command=lambda c=car: self.mediator.notify(
                              self, "show_messages", c.owner.email)).pack(fill="x", pady=3)

    def _watch(self, car):
        user = SessionManager.get_instance().get_current_user()
        get_or_create_watcher(user.email, car)
        messagebox.showinfo("Watching",
                            "You are now watching\n" +
                            car.year + " " + car.make + " " + car.model +
                            "\n\nYou will get a notification if it becomes "
                            "available or if the price drops.")

    def _logout(self):
        SessionManager.get_instance().logout()
        self.mediator.notify(self, "show_login")


# ============================================================
# BookCarFrame - uses PaymentProxy (Pattern 5)
# ============================================================

class BookCarFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._car = None
        self._build_ui()

    def set_car(self, car):
        self._car = car
        self._update_display()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Confirm Booking",
                 font=("Arial", 14, "bold"), bg=NAV_BG, fg=WHITE).pack(
            side="left", padx=16, pady=12)
        _nav_btn(hdr, "Cancel",
                 lambda: self.mediator.notify(self, "show_renter_dash"))

        # Centered card
        card = tk.Frame(self, bg=WHITE, bd=1, relief="groove")
        card.place(relx=0.5, rely=0.5, anchor="center", width=480)

        self.car_label = tk.Label(card, text="",
                                  font=("Arial", 13, "bold"), bg=WHITE, fg=TEXT)
        self.car_label.pack(pady=(24, 4), padx=30)

        tk.Frame(card, bg="#e0e0e0", height=1).pack(fill="x", padx=30, pady=8)

        row = tk.Frame(card, bg=WHITE)
        row.pack(pady=10)
        tk.Label(row, text="Number of days:", font=("Arial", 12),
                 bg=WHITE, fg=TEXT).pack(side="left", padx=(0, 12))
        self.days_var = tk.StringVar(value="1")
        tk.Entry(row, textvariable=self.days_var,
                 font=("Arial", 14, "bold"), width=6,
                 relief="solid", bd=1, justify="center").pack(side="left", ipady=6)

        self.total_label = tk.Label(card, text="",
                                    font=("Arial", 13, "bold"), bg=WHITE, fg=GREEN)
        self.total_label.pack(pady=8)

        self.msg = tk.Label(card, text="", font=("Arial", 10),
                            bg=WHITE, fg=RED_FG, wraplength=420)
        self.msg.pack(pady=(0, 8))

        _big_btn(card, "Confirm and Pay", self._book).pack(
            pady=(4, 24), padx=30, fill="x")

        self.days_var.trace_add("write", lambda *_: self._update_display())

    def _update_display(self):
        if self._car:
            self.car_label.config(
                text=self._car.year + " " + self._car.make + " " +
                     self._car.model + "  |  " + self._car.location)
            try:
                days = int(self.days_var.get())
                total = self._car.price_per_day * days
                self.total_label.config(
                    text="Total: $" + str(round(total, 2)) +
                         "   for " + str(days) + " day(s)   @  $" +
                         str(self._car.price_per_day) + "/day")
            except ValueError:
                self.total_label.config(text="")

    def _book(self):
        if not self._car:
            return

        user = SessionManager.get_instance().get_current_user()

        try:
            days = int(self.days_var.get())
            if days <= 0:
                raise ValueError
        except ValueError:
            self.msg.config(text="Enter a valid number of days (whole number, greater than 0).")
            return

        owner = self._car.owner
        if not owner:
            self.msg.config(text="This listing has no owner.")
            return

        amount  = self._car.price_per_day * days
        booking = Booking(self._car, user, days)

        # Send the payment through the Proxy (Pattern 5)
        proxy = PaymentProxy()
        ok, result_msg = proxy.process_payment(amount, user, owner, booking)

        if ok:
            self._car.set_available(False)
            self.msg.config(text="")
            messagebox.showinfo("Booking Confirmed", result_msg)
            self.mediator.notify(self, "show_renter_dash")
        else:
            self.msg.config(text=result_msg, fg=RED_FG)


# ============================================================
# MessagesFrame
# ============================================================

class MessagesFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def set_partner(self, partner_email):
        self.to_var.set(partner_email)
        self._refresh()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Messages",
                 font=("Arial", 14, "bold"), bg=NAV_BG, fg=WHITE).pack(
            side="left", padx=16, pady=12)
        _nav_btn(hdr, "Back", self._back)

        # To field
        to_bar = tk.Frame(self, bg=WHITE, bd=1, relief="groove")
        to_bar.pack(fill="x", padx=20, pady=12)
        tk.Label(to_bar, text="To (email):", font=("Arial", 11),
                 bg=WHITE, fg=TEXT).pack(side="left", padx=12, pady=10)
        self.to_var = tk.StringVar()
        tk.Entry(to_bar, textvariable=self.to_var,
                 font=("Arial", 11), width=30,
                 relief="solid", bd=1).pack(side="left", padx=8, pady=10, ipady=4)
        tk.Button(to_bar, text="Refresh",
                  font=("Arial", 10), bg=BG, fg=NAV_BG, bd=0, padx=10,
                  cursor="hand2", command=self._refresh).pack(side="left", padx=4)

        # Message inbox
        self.inbox = scrolledtext.ScrolledText(
            self, font=("Arial", 10), width=70, height=14,
            state="disabled", relief="groove", bd=1,
            bg="#fafafa")
        self.inbox.pack(padx=20, pady=(0, 8), fill="both", expand=True)

        # Compose row
        compose = tk.Frame(self, bg=BG)
        compose.pack(fill="x", padx=20, pady=(0, 14))
        self.entry = tk.Entry(compose, font=("Arial", 11),
                              relief="solid", bd=1)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        tk.Button(compose, text="Send",
                  font=("Arial", 11, "bold"), bg=NAV_BG, fg=WHITE,
                  bd=0, padx=18, pady=6, cursor="hand2",
                  command=self._send).pack(side="left")

    def on_show(self):
        self._refresh()

    def _refresh(self):
        user = SessionManager.get_instance().get_current_user()
        if not user:
            return
        partner = self.to_var.get().strip().lower()
        self.inbox.config(state="normal")
        self.inbox.delete("1.0", "end")
        for m in MESSAGES:
            if ((m.sender_email == user.email and m.receiver_email == partner) or
                    (m.sender_email == partner and m.receiver_email == user.email)):
                self.inbox.insert("end",
                                  "[" + m.timestamp + "]  " +
                                  m.sender_email + ":  " + m.text + "\n\n")
        self.inbox.config(state="disabled")
        self.inbox.see("end")

    def _send(self):
        user = SessionManager.get_instance().get_current_user()
        to   = self.to_var.get().strip().lower()
        text = self.entry.get().strip()
        if not to or not text:
            return
        if to not in USERS:
            messagebox.showwarning("Not found", "No user with that email.")
            return
        MESSAGES.append(Message(user.email, to, text))
        self.entry.delete(0, "end")
        self._refresh()

    def _back(self):
        user = SessionManager.get_instance().get_current_user()
        if user and user.role in ("owner", "both"):
            self.mediator.notify(self, "show_owner_dash")
        else:
            self.mediator.notify(self, "show_renter_dash")


# ============================================================
# HistoryFrame
# ============================================================

class HistoryFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="My Rental History",
                 font=("Arial", 14, "bold"), bg=NAV_BG, fg=WHITE).pack(
            side="left", padx=16, pady=12)
        _nav_btn(hdr, "Back",
                 lambda: self.mediator.notify(self, "show_renter_dash"))

        tk.Label(self, text="All cars you have booked and paid for.",
                 font=("Arial", 11), bg=BG, fg=MUTED).pack(
            anchor="w", padx=20, pady=(12, 6))

        outer, self.list_frame, _ = _scrollable(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def on_show(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        user = SessionManager.get_instance().get_current_user()
        history = user.rental_history if user else []
        if not history:
            tk.Label(self.list_frame, text="No rental history yet.",
                     font=("Arial", 11), bg=BG, fg=MUTED).pack(pady=24)
            return
        for b in reversed(history):
            card = tk.Frame(self.list_frame, bg=WHITE, bd=1, relief="solid")
            card.pack(fill="x", pady=5, ipady=10)
            tk.Label(card, text=str(b),
                     font=("Arial", 11), bg=WHITE, fg=TEXT,
                     anchor="w").pack(fill="x", padx=14)


# ============================================================
# NotificationsFrame
# ============================================================
# Shows Observer notifications (Pattern 2). These are filled
# by RenterWatcher.update() when CarListing calls notify_observers().

class NotificationsFrame(BaseFrame):

    def __init__(self, parent, mediator):
        super().__init__(parent, mediator)
        self._build_ui()

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=NAV_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="My Notifications",
                 font=("Arial", 14, "bold"), bg=NAV_BG, fg=WHITE).pack(
            side="left", padx=16, pady=12)
        _nav_btn(hdr, "Back",
                 lambda: self.mediator.notify(self, "show_renter_dash"))

        tk.Label(self,
                 text="You get a notification here when a car you are watching "
                      "becomes available or when the price drops.",
                 font=("Arial", 11), bg=BG, fg=MUTED,
                 wraplength=700, justify="left").pack(
            anchor="w", padx=20, pady=(12, 6))

        outer, self.list_frame, _ = _scrollable(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def on_show(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        user = SessionManager.get_instance().get_current_user()
        notes = NOTIFICATIONS.get(user.email, []) if user else []
        if not notes:
            tk.Label(self.list_frame, text="No notifications yet.",
                     font=("Arial", 11), bg=BG, fg=MUTED).pack(pady=24)
            return
        for note in reversed(notes):
            card = tk.Frame(self.list_frame, bg="#fffde7", bd=1, relief="solid")
            card.pack(fill="x", pady=5, ipady=10)
            tk.Label(card, text=note,
                     font=("Arial", 11), bg="#fffde7", fg=TEXT,
                     anchor="w").pack(fill="x", padx=14)


# ============================================================
# Demo data and main
# ============================================================

def load_demo_data():
    # Two demo accounts so the app can be shown without registering.
    # Demo owner: owner@demo.com / pass123
    # Demo renter: renter@demo.com / pass123
    # Security answers for owner: rex / detroit / smith
    # Security answers for renter: milo / chicago / jones

    q = RegisterFrame.QUESTIONS

    owner = User("owner@demo.com", "pass123", "Alex Owner", "owner",
                 q[0], "rex", q[1], "detroit", q[2], "smith")
    USERS["owner@demo.com"] = owner
    NOTIFICATIONS["owner@demo.com"] = []

    renter = User("renter@demo.com", "pass123", "Sara Renter", "renter",
                  q[0], "milo", q[1], "chicago", q[2], "jones")
    USERS["renter@demo.com"] = renter
    NOTIFICATIONS["renter@demo.com"] = []

    # Two demo cars built with CarListingBuilder (Pattern 4)
    b = CarListingBuilder()

    b.set_owner(owner).set_make("Toyota").set_model("Camry").set_year("2021")
    b.set_mileage("32,000 mi").set_location("Detroit, MI").set_price(55.00)
    CARS.append(b.build())

    b.set_owner(owner).set_make("Honda").set_model("Civic").set_year("2020")
    b.set_mileage("45,000 mi").set_location("Ann Arbor, MI").set_price(45.00)
    CARS.append(b.build())


def main():
    root = tk.Tk()
    root.title("DriveShare - Peer-to-Peer Car Rental")
    root.geometry("920x680")
    root.minsize(860, 620)
    root.configure(bg=BG)
    root.resizable(True, True)

    mediator = AppMediator(root)

    login_frame    = LoginFrame(root, mediator)
    register_frame = RegisterFrame(root, mediator)
    forgot_frame   = ForgotPasswordFrame(root, mediator)
    owner_dash     = OwnerDashFrame(root, mediator)
    add_car_frame  = AddCarFrame(root, mediator)
    renter_dash    = RenterDashFrame(root, mediator)
    book_car_frame = BookCarFrame(root, mediator)
    msg_frame      = MessagesFrame(root, mediator)
    history_frame  = HistoryFrame(root, mediator)
    notif_frame    = NotificationsFrame(root, mediator)

    mediator.register_frame("login",         login_frame)
    mediator.register_frame("register",      register_frame)
    mediator.register_frame("forgot",        forgot_frame)
    mediator.register_frame("owner_dash",    owner_dash)
    mediator.register_frame("add_car",       add_car_frame)
    mediator.register_frame("renter_dash",   renter_dash)
    mediator.register_frame("book_car",      book_car_frame)
    mediator.register_frame("messages",      msg_frame)
    mediator.register_frame("history",       history_frame)
    mediator.register_frame("notifications", notif_frame)

    load_demo_data()
    mediator.show_frame("login")
    root.mainloop()


if __name__ == "__main__":
    main()
