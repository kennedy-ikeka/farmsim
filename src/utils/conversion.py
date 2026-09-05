def to_kobo(naira):
    return round(naira * 100)

def to_naira(kobo):
    return f"₦{ kobo / 100:,.2f}"

def to_grams(kg):
    return round(kg * 1000)