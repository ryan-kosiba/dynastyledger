"""Database helpers for Dynasty Ledger."""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynasty:dynasty@localhost:5432/dynastyledgerdb",
)


def get_connection():
    """Return a new psycopg2 connection using DATABASE_URL."""
    return psycopg2.connect(DATABASE_URL)


def insert_player_values(df):
    """Upsert a DataFrame of player values into the player_values table.

    Expected DataFrame columns: player_id, date, value
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO player_values (ktc_player_id, date, value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ktc_player_id, date)
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    (int(row["player_id"]), row["date"].date(), int(row["value"])),
                )
        conn.commit()
    finally:
        conn.close()
