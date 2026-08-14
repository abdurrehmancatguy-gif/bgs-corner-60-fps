#!/usr/bin/env python3
"""Generate the footer legal dialog markup and splice it into index.html."""
import html
import re
from pathlib import Path

PAGE = Path("/Users/ajoomama/github/corner-60-fps/index.html")
EMAIL = "info@bgscorner.com"
PHONE = "+971 56 489 1974"

TERMS = [
    (None, ['Welcome to the website of B G S Corner General Trading L.L.C. ("Company," "we," '
            '"us," or "our"). By accessing or using our website and purchasing our products, you '
            'agree to be bound by these Terms & Conditions ("Terms"). Please read them carefully.']),
    ("1. Company Information", [
        "Legal Name: B G S Corner General Trading L.L.C.",
        f"Email: {EMAIL}",
        f"Phone: {PHONE}"]),
    ("2. Eligibility", [
        "By using this website, you represent that you are at least 18 years of age and have the "
        "legal capacity to enter into a binding contract."]),
    ("3. Account & Security", [
        "You may be required to create an account. You are responsible for maintaining the "
        "confidentiality of your login details and for all activity under your account. Notify us "
        f"immediately at {EMAIL} if you suspect any unauthorized use."]),
    ("4. Products & Pricing", [
        "We strive to display product colors, descriptions, and images accurately, but cannot "
        "guarantee exact representation on your screen. All prices are subject to change without "
        "notice. We reserve the right to modify or discontinue any product at any time. In the "
        "event of a pricing error, we may cancel affected orders and will notify you accordingly, "
        "with a full refund if payment has been made."]),
    ("5. Orders & Payment", [
        "Placing an order constitutes an offer to purchase. We reserve the right to accept or "
        "decline any order for reasons including product availability, suspicion of fraud, or "
        "pricing errors. Payment must be made in full at checkout using our accepted methods. "
        "Order confirmation does not signify final acceptance – the contract is formed upon "
        "shipment."]),
    ("6. Shipping & Delivery", [
        "We ship to the locations specified on our website. Delivery timelines are estimates and "
        "may be affected by factors beyond our control. Risk of loss and title pass to you upon "
        "delivery to the carrier. Any delivery damage must be reported within 48 hours with "
        "photographic evidence. Shipping charges and any applicable customs duties are your "
        "responsibility unless stated otherwise."]),
    ("7. Returns & Refunds", [
        "Our return policy allows returns within [7/14/30] days of delivery for eligible products "
        "that are unused, in original packaging, and accompanied by proof of purchase. To initiate "
        f"a return, contact us at {EMAIL} or call {PHONE}. Refunds are processed to the original "
        "payment method within 14 business days after we receive and inspect the returned item. "
        "Shipping costs are non-refundable, and return shipping is at your expense unless the "
        "product is defective or we made an error."]),
    ("8. Intellectual Property", [
        "All content on the website – including logos, trademarks, text, graphics, images, and "
        "software – is the exclusive property of B G S Corner General Trading L.L.C. or its "
        "licensors and is protected by UAE and international copyright and trademark laws. No "
        "content may be reproduced or used for commercial purposes without our prior written "
        "consent."]),
    ("9. User Conduct", [
        "You agree not to use the website for any unlawful purpose, upload viruses or malicious "
        "code, or disrupt the website’s functioning. You also agree not to violate the "
        "intellectual property or privacy rights of others."]),
    ("10. Limitation of Liability", [
        "To the fullest extent permitted by law, B G S Corner General Trading L.L.C. shall not be "
        "liable for any indirect, incidental, special, or consequential damages arising from your "
        "use of the website or purchase of products. Our total liability for any claim related to "
        "a product shall not exceed the purchase price of that product."]),
    ("11. Indemnification", [
        "You agree to indemnify and hold harmless B G S Corner General Trading L.L.C., its "
        "officers, directors, and employees from any claims, losses, or damages (including legal "
        "fees) arising out of your violation of these Terms or misuse of the website."]),
    ("12. Governing Law & Dispute Resolution", [
        "These Terms are governed by the laws of the United Arab Emirates. Any dispute shall first "
        "be attempted to be resolved amicably. If unresolved, it shall be subject to the exclusive "
        "jurisdiction of the competent courts in the relevant Emirate."]),
    ("13. Changes to Terms", [
        "We may update these Terms at any time. Changes will be posted on this page, and your "
        "continued use of the website constitutes acceptance of the modified Terms."]),
    ("14. Contact Us", [
        "For any questions about these Terms, please contact:",
        f"Email: {EMAIL}",
        f"Phone: {PHONE}"]),
]

PRIVACY = [
    (None, ['B G S Corner General Trading L.L.C. ("we," "us," or "our") is committed to protecting '
            "your personal data and respecting your privacy. This Privacy Policy explains how we "
            "collect, use, disclose, and safeguard your information when you visit our website or "
            "engage with our services."]),
    ("1. Information We Collect", [
        "We may collect the following types of personal data:",
        ["Contact & Identity Data: Full name, email address, phone number, delivery/billing address.",
         "Transaction Data: Products purchased, payment method details (we do not store full credit "
         "card numbers; payment processing is handled by a secure PCI-compliant gateway), order history.",
         "Technical Data: IP address, browser type, device type, operating system, referring/exit "
         "pages, and clickstream data collected via cookies and similar technologies.",
         "Communication Data: Any information you provide when contacting us via email, phone, or "
         "contact forms."]]),
    ("2. How We Collect Information", [
        "We collect information:",
        ["Directly from you when you place an order, create an account, subscribe to newsletters, "
         "or contact us.",
         "Automatically as you navigate the website (through cookies, server logs, and analytics tools).",
         "From third-party service providers (e.g., payment processors, delivery partners) that "
         "help us fulfill orders."]]),
    ("3. How We Use Your Information", [
        "We use your personal data only for purposes necessary to provide our services and improve "
        "your experience:",
        ["To process, fulfill, and ship your orders, and communicate order status.",
         "To handle returns, refunds, and customer support requests.",
         "To send transactional emails (order confirmations, invoices) and, with your consent, "
         "marketing communications. You can opt out of marketing at any time.",
         "To analyze website usage and improve our product offerings, user interface, and security.",
         "To comply with legal obligations and prevent fraud."]]),
    ("4. Legal Basis for Processing", [
        "We process your personal data based on:",
        ["Contractual necessity: to perform a contract with you (e.g., delivering products).",
         "Legitimate interests: to improve our business, secure our website, and provide effective "
         "customer service.",
         "Legal obligation: to meet regulatory requirements under UAE law.",
         "Consent: for optional activities like marketing newsletters (you may withdraw consent at "
         "any time)."]]),
    ("5. Cookies & Tracking Technologies", [
        "Our website uses cookies and similar technologies. Essential cookies are required for "
        "basic site operations (shopping cart, secure login). Analytical/performance cookies help "
        "us understand visitor behavior anonymously. You can control cookie preferences through "
        "your browser settings; however, disabling cookies may affect website functionality."]),
    ("6. Data Sharing & Disclosure", [
        "We do not sell, trade, or rent your personal data. We may share information with:",
        ["Service Providers: Trusted partners assisting in website hosting, payment processing, "
         "order delivery, email distribution, and analytics, bound by data protection obligations.",
         "Legal & Regulatory Authorities: If required by law, court order, or to protect our "
         "rights, property, or safety."]]),
    ("7. Data Transfer & Storage", [
        "Your data is stored on secure servers, which may be located inside or outside the UAE. "
        "Where transfers occur, we ensure appropriate safeguards are in place to keep your data "
        "secure and in compliance with this policy."]),
    ("8. Data Security", [
        "We implement commercially reasonable technical and organizational measures – including "
        "encryption, firewalls, and SSL technology – to protect your personal information. No "
        "method of transmission over the Internet is 100% secure; we cannot guarantee absolute "
        "security."]),
    ("9. Data Retention", [
        "We retain your personal data only as long as necessary to fulfill the purposes outlined "
        "herein or as required by applicable law. Transaction records may be kept for tax and "
        "commercial compliance periods, after which data is securely deleted or anonymized."]),
    ("10. Your Rights", [
        "Subject to legal limitations, you may have the right to:",
        ["Access the personal data we hold about you.",
         "Request correction of inaccurate or incomplete data.",
         "Request erasure of your data in certain circumstances.",
         "Object to or restrict processing based on legitimate interests.",
         "Withdraw consent for marketing communications at any time.",
         "Request a copy of your data in a structured machine-readable format."],
        f"To exercise any of these rights, contact us at {EMAIL} or call {PHONE}. We will respond "
        "within a reasonable timeframe."]),
    ("11. Third-Party Links", [
        "Our website may contain links to external websites not operated by us. We are not "
        "responsible for their privacy practices and encourage you to review their policies "
        "separately."]),
    ("12. Children’s Privacy", [
        "Our website is not directed to individuals under 18. We do not knowingly collect personal "
        "data from minors. If we become aware that a child has provided personal data, we will "
        "promptly delete it."]),
    ("13. Changes to This Privacy Policy", [
        "We may update this policy from time to time. Changes will be posted on this page, and "
        "material changes may be communicated via email or a website notice."]),
    ("14. Contact Us", [
        "For any questions or concerns about our privacy practices:",
        f"Email: {EMAIL}",
        f"Phone: {PHONE}"]),
]

# Drawn only from the documents above plus the address already on the site.
LEGAL = [
    (None, ["The website is operated by B G S Corner General Trading L.L.C., a company registered "
            "in Dubai, United Arab Emirates."]),
    ("Company", [
        "Legal Name: B G S Corner General Trading L.L.C.",
        "4th & 17th Street Corner, Riggat Al Buteen, near Deira Clock Tower, Dubai, "
        "United Arab Emirates",
        f"Email: {EMAIL}",
        f"Phone: {PHONE}"]),
    ("Intellectual Property", [
        "All content on this website – including logos, trademarks, text, graphics, images, and "
        "software – is the exclusive property of B G S Corner General Trading L.L.C. or its "
        "licensors and is protected by UAE and international copyright and trademark laws. No "
        "content may be reproduced or used for commercial purposes without our prior written "
        "consent."]),
    ("Governing Law", [
        "These terms and any dispute arising from use of this website are governed by the laws of "
        "the United Arab Emirates, subject to the exclusive jurisdiction of the competent courts "
        "in the relevant Emirate."]),
    ("Documents", [
        "See also the Terms & Conditions and the Privacy Policy, available from the footer of "
        "every page."]),
]


def render(blocks, indent="        "):
    out = []
    for heading, body in blocks:
        if heading:
            out.append(f"{indent}<h4>{html.escape(heading)}</h4>")
        for item in body:
            if isinstance(item, list):
                out.append(f"{indent}<ul>")
                for li in item:
                    out.append(f"{indent}  <li>{html.escape(li)}</li>")
                out.append(f"{indent}</ul>")
            else:
                out.append(f"{indent}<p>{html.escape(item)}</p>")
    return "\n".join(out)


def main() -> None:
    h = PAGE.read_text()

    panes = [("terms", "Terms &amp; Conditions", TERMS),
             ("privacy", "Privacy Policy", PRIVACY),
             ("legal", "Legal", LEGAL)]

    body = []
    for slug, title, blocks in panes:
        body.append(f'      <section class="legal-pane" id="legal-{slug}" hidden>')
        body.append(f'        <h3 class="legal-heading">{title}</h3>')
        body.append(render(blocks))
        body.append("      </section>")

    dialog = (
        "\n  <!-- ══════════════════ LEGAL DIALOG ══════════════════ -->\n"
        '  <dialog class="legal" id="legal" aria-labelledby="legal-title">\n'
        '    <div class="legal-inner">\n'
        '      <div class="legal-bar">\n'
        '        <span class="legal-title" id="legal-title">Legal</span>\n'
        '        <button class="legal-close" type="button" aria-label="Close">&#215;</button>\n'
        "      </div>\n"
        '      <div class="legal-body">\n'
        + "\n".join(body) + "\n"
        "      </div>\n"
        "    </div>\n"
        "  </dialog>\n"
    )

    marker = re.search(r'\n  <script src="main\.js\?v=\d+"></script>', h)
    assert marker, "script tag not found"
    h = h[:marker.start()] + dialog + h[marker.start():]

    # footer: drop the strapline, add the three links
    old_fine = ("    <span class=\"footer-fine\">&copy; 2026 BGS CORNER "
                "&mdash; Maison de l'Oud, Duba&iuml;.</span>")
    assert h.count(old_fine) == 1, "footer fine print not matched"
    new_fine = (
        '    <div class="footer-legal">\n'
        '      <span class="footer-fine">&copy; 2026 BGS CORNER</span>\n'
        '      <nav class="legal-links" aria-label="Legal">\n'
        '        <button type="button" data-legal="terms">Terms</button>\n'
        '        <button type="button" data-legal="privacy">Privacy Policy</button>\n'
        '        <button type="button" data-legal="legal">Legal</button>\n'
        "      </nav>\n"
        "    </div>"
    )
    h = h.replace(old_fine, new_fine)

    # the phone number is public in these documents, so the WhatsApp link and the
    # footer can both use it
    h = h.replace("https://wa.me/971000000000", "https://wa.me/971564891974")
    h = h.replace("        <!-- TODO: replace 971000000000 with the house WhatsApp number -->\n", "")
    h = h.replace("        <p>info@bgscorner.com</p>",
                  "        <p>info@bgscorner.com<br>+971 56 489 1974</p>")

    h = re.sub(r'styles\.css\?v=\d+', 'styles.css?v=32', h)
    h = re.sub(r'main\.js\?v=\d+', 'main.js?v=32', h)
    PAGE.write_text(h)
    print("legal dialog inserted; footer links added; phone wired")


if __name__ == "__main__":
    main()
