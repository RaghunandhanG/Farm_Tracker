import pandas as pd
from pathlib import Path
from pandas.errors import EmptyDataError


def load_data(file_path, columns):

    file = Path(file_path)

    file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not file.exists():

        df = pd.DataFrame(
            columns=columns
        )

        df.to_csv(
            file_path,
            index=False
        )

        return df

    try:

        df = pd.read_csv(
            file_path
        )

        if df.empty and len(df.columns) == 0:

            raise EmptyDataError(
                "Empty file"
            )

        return df

    except (
        EmptyDataError,
        pd.errors.ParserError
    ):

        df = pd.DataFrame(
            columns=columns
        )

        df.to_csv(
            file_path,
            index=False
        )

        return df


def save_row(
    file_path,
    values
):

    df = pd.read_csv(
        file_path
    )

    df.loc[
        len(df)
    ] = values

    df.to_csv(
        file_path,
        index=False
    )