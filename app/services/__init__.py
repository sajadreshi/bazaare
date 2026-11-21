"""Business logic for the shop: carts, checkout, payments and orders.

Routes stay thin: they read the request, call a service function and render
a template with the model objects it returns. Services own the database
writes and commit (or roll back) their own transactions.
"""
