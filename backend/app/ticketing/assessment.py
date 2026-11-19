"""TNG Oklahoma event assessment: 5% of ticket revenue, $450 minimum."""
from decimal import Decimal,ROUND_HALF_UP
MINIMUM_CENTS=45000
RATE_PERCENT=5

def percentage_cents(gross_cents):
 return int((Decimal(max(0,int(gross_cents)))*Decimal('0.05')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def required_cents(gross_cents):return max(MINIMUM_CENTS,percentage_cents(gross_cents))
