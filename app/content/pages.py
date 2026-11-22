"""Starting text for the About and policy pages. Seeded once; after that they're edited in
Admin > Content > Pages & policies (re-seeding never overwrites an existing page).

These are drafts written for BazaarE' (ships from Long Island, NY, within the US). The shop
owner should review them, ideally with a lawyer, before launch.
"""

SUPPORT = "support@bazaare.com"

ABOUT = """
<p>BazaarE' is a small jewellery boutique from Long Island, New York, rooted in Indian craft and culture.
We bring you jhumkas, chandbalis, haslis, kadas and statement pieces, chosen for their craftsmanship,
their materials and the stories behind them.</p>
<p>Many of our pieces are handmade by independent artisans, so no two are ever exactly alike. We tell you
what every piece is made of, check each one before it ships, and wrap it with care, so it arrives ready to
wear or to give.</p>
<h2>Questions?</h2>
<p>We'd love to hear from you: write to <a href="mailto:{support}">{support}</a>.</p>
"""

SHIPPING = """
<h2>Where we ship</h2>
<p>We ship from Long Island, New York, to addresses in the United States. We don't ship internationally yet.</p>
<h2>Shipping options</h2>
<ul>
<li><strong>Standard</strong>: 3–5 business days, $5.99. Free on orders over the amount shown in your bag.</li>
<li><strong>Express</strong>: 1–2 business days, $14.99.</li>
</ul>
<p>Delivery times are counted in business days (Monday to Friday, excluding public holidays) from the day
your order is placed. You'll see estimated delivery dates at checkout and in your order confirmation.</p>
<h2>Processing</h2>
<p>We check, pack and dispatch orders within 1–2 business days. For some local orders we may deliver by hand;
we'll let you know if so.</p>
<h2>Tracking</h2>
<p>When your order ships we email you the carrier and tracking number, with a link to follow your parcel. You
can also see your order's status under <a href="/customer/orders">Your orders</a> if you have an account.</p>
<h2>Sales tax</h2>
<p>Orders delivered in New York State include New York sales tax at the rate for the delivery address, on the
items and on shipping. Tax is shown at checkout before you place your order.</p>
<h2>Lost or damaged parcels</h2>
<p>If your parcel hasn't arrived by the latest estimated date, or arrives damaged, email us at
<a href="mailto:{support}">{support}</a> with your order number (and photos for damage) within 48 hours of
delivery, and we'll make it right.</p>
"""

RETURNS = """
<p>We want you to love your jewellery. If something isn't right, we're happy to help with a return or an exchange.</p>
<h2>Returns</h2>
<ul>
<li>You can return items within <strong>14 days of delivery</strong>.</li>
<li>Items must be unworn, undamaged and in their original packaging, with any tags attached.</li>
<li>For hygiene reasons, <strong>earrings can't be returned</strong> unless they arrive faulty or not as described.</li>
<li>Gift cards and items marked as final sale can't be returned.</li>
</ul>
<h2>Exchanges</h2>
<p>Would you prefer a different design or size? We'll exchange it for an item of the same price, subject to
availability. If the new item costs more or less, we'll settle the difference.</p>
<h2>How to start a return or exchange</h2>
<ol>
<li>Email <a href="mailto:{support}">{support}</a> within 14 days of delivery with your order number and the
items you'd like to return or exchange.</li>
<li>We'll reply with the return address and instructions.</li>
<li>Pack the items securely in their original packaging and send them back. Please use a tracked service;
we can't be responsible for parcels lost on the way back to us.</li>
</ol>
<h2>Return shipping</h2>
<p>Return shipping is paid by you, unless the item arrived faulty, damaged or not what you ordered. In that case
we cover it.</p>
<h2>Refunds</h2>
<p>Once we receive and check your return, we'll refund the item price within 5 business days. Original
shipping charges aren't refunded unless the item was faulty or sent in error. For cash-on-delivery orders we'll
agree the refund method with you by email.</p>
<h2>Faulty or damaged items</h2>
<p>Handmade pieces can have small variations; that's part of their charm. If a piece arrives broken, faulty or
not as described, email us with photos within 48 hours of delivery and we'll repair, replace or refund it.</p>
"""

PRIVACY = """
<p>This policy explains what personal information BazaarE' collects, how we use it and the choices you have.</p>
<h2>What we collect</h2>
<ul>
<li><strong>Order details</strong>: your name, shipping and billing addresses, email address and phone number,
and what you buy.</li>
<li><strong>Account details</strong> (if you create an account): your name, email, a securely scrambled
(hashed) password, your saved addresses and your email/text preferences.</li>
<li><strong>Basic technical information</strong>: cookies that keep you signed in and remember your bag and
wishlist, and standard server logs.</li>
</ul>
<h2>How we use it</h2>
<ul>
<li>To process, deliver and support your orders, including order and shipping emails.</li>
<li>To run your account and remember your bag and wishlist.</li>
<li>To send news and offers, only if you choose to receive them (you can switch this off at any time in your account).</li>
<li>To prevent fraud, keep the shop secure and meet our legal and tax obligations.</li>
</ul>
<h2>Who we share it with</h2>
<p>We never sell your personal information. We share only what's needed with the services that help us run the
shop: our website host, Cloudflare (which stores and serves product photos), our email provider, payment
providers and delivery carriers. They may only use it to provide their service to us.</p>
<h2>Cookies</h2>
<p>We use essential cookies to keep you signed in and to remember your bag, checkout progress and wishlist. We
don't use advertising cookies. If we add analytics in the future, we'll update this policy.</p>
<h2>How long we keep it</h2>
<p>We keep order records for as long as needed for accounting and tax purposes (usually up to seven years) and
account details until you ask us to delete your account.</p>
<h2>Your choices and rights</h2>
<p>You can see and update your details and email preferences in your account. You can ask us to send you a copy
of your information, correct it, or delete your account by writing to <a href="mailto:{support}">{support}</a>.
We'll respond within 30 days.</p>
<h2>Children</h2>
<p>Our shop isn't directed at children under 13, and we don't knowingly collect their information.</p>
<h2>Changes</h2>
<p>We may update this policy from time to time. The date at the top shows when it last changed.</p>
<h2>Contact</h2>
<p>Questions about privacy? Write to <a href="mailto:{support}">{support}</a>.</p>
"""

TERMS = """
<p>These terms apply when you use the BazaarE' website and buy from us. By placing an order you agree to them.</p>
<h2>About us</h2>
<p>BazaarE' is an online jewellery shop based on Long Island, New York, USA. You can reach us at
<a href="mailto:{support}">{support}</a>.</p>
<h2>Our products</h2>
<p>Many pieces are handmade, so small differences in shape, colour and finish are natural and not defects. We
describe materials as accurately as we can; colours may look slightly different on different screens.</p>
<h2>Prices and availability</h2>
<p>Prices are in US dollars and don't include sales tax or shipping, which are shown at checkout. Items are
subject to availability. If a price is clearly wrong or an item is no longer available, we'll contact you and
may cancel the order, with a full refund of anything you've paid.</p>
<h2>Orders</h2>
<p>Your order is an offer to buy. We accept it when we send your order confirmation email. We may decline or
cancel an order, for example if we suspect fraud or can't deliver to the address.</p>
<h2>Payment</h2>
<p>Payment methods are shown at checkout. For cash on delivery, please have the exact order total ready when your
order arrives.</p>
<h2>Coupon codes</h2>
<p>Coupon codes are subject to their stated conditions (such as minimum spend, dates and number of uses), can't
be exchanged for cash and may be withdrawn at any time. One code per order.</p>
<h2>Shipping, returns and exchanges</h2>
<p>See our <a href="/policies/shipping">Shipping policy</a> and <a href="/policies/returns">Returns &amp;
exchanges</a>. Risk in the items passes to you when they're delivered.</p>
<h2>Your account</h2>
<p>Keep your password private; you're responsible for activity on your account. Tell us straight away if you
think someone else has used it.</p>
<h2>Our content</h2>
<p>Photos, text and designs on this website belong to BazaarE' or its artisans and may not be copied without permission.</p>
<h2>Liability</h2>
<p>We aren't liable for losses that weren't foreseeable, or for indirect losses. Nothing in these terms limits
rights you have by law as a consumer.</p>
<h2>Governing law</h2>
<p>These terms are governed by the laws of the State of New York, USA.</p>
<h2>Changes</h2>
<p>We may update these terms; the version on the website when you place your order applies to that order.</p>
"""

PAGES = [
    {
        "slug": "about",
        "title": "About BazaarE'",
        "summary": "Handcrafted jewellery rooted in Indian craft and culture, from Long Island, New York.",
        "body": ABOUT,
        "position": 0,
    },
    {
        "slug": "shipping",
        "title": "Shipping",
        "summary": "Where we ship, how long it takes and what it costs.",
        "body": SHIPPING,
        "position": 10,
    },
    {
        "slug": "returns",
        "title": "Returns & exchanges",
        "summary": "Changed your mind? Returns within 14 days, plus easy exchanges.",
        "body": RETURNS,
        "position": 20,
    },
    {
        "slug": "privacy",
        "title": "Privacy policy",
        "summary": "What we collect, why, and the choices you have.",
        "body": PRIVACY,
        "position": 30,
    },
    {
        "slug": "terms",
        "title": "Terms & conditions",
        "summary": "The terms that apply when you shop with BazaarE'.",
        "body": TERMS,
        "position": 40,
    },
]


def seed_pages(db, Page):
    """Create any missing page from PAGES. Existing pages (possibly edited) are left alone."""
    added = 0
    for spec in PAGES:
        if db.session.query(Page).filter_by(slug=spec["slug"]).first() is None:
            body = " ".join(spec["body"].split()).replace("{support}", SUPPORT)
            db.session.add(Page(**{**spec, "body": body}))
            added += 1
    if added:
        db.session.commit()
    return added
