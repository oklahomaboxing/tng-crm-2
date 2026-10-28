"""Paginated Clover profile reconciliation. Does not send messages or record payments."""
import asyncio
import logging
import os
import requests
from fastapi import HTTPException
from app.database import SessionLocal
from .member_profiles import import_customer, lock_profiles, audit_profile


def fetch_customers():
    token = os.getenv('CLOVER_API_TOKEN', '')
    merchant = os.getenv('CLOVER_MERCHANT_ID', '')
    if not token or not merchant:
        raise HTTPException(503, 'Clover customer access is not configured. Configure the Clover API token and merchant ID.')
    base = 'https://api.clover.com' if os.getenv('CLOVER_ENV', 'production') == 'production' else 'https://apisandbox.dev.clover.com'
    customers = []
    seen = set()
    for offset in range(0, 20000, 100):
        try:
            response = requests.get(f'{base}/v3/merchants/{merchant}/customers',
                params={'expand': 'emailAddresses,phoneNumbers', 'limit': 100, 'offset': offset},
                headers={'Authorization': 'Bearer ' + token}, timeout=30)
            if not response.ok:
                raise HTTPException(502, f'Clover customer access returned HTTP {response.status_code}. Check Customers read permission on the Clover API token.')
            rows = response.json().get('elements')
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError('Invalid customer page')
        except (requests.RequestException, ValueError, AttributeError):
            raise HTTPException(502, 'Clover customers could not be read. No profiles were imported; retry the sync.')
        ids = {row.get('id') for row in rows if row.get('id')}
        if rows and ids and ids.issubset(seen):
            raise HTTPException(502, 'Clover repeated a customer page. No partial import was applied; retry the sync.')
        seen.update(ids)
        customers.extend(rows)
        if len(rows) < 100:
            return customers
    raise HTTPException(502, 'Clover customer sync exceeded its page limit. Contact support to complete the import.')


def reconcile_customers(db, customers, user_id=None):
    lock_profiles(db)
    counts = {'customers_received': len(customers), 'members_created': 0, 'members_linked': 0,
              'skipped': 0, 'needs_review': 0, 'review_customer_ids': []}
    for customer in customers:
        try:
            outcome, member = import_customer(db, customer)
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            counts['needs_review'] += 1
            counts['review_customer_ids'].append(str(customer.get('id') or ''))
            continue
        counts[{'created': 'members_created', 'linked': 'members_linked', 'skipped': 'skipped'}[outcome]] += 1
    audit_profile(db, user_id, 'CLOVER_PROFILE_SYNC',
                  f"Received {len(customers)}; created {counts['members_created']}; linked {counts['members_linked']}; review {counts['needs_review']}")
    db.commit()
    return {'message': 'Clover customer profiles synced. Membership payments and portal passwords were unchanged.', **counts}


def sync_profiles():
    customers = fetch_customers()
    with SessionLocal() as db:
        return reconcile_customers(db, customers)


async def profile_sync_loop():
    interval = max(300, int(os.getenv('CLOVER_PROFILE_SYNC_INTERVAL_SECONDS', '600')))
    while True:
        if os.getenv('CLOVER_API_TOKEN') and os.getenv('CLOVER_MERCHANT_ID'):
            try:
                await asyncio.to_thread(sync_profiles)
            except Exception as exc:
                # Never log provider response bodies, credentials or customer contact information.
                logging.getLogger(__name__).warning('Clover profile reconciliation failed (%s)', type(exc).__name__)
        await asyncio.sleep(interval)
