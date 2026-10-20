-- Migration additive et réexécutable ; aucune suppression d'historique.
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS duration_ms DOUBLE PRECISION;
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS message VARCHAR(2000);
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS processing_stage VARCHAR(40) DEFAULT 'legacy';
ALTER TABLE api_exchanges ALTER COLUMN processing_stage SET DEFAULT 'received';
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS row_count INTEGER;
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS feature_count INTEGER;
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS request_details JSONB;
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS error_details JSONB;
ALTER TABLE api_exchanges ADD COLUMN IF NOT EXISTS response_summary JSONB;

CREATE OR REPLACE VIEW api_logs AS
SELECT started_at AS date_requete, id AS requete_id, method AS methode,
       endpoint AS route, operation AS operation_modele, status AS statut,
       http_status AS code_http, duration_ms AS duree_ms, message,
       processing_stage AS etape, row_count AS lignes, feature_count AS variables,
       filename AS fichier, error_type AS type_erreur, error_details AS detail_erreur,
       request_details AS contexte, response_summary AS resume_resultat,
       model_sha256 AS version_modele, completed_at AS date_fin
FROM api_exchanges;
