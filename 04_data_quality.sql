-- Operational metrics and reject reason distribution.
SELECT file_name, records_read, accepted, rejected, superseded_in_batch,
       ignored_old_or_equal, completed_at
FROM ingestion_runs
ORDER BY completed_at, file_name;

SELECT reason, COUNT(*) AS rejected_rows
FROM rejected_order_events GROUP BY reason ORDER BY rejected_rows DESC;
