# PRIZMBET v3 Product Requirements

## Product Overview
PRIZMBET v3 is a prematch crypto betting web application built around PRIZM blockchain transfers. The website issues a temporary betting coupon code, and a bet is considered valid only after an on-chain PRIZM transfer is detected by the backend listener.

## Core Principles
- Bets are accepted only through PRIZM blockchain transfers.
- Live betting is disabled. Only prematch events are available.
- One active coupon per sender wallet is the preferred operational rule.
- If a transfer message is unreadable, the backend may match the transfer by sender wallet only when exactly one active coupon exists for that wallet.
- Maximum stake is 30,000 PRIZM.

## Main User Flows

### 1. Public betting flow
1. User opens the homepage.
2. User filters prematch events and selects an outcome.
3. User opens the smart coupon.
4. User enters sender PRIZM wallet and stake amount.
5. System issues a coupon code with fixed odds and expiration time.
6. User opens the official PRIZM wallet and sends PRIZM to the project wallet with the coupon code in the transfer message.
7. Backend listener validates sender wallet, coupon status, event start time, and stake limits.
8. Bet becomes accepted or rejected.
9. User sees the resulting status in the wallet cabinet.

### 2. Wallet cabinet flow
- User opens cabinet from the site.
- User enters or reuses PRIZM wallet.
- Cabinet shows coupon history, accepted and rejected bets, settlement state, turnover, and rank preview.

### 3. Operator flow
- Operator opens operator panel.
- Operator authenticates with named account.
- Operator monitors accepted, rejected, settled, and paid bets.
- Finance role or admin marks payouts.
- Audit events are visible in the operator audit stream.

## Roles
- Admin: full operator access and user management.
- Operator: view and work with operational feed.
- Finance: payout-related actions.
- Viewer: read-only monitoring.

## Main Pages
- `/` main public betting page
- `/operator.html` operator dashboard
- `/admin.html` admin redirect shell
- `/intent-lab.html` archive testing page

## Functional Requirements
- RU and EN language switch on active surfaces.
- Moscow time is used consistently in the product.
- Main line displays prematch events only.
- Matches starting soon should be visually highlighted.
- Finished events should have separate visual state where applicable.
- Event links must point to specific matches, not generic sport landing pages.
- Smart coupon must show fixed odds, expiration time, sender wallet, stake amount, and potential payout.
- Cabinet must show accepted, rejected, won, lost, and paid states.
- Operator audit log must record important state changes.
- Telegram notifications are used for operational alerts.

## Validation Rules
- Reject if event is live or already started.
- Reject if coupon is expired.
- Reject if sender wallet does not match the coupon wallet.
- Reject if no valid coupon can be determined.
- Reject if transfer amount exceeds 30,000 PRIZM.
- Reject if transfer amount is below minimum configured amount.

## Non-Goals for This Test Pass
- No live betting.
- No full affiliate system.
- No bonus wheel or casino mechanics.
- No non-PRIZM payment method for core betting acceptance.

## Test Focus
Please focus on:
- main page rendering
- RU and EN switching
- prematch event filtering and sorting
- coupon issuance flow
- cabinet rendering and status display
- operator shell rendering and login flow
- operator feed and audit visibility
- layout regressions and major broken interactions

## Environment
- Local frontend target: http://127.0.0.1:8010/
- Local backend health endpoint expected at: http://127.0.0.1:8081/health
