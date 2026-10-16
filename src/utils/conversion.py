KILO = 1000
NAIRA = 100
DAY_IN_HOURS = 24
HOUR_IN_MINUTES = 60
MINUTE_IN_SECONDS = 60

def to_kobo(naira):
    return round(naira * NAIRA)

def to_naira(kobo):
    return round(kobo/NAIRA, 2)

def to_money(kobo):
    return f"₦{ kobo / NAIRA:,.2f}"

def to_grams(kg):
    return round(kg * KILO)

def to_kilo(gram):
    return gram / KILO