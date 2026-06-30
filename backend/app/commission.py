def commission_rate(monthly_sale_count: int) -> float:
    if monthly_sale_count >= 20:
        return 0.25
    if monthly_sale_count >= 10:
        return 0.20
    if monthly_sale_count >= 1:
        return 0.15
    return 0.0
