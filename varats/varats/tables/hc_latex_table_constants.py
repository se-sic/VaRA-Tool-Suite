import pandas as pd

CS_MAPPINGS = {
    "duckdb": r"\duckdb{}",
    "libzmq": r"\zmq{}",
    "7zip": r"\SZip{}",
    "FastDownward": r"\fd{}",
    "cadical": r"\cadical{}",
    "cryptominisat": r"\cms{}",
    "lrzip": r"\lrzip{}",
    "bzip2": r"\bzip{}",
    "brotli": r"\brotli{}",
    "xz": r"\xz{}",
    "libvpx": r"\vpx{}",
    "mariadb": r"\mariadb{}",
    "postgres": r"\psql{}",
    "x264": r"\xVid{}",
    "DunePerfRegression": r"\dune{}",
}

def reformat_project_column(df: pd.DataFrame, column_name="project") -> pd.DataFrame:
    # Check if the column exists in the DataFrame
    if column_name in df.columns:
        df[column_name] = df[column_name].apply(lambda x: CS_MAPPINGS.get(x, x))
    #Otherwise, check if the index name matches the column name and reformat the index
    elif df.index.name == column_name:
        df.index = df.index.to_series().apply(lambda x: CS_MAPPINGS.get(x, x))
    return df