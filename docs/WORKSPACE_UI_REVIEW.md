# Workspace purpose and UI review — November 27, 2026

This source review covers every role-visible navigation entry. Public checkout, signup, kiosk, member/fighter portals and embedded event tabs retain their dedicated flows. It is not a claim that every production transaction has been exercised.

## Navigation ownership

### HOME

| Page | Purpose | Roles |
| --- | --- | --- |
| Dashboard | Daily membership, attendance, sales and event overview | admin |
| System Overview | Work queue, payment reconciliation and connection status | admin |
| Investor Portal | Your assigned event updates and approved business summaries | investor |
| Sponsor Portal | Your assigned sponsorship events and TNG updates | sponsor |

### GYM & MEMBERS

| Page | Purpose | Roles |
| --- | --- | --- |
| Members | Gym member profiles, account activation, memberships and renewals | admin, staff |
| Member Check-In | Front desk member-number keypad and new-member signup QR | admin, staff |
| Check-In Kiosk | Entrance tablet pairing, attendance and device settings | admin, staff |
| Renewal Reminders | Membership renewal and expiration email/text notices and delivery history | admin |
| TNGTrainer | Training sessions, coaches and member development | admin, staff |
| TNG Boxing Game | Play boxing combinations with keyboard or controller: punches, slips, defense and timed drills | admin |

### TNG PROMOTIONS

| Page | Purpose | Roles |
| --- | --- | --- |
| Announcer & DJ | Event run of show, fighter introductions, walkout songs, announcer profile, sponsor promotions and concessions sales announcements | admin, staff, announcer, dj |
| Amateur Matchmaker | Upload amateur boxing rosters, review ages weights and experience, USA Boxing Appendix F proposals | admin, staff, matchmaker |
| TNG BOXING EVENTS | Open an event: fight card, tickets, contracts, printing and event operations | admin, staff, matchmaker |
| Fight Recap | Compare event revenue costs fighter purses commissions expenses profit loss side by side | admin, staff |
| USA Boxing Officials | Oklahoma LBC 27 USA Boxing official contacts work texts SMS permission messages conversations | admin, staff |
| Oklahoma Boxing Clubs | Oklahoma boxing gyms clubs coaches contact person phone email directory | admin, staff |
| Club Inbox | Oklahoma club SMS conversations and replies | admin, staff |
| Officials Inbox | Official work texts, replies and unread conversations | admin, staff |
| Promoter | Find fighters, scout opponents, manage matchups and view signed contracts | admin, matchmaker |
| Event Check-In | Fight-night ticket QR scanner and printed ticket activation | admin, staff |
| Fight Calendar | Upcoming fight dates and event planning | admin, staff, matchmaker |
| Fighter Portal Videos | Review fighter submissions and footage | admin |
| Manager Portal | Manager agreements and fighter representation | manager |

### FACILITY MANAGEMENT

| Page | Purpose | Roles |
| --- | --- | --- |
| Venue & Event Bookings | Facility rentals, coordinator calendar, public booking requests, holds and reservations | admin, event_coordinator |
| Venue Inbox | Venue booking SMS conversations and replies | admin, staff |
| Chef & Concessions | Event kitchen: menu pricing, food costs, shopping lists, prep, AI drafts and printable menus | admin, concessions |

### SHOP & SALES

| Page | Purpose | Roles |
| --- | --- | --- |
| TNG Apparel | Shirt designs, presales, Clover items, public shop links and pickup orders | admin |
| Sales | Record purchases and review the sales ledger | admin, staff |
| Products | Membership plans, prices and merchandise inventory | admin |
| Reports | Revenue, sales, commissions and business reports | admin |
| My Sales | Your sales and commissions | rep |

### MARKETING

| Page | Purpose | Roles |
| --- | --- | --- |
| Text Inbox | Incoming SMS, unread conversations and customer service replies | admin, staff |
| Call Center | Inbound phone calls, marketing transfers, callbacks and ticket checkout texts | admin |
| Marketing Center | Email, text messages and campaigns for gym members | admin |
| Leads | Prospective customers, follow-ups and contact details | admin, staff |
| QR Referrals | Referral QR codes and signup links | admin, staff |

### ADMINISTRATION

| Page | Purpose | Roles |
| --- | --- | --- |
| Investor Center | Investor business access, membership revenue, event and fighter ticket sales, expenses and published updates | admin |
| Clover | Payment connection, catalog and customer synchronization | admin |
| Duplicate Review | Find and merge duplicate contacts | admin |
| User Management | Staff accounts, roles and access | admin |
| Security Center | Trusted devices, sign-ins, account protection and activity | admin |

## Changes in this upgrade

- Boxing & Events is now TNG PROMOTIONS. Event planning, fight-night tools and boxing contacts have labeled sections. Existing route IDs, role checks and saved links remain valid.
- Venue bookings, venue inbox and chef tools have a separate operations category.
- Dashboard views separate the overview, gym attendance, promotions, and business sales. Officials, clubs and bookings remain directly reachable from the overview.
- Global navigation now focuses on the current page, search, messages and workspaces. Account/appearance settings are in the account menu. Clover synchronization is on the Clover page.
- Optional workspace guidance is compact, with related pages collapsed. Command briefing appears only in overview workspaces. The commission deadline alert remains global as previously requested.
- Shared spacing, typography, borders, cards and Standard-mode background are quieter. Command mode remains selectable.

## Existing dedicated views reviewed

Members: profile/account and membership actions. Amateur Matchmaker: roster, setup, proposals, event planner and rule reference. Event workspace: event-specific card, tickets, contracts, medicals, costs, sponsors and recap. Marketing Center: contacts, generator, email, text, templates, history and analytics views. User Management: access, account creation, event access and roster requests. Venue: calendar and request inbox. Clubs/officials: their own contacts and message views. Investor Center: access, business ledger, updates and preview. These views already scope their working content; their business forms were preserved.

## Productization follow-up

The UI upgrade is not a multi-tenant product release. Before selling hosted versions: implement and test organization-level data isolation across every backend query and file; per-company configuration/branding; onboarding and billing; backup/restore drills; migration and deployment rollback; and authorization, payment reconciliation and messaging delivery acceptance tests. Current TNG production records must not become demo data.

## Validation

All 108 frontend tests passed, including navigation ownership, role-limited routes, event deep links and existing game/operations tests. The production Vite build passed. Browser checks used the real AppShell/Dashboard with synthetic read-only fixtures at desktop 1440×1050 and phone 390×844: four scoped dashboard panels, category ownership, Standard/Command switching, mobile navigation, no page overflow, and no captured browser errors. This does not replace live payment, email, text, contract or kiosk acceptance testing. No production data was changed and no messages were sent.
