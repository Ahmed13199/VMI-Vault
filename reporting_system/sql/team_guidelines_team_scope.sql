BEGIN;

INSERT INTO teams (name, type)
SELECT 'Sales', 'department'
WHERE NOT EXISTS (
    SELECT 1
    FROM teams
    WHERE lower(name) = 'sales'
);

ALTER TABLE sales_guideline_partitions
ADD COLUMN IF NOT EXISTS team_id integer;

UPDATE sales_guideline_partitions
SET team_id = (
    SELECT id
    FROM teams
    WHERE lower(name) = 'sales'
    ORDER BY id
    LIMIT 1
)
WHERE team_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sales_guideline_partitions'
          AND column_name = 'team_id'
          AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE sales_guideline_partitions
        ALTER COLUMN team_id SET NOT NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_sales_guideline_partitions_team_id'
    ) THEN
        ALTER TABLE sales_guideline_partitions
        ADD CONSTRAINT fk_sales_guideline_partitions_team_id
        FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_sales_guideline_partitions_team_id
ON sales_guideline_partitions (team_id);

COMMIT;
