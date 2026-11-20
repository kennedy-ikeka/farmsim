KILO = 1000
NAIRA = 100
SECONDS_IN_MINUTE = 60
MINUTES_IN_HOUR = 60
HOURS_IN_DAY = 24
DAYS_IN_MONTHS = 30
MONTHS_IN_YEAR = 12

def to_kobo(naira):
    return round(naira * NAIRA)

def to_naira(kobo):
    return round(kobo/NAIRA, 2)

def to_money(kobo):
    return f"₦{ kobo / NAIRA:,.2f}"

def to_gram(kg):
    return round(kg * KILO)

def to_kilo(gram):
    return gram / KILO