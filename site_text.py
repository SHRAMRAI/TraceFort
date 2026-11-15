"""Words for TraceFort's info and legal pages. Edit the text here; app.py only displays it.

Not reviewed by a lawyer. Have one review TERMS and PRIVACY before any real launch.
"""

UPDATED = "November 14, 2026"   # change with accounts.TERMS_VERSION when the Terms or Privacy change

ABOUT = """
**TraceFort helps first-time buyers in Dallas–Fort Worth and Houston walk into a foreclosure auction knowing the most they should bid.**

### Why we built it
Auctions move fast. Experienced investors arrive with numbers; first-time buyers often overpay or give up.
TraceFort gives everyone the same head start: a clear walk-away bid, worked out before the auction begins.

### What it does
1. You answer seven quick questions about your budget and what you need.
2. We check every home in our list against your answers.
3. You get your best three homes, each with a walk-away bid, a repair estimate, a risk level, a map and a checklist.

### What's real and what's a sample
- **Real:** home values by ZIP code and bedroom count (Zillow Home Value Index, September 2026), ZIP code
  locations (U.S. Census) and Walmart and Costco locations (OpenStreetMap).
- **Sample:** the 2,270 homes themselves (1,227 across 171 ZIP codes in 61 DFW cities, 1,043 across 149 ZIP
  codes in 37 Houston-area cities) and their auction
  details (addresses, opening bids, auction dates).
  Real auction data isn't public, so these are made up for the demo.

### Who we are
TraceFort is a student project built at HackUTA 2026 for the Xome challenge by
[Shramika Rai](https://github.com/SHRAMRAI), [Prajita Gyawali](https://github.com/gyawaliprajita50) and
[Prashna Pandey](https://github.com/forbidynaliew). The code is on
[GitHub](https://github.com/SHRAMRAI/TraceFort).
It is not affiliated with or endorsed by Xome.
"""

HOW = """
### What is a walk-away bid?
It's the most you should bid on a home. Auctions move fast and it's easy to keep raising your hand.
Decide your number before the auction starts, and stop when bidding passes it.

### How we work it out
We start from what the home is worth once it's fixed, keep a safety cushion for your goal and risk level,
then subtract the repairs. Fixing up to resell keeps a 30% cushion, the "70% rule" many investors use.

Winning costs more than the bid: Xome usually adds a buyer's premium (often 5% of the bid or $2,500, whichever
is more; check each listing's terms) and you pay about 2% in closing costs. Your walk-away bid leaves room for both, so the bid, the fees and the
repairs together never go over your budget.

Repairs often cost more than planned, so we add a buffer: 10% more, or 25% if nobody has seen inside the home.
Even at your walk-away bid, everything together never costs more than the home is worth.

### Where the numbers come from
Home values come from Zillow's home value index for each ZIP code and bedroom count (September 2026).
Store locations come from OpenStreetMap. The homes and their auction details are samples, because real auction
data isn't public.

### What it isn't
Every number is an estimate for education. It isn't an appraisal, financial advice or a brokerage service.
Signing up for auctions, deposits and bidding all happen on Xome's own site.
"""

TERMS = f"""
*Last updated {UPDATED}*

TraceFort is a student project built at HackUTA 2026. By creating an account or using TraceFort, you agree to
these terms. If you don't agree, please don't use TraceFort.

### 1. Who can use TraceFort
You must be 18 or older.

### 2. What TraceFort is
TraceFort gives educational estimates to help you think about foreclosure auction homes in Dallas–Fort Worth and Houston, Texas.
Walk-away bids, home values, repair costs, risk scores and profits come from simple formulas.
**They are not an appraisal, not financial, legal or tax advice, and not a real estate brokerage service.**
Talk to a licensed professional before you bid on or buy a home.
Answers from Ask TraceFort, our AI helper, can be wrong or incomplete; check anything important yourself.

### 3. Sample data
The homes shown are samples for demonstration. Their addresses and auction details are made up; home values are
based on public ZIP-code data. Don't rely on them for a real purchase.

### 4. Not affiliated with Xome
TraceFort was built for the HackUTA 2026 Xome challenge. It is not affiliated with or endorsed by Xome.
Registration, deposits and bidding happen on Xome's own site, under Xome's own terms.

### 5. Your account
Choose a 4-digit PIN you don't use anywhere else, and keep it private. You're responsible for what happens under
your account. You can delete your account at any time from the Account page.

### 6. Fair use
Don't try to break into, overload or copy TraceFort in bulk, and don't use it to break the law or harm others.
We may remove accounts that do.

### 7. Credits
Home values: Zillow Home Value Index (Zillow Research). Map data © OpenStreetMap contributors. Map tiles © CARTO.

### 8. No warranty
TraceFort is provided "as is", without warranties of any kind. Estimates may be wrong or out of date.

### 9. Limits on liability
To the fullest extent the law allows, the TraceFort team isn't liable for any loss or damage from using TraceFort,
including losses from bids or purchases.

### 10. Changes
We may update these terms. The date at the top shows the current version. If we make a significant change,
we'll ask you to agree again.

### 11. Governing law
These terms are governed by the laws of the State of Texas.

### 12. Contact
Questions? Use the Contact page.
"""

PRIVACY = f"""
*Last updated {UPDATED}*

**In short:** we collect as little as we can: a first name, a scrambled PIN and your home preferences.
We don't sell or share your data or show ads, and TraceFort's own code doesn't track you. Our free host,
Streamlit Community Cloud, runs its own analytics on this site; see "Our host" below.

### What we collect
- **A first name** you choose. A nickname is fine.
- **Your 4-digit PIN**, stored only as a one-way scrambled code (a salted hash). We can't read it.
- **Your answers and preferences:** budget, goal, bedrooms, drive time, repairs and risk.
- **Your work ZIP code, only if you type one.** We use it to work out drive times. You can skip it.
- **When you agreed** to the Terms and this policy, and which version.
- **Sign-in attempts:** if a PIN is entered wrong 5 times in a row, we pause sign-in for that name for 15 minutes.
- **Cookies** that keep you signed in and remember the cookie notice. See the Cookie Policy.
- **Messages** you send us through the Contact page.

### What we don't collect
- **We never track your location.** No GPS, no location from your browser, no location from your IP address.
  If you give us a work ZIP code, that ZIP is all we keep.
- No email, phone number, home address, ID, bank or payment details.
- TraceFort's own code adds no analytics, advertising or tracking. Our host adds its own; see "Our host" below.

### How we use it
To show homes that fit you, remember your preferences, keep you signed in, protect your account from
guessing, and reply to your messages.

### Ask TraceFort (AI chat)
When you use Ask TraceFort, your questions, your preferences and your top 3 sample homes are sent to
Anthropic, the company that makes the Claude AI, so it can write an answer. TraceFort doesn't save your chats:
they disappear when you leave or clear the chat. Anthropic handles that data under its own commercial terms and
privacy policy. Please don't type personal details into the chat. AI answers can be wrong; they're
educational estimates, not advice.

### Where it's stored and who sees it
Your account and messages are stored in a database on the TraceFort server. Your browser holds only a random
sign-in code. Contact messages are read only by the TraceFort team, in a PIN-protected inbox.
We don't sell or share your personal data. The map loads tiles from CARTO and the fonts load from Google Fonts;
like any website, those services see your device's IP address.

### Our host (Streamlit Community Cloud)
TraceFort runs on Streamlit Community Cloud, a free hosting service owned by Snowflake. The page that holds
TraceFort loads Snowflake's own analytics and monitoring tools (including Google Analytics, Segment, Heap and
Datadog), and they set their own cookies in your browser. We didn't add these tools, can't turn them off on this
free host, and never see what they collect. Snowflake handles that data under its own privacy notice:
[streamlit.io/privacy-policy](https://streamlit.io/privacy-policy). To block them, use your browser's tracking
protection or a content blocker.

### How long we keep it
Until you delete your account. Signing out removes this device's sign-in right away.
Contact messages are kept until the team deletes them.

### Your choices
- **See your data:** Account → Download my data.
- **Change it:** My preferences.
- **Delete it:** Account → Delete my account. This removes your name, PIN and preferences everywhere.
- **Anything else:** use the Contact page.

### Cookies
We use a few small cookies to keep you signed in, remember the cookie notice and protect forms.
None of TraceFort's own cookies are for advertising or tracking. Our host sets its own analytics cookies.
Details are in the Cookie Policy.

### Children
TraceFort is for people 18 and older. We don't knowingly collect data from anyone younger.

### Security
Your PIN is stored as a salted hash, never as plain text. This is a demo, so please don't reuse a PIN you use
anywhere else.

### Changes
If we change this policy, we'll update the date at the top. For significant changes, we'll ask you to agree again.
"""

COOKIES = f"""
*Last updated {UPDATED}*

A cookie is a small text file a website saves in your browser. TraceFort's own code sets only the cookies it
needs to work, and none of them are for advertising, analytics or tracking. Our free host, Streamlit Community
Cloud, sets more cookies of its own; they're listed further down.

### TraceFort's cookies

| Cookie | What it does | How long it lasts |
| --- | --- | --- |
| `tracefort_token` | Keeps you signed in on this device. It holds a random code, not your name or PIN. | 1 year, or until you sign out |
| `tracefort_notice` | Remembers that you closed the cookie notice, so it doesn't keep coming back. | 1 year |
| `_streamlit_xsrf` | Protects our forms from being submitted by other websites. Set by the software TraceFort runs on. | Until you close your browser |

### Your choices
- **Sign out** to remove the sign-in cookie right away.
- You can also block or delete cookies in your browser settings. If you block them, TraceFort still works,
  but you'll need to sign in each time.

Because these cookies are needed for the site to work, we don't ask for permission before setting them.
If TraceFort's own code ever adds any other kind of cookie, we'll ask you first.

### Cookies from our host
TraceFort runs on Streamlit Community Cloud, owned by Snowflake. Its hosting page sets these cookies on every
visit, without asking, and we can't turn them off on this free host. We never see what they collect.
Snowflake can change them at any time; this is what we saw on November 14, 2026.

| Cookie | Set by | What it's for | About how long |
| --- | --- | --- | --- |
| `_ga`, `_gid`, `_dc_gtm_…` | Google Analytics | Counts visits and how people move around the site | Up to 13 months |
| `ajs_anonymous_id` | Segment | Analytics: a random ID for your browser | 1 year |
| `_dd_s` | Datadog | Monitors whether the hosting page loads and works | Up to 1 year |
| `streamlit_session`, `_streamlit_csrf`, `proxy-tracking-id` | Streamlit | Runs the hosting service and protects its forms | Up to 1 month |

Snowflake explains these in its privacy notice: [streamlit.io/privacy-policy](https://streamlit.io/privacy-policy).
To block them, use your browser's tracking protection or a content blocker.
"""

ACCESSIBILITY = """
We want TraceFort to work for everyone, at any age and ability. Our goal is to meet
the Web Content Accessibility Guidelines (WCAG) 2.1, Level AA.

### What we've done
- Large, easy-to-read text (18px base) in a font with clear, plain numbers.
- High-contrast black, white and red that meets WCAG contrast levels for text.
- Every button, field and menu can be used with a keyboard.
- Every form field has a visible label.
- Nothing relies on color alone: risk is written as a word, and the best homes are numbered I, II and III.
- Every home on the map is also listed as a text card above it.
- Pages work on phones and when zoomed in.

### Known limits
- The interactive map isn't fully usable with a screen reader. The home cards above it carry the same details.
- TraceFort hasn't had an independent accessibility audit yet.

### Tell us
If something is hard to use, please tell us on the Contact page. We read every message.
"""
