BEGIN;

ALTER TABLE sales_guideline_resources
ADD COLUMN IF NOT EXISTS partition_id integer,
ADD COLUMN IF NOT EXISTS section_id integer;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sales_guideline_resources'
          AND column_name = 'subsection_id'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE sales_guideline_resources
        ALTER COLUMN subsection_id DROP NOT NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_sales_guideline_resources_partition_id'
    ) THEN
        ALTER TABLE sales_guideline_resources
        ADD CONSTRAINT fk_sales_guideline_resources_partition_id
        FOREIGN KEY (partition_id) REFERENCES sales_guideline_partitions (id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_sales_guideline_resources_section_id'
    ) THEN
        ALTER TABLE sales_guideline_resources
        ADD CONSTRAINT fk_sales_guideline_resources_section_id
        FOREIGN KEY (section_id) REFERENCES sales_guideline_sections (id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_sales_guideline_resources_partition_id
ON sales_guideline_resources (partition_id);

CREATE INDEX IF NOT EXISTS ix_sales_guideline_resources_section_id
ON sales_guideline_resources (section_id);

ALTER TABLE sales_guideline_resources
DROP CONSTRAINT IF EXISTS ck_sales_guideline_resource_single_parent;

ALTER TABLE sales_guideline_resources
ADD CONSTRAINT ck_sales_guideline_resource_single_parent
CHECK (
    ((partition_id IS NOT NULL)::integer +
     (section_id IS NOT NULL)::integer +
     (subsection_id IS NOT NULL)::integer) = 1
);

COMMIT;
