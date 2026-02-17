CREATE TABLE IF NOT EXISTS player_values (
    id SERIAL PRIMARY KEY,
    ktc_player_id INTEGER NOT NULL,
    date DATE NOT NULL,
    value INTEGER NOT NULL,
    UNIQUE (ktc_player_id, date)
);
