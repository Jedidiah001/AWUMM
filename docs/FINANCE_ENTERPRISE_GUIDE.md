# Finance Enterprise Feature Guide

## What Was Added

The Finance page now contains tabs for:

- Dashboard
- Sponsorships
- Venues & Tours
- Event Financials
- Settlements
- Reports

All features remain inside the existing `/finance` page. No separate frontend page was added.

## API Surface

- `GET /api/finance/dashboard`
- `GET /api/finance/transactions`
- `POST /api/finance/transactions`
- `GET /api/finance/sponsorships`
- `POST /api/finance/sponsors`
- `POST /api/finance/sponsorships/<sponsor_id>/contracts`
- `POST /api/finance/sponsorship-requirements/<requirement_id>/deliverables`
- `POST /api/finance/sponsorships/<sponsor_id>/controversies`
- `POST /api/finance/sponsorship-contracts/<contract_id>/payments`
- `GET /api/finance/venues-tours`
- `POST /api/finance/venue-upgrades`
- `POST /api/finance/tours`
- `POST /api/finance/tours/<tour_id>/optimize`
- `POST /api/finance/settlements/event/<event_id>`
- `POST /api/finance/settlements/tour/<tour_id>`
- `GET /api/finance/reports/profitability`
- `GET /api/finance/reports/budget-variance`
- `GET /api/finance/forecasts`
- `POST /api/finance/reconcile`

## Core Workflows

### Sponsorship

1. Open `/finance`.
2. Select `Sponsorships`.
3. Create a sponsor profile.
4. Create a contract for that sponsor.
5. Track deliverables from the sponsor directory.
6. Process a payment to post a `Sponsorship Revenue` finance transaction.
7. Record a controversy to lower satisfaction and set a threat level.

### Venue Upgrade

1. Open `Venues & Tours`.
2. Select a venue.
3. Enter upgrade name, cost, and expected revenue lift.
4. Purchase the upgrade.
5. Confirm a negative `Capital Expenditure` transaction is posted.

### Tour And Settlement

1. Open `Venues & Tours`.
2. Create a tour with three venue stops.
3. Optimize the latest tour to update routing and travel cost records.
4. Open `Event Financials`.
5. Select an event and enter actual revenue/expense results.
6. Settle the event.
7. Confirm event revenue and expense transactions appear under `Settlements`.

## Financial Rules Implemented

- Sponsorship payment amount is derived from total contract value and payment schedule.
- Event settlement posts one revenue transaction and separate expense transactions.
- Profit and margin are calculated from posted event actuals.
- Venue upgrades post as capital expenditures.
- Sponsorship controversies lower sponsor satisfaction based on severity.
- Reports expose profitability, budget variance, and 30/60/90-day forecasts.

## Verification

Run:

```powershell
$env:PYTHONUTF8='1'
python -m unittest backend.test_regressions backend.test_finance_enterprise
```

The UTF-8 environment variable avoids an existing Windows console encoding issue in unrelated startup logging.
