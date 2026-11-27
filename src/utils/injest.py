from pandas import DataFrame, read_csv

def load_observation(path: str, dates=[]) -> DataFrame:
    df = read_csv(path, parse_dates=dates)
    return (
        df.set_axis(df.iloc[0], axis=1)
        .iloc[1:]
        .reset_index(drop=True)
    )