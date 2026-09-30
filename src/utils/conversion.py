def to_kobo(naira):
    return round(naira * 100)

def to_naira(kobo):
    return round(kobo/100, 2)

def to_money(kobo):
    return f"₦{ kobo / 100:,.2f}"

def to_grams(kg):
    return round(kg * 1000)

def to_kilo(gram):
    return gram / 1000