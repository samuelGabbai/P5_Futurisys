-- Vues de lecture pour les tableaux de bord, sans identifiant salarié ni input brut.
CREATE OR REPLACE VIEW analytics_daily_activity AS
SELECT date_trunc('day', started_at) AS day,
       endpoint AS route,
       COUNT(*) AS requests,
       COUNT(*) FILTER (WHERE status = 'succeeded') AS succeeded,
       COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
       COUNT(*) FILTER (WHERE status = 'failed') AS failed,
       COUNT(*) FILTER (WHERE status = 'pending') AS pending,
       COUNT(*) FILTER (WHERE http_status IN (401, 403)) AS access_denied,
       SUM(COALESCE(row_count, 0)) AS processed_rows,
       AVG(duration_ms) AS mean_duration_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_duration_ms
FROM api_exchanges
GROUP BY date_trunc('day', started_at), endpoint;

CREATE OR REPLACE VIEW analytics_model_scores AS
SELECT date_trunc('day', e.started_at) AS day,
       e.model_sha256,
       (o.payload->>'threshold')::double precision AS threshold,
       COUNT(*) AS scored_requests,
       AVG((o.payload->>'probability')::double precision) AS mean_probability,
       AVG((o.payload->>'prediction')::integer) AS high_risk_request_rate
FROM api_exchanges e
JOIN model_outputs o ON o.exchange_id = e.id
WHERE e.status = 'succeeded'
  AND e.operation = 'threshold_predict'
  AND o.payload ? 'probability'
GROUP BY date_trunc('day', e.started_at), e.model_sha256,
         (o.payload->>'threshold')::double precision
HAVING COUNT(*) >= 5;
