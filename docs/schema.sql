-- Schéma PostgreSQL HRNova généré depuis database.py.
-- Création de la base et import : python create_db.py --create-database

CREATE TABLE employees (
	id_employee SERIAL NOT NULL, 
	age INTEGER NOT NULL, 
	genre VARCHAR NOT NULL, 
	revenu_mensuel INTEGER NOT NULL, 
	statut_marital VARCHAR NOT NULL, 
	departement VARCHAR NOT NULL, 
	poste VARCHAR NOT NULL, 
	nombre_experiences_precedentes INTEGER NOT NULL, 
	nombre_heures_travailless INTEGER NOT NULL, 
	annee_experience_totale INTEGER NOT NULL, 
	annees_dans_l_entreprise INTEGER NOT NULL, 
	annees_dans_le_poste_actuel INTEGER NOT NULL, 
	PRIMARY KEY (id_employee)
);

CREATE TABLE model_versions (
	sha256 VARCHAR(64) NOT NULL, 
	feature_names JSONB NOT NULL, 
	threshold FLOAT NOT NULL, 
	positive_class INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (sha256)
);

CREATE TABLE surveys (
	employee_id INTEGER NOT NULL, 
	code_sondage VARCHAR NOT NULL, 
	a_quitte_l_entreprise VARCHAR NOT NULL, 
	nombre_participation_pee INTEGER NOT NULL, 
	nb_formations_suivies INTEGER NOT NULL, 
	nombre_employee_sous_responsabilite INTEGER NOT NULL, 
	distance_domicile_travail INTEGER NOT NULL, 
	niveau_education INTEGER NOT NULL, 
	domaine_etude VARCHAR NOT NULL, 
	ayant_enfants VARCHAR NOT NULL, 
	frequence_deplacement VARCHAR NOT NULL, 
	annees_depuis_la_derniere_promotion INTEGER NOT NULL, 
	annes_sous_responsable_actuel INTEGER NOT NULL, 
	PRIMARY KEY (employee_id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id_employee), 
	UNIQUE (code_sondage)
);

CREATE TABLE evaluations (
	employee_id INTEGER NOT NULL, 
	eval_number VARCHAR NOT NULL, 
	satisfaction_employee_environnement INTEGER NOT NULL, 
	note_evaluation_precedente INTEGER NOT NULL, 
	niveau_hierarchique_poste INTEGER NOT NULL, 
	satisfaction_employee_nature_travail INTEGER NOT NULL, 
	satisfaction_employee_equipe INTEGER NOT NULL, 
	satisfaction_employee_equilibre_pro_perso INTEGER NOT NULL, 
	note_evaluation_actuelle INTEGER NOT NULL, 
	heure_supplementaires VARCHAR NOT NULL, 
	augementation_salaire_precedente VARCHAR NOT NULL, 
	PRIMARY KEY (employee_id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id_employee), 
	UNIQUE (eval_number)
);

CREATE TABLE prepared_employees (
	employee_id INTEGER NOT NULL, 
	model_sha256 VARCHAR(64) NOT NULL, 
	features JSONB NOT NULL, 
	PRIMARY KEY (employee_id, model_sha256), 
	FOREIGN KEY(employee_id) REFERENCES employees (id_employee), 
	FOREIGN KEY(model_sha256) REFERENCES model_versions (sha256)
);

CREATE TABLE api_exchanges (
	id VARCHAR(36) NOT NULL, 
	method VARCHAR(10) NOT NULL, 
	endpoint VARCHAR(255) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	status VARCHAR(20) NOT NULL, 
	http_status INTEGER, 
	error_type VARCHAR(100), 
	model_sha256 VARCHAR(64), 
	operation VARCHAR(40), 
	filename VARCHAR(255), 
	duration_ms DOUBLE PRECISION,
	message VARCHAR(2000),
	processing_stage VARCHAR(40) NOT NULL,
	row_count INTEGER,
	feature_count INTEGER,
	request_details JSONB,
	error_details JSONB,
	response_summary JSONB,
	PRIMARY KEY (id), 
	CHECK (status IN ('pending', 'succeeded', 'rejected', 'failed')), 
	FOREIGN KEY(model_sha256) REFERENCES model_versions (sha256)
);

CREATE INDEX ix_api_exchanges_status ON api_exchanges (status);

CREATE INDEX ix_api_exchanges_endpoint ON api_exchanges (endpoint);

CREATE INDEX ix_api_exchanges_started_at ON api_exchanges (started_at);

CREATE TABLE model_inputs (
	id SERIAL NOT NULL, 
	exchange_id VARCHAR(36) NOT NULL, 
	row_index INTEGER NOT NULL, 
	employee_id INTEGER, 
	features JSONB NOT NULL, 
	target INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (exchange_id, row_index), 
	FOREIGN KEY(exchange_id) REFERENCES api_exchanges (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id_employee)
);

CREATE INDEX ix_model_inputs_exchange_id ON model_inputs (exchange_id);

CREATE TABLE model_outputs (
	exchange_id VARCHAR(36) NOT NULL, 
	payload JSONB NOT NULL, 
	model_values JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (exchange_id), 
	FOREIGN KEY(exchange_id) REFERENCES api_exchanges (id)
);

CREATE VIEW api_logs AS
SELECT started_at AS date_requete, id AS requete_id, method AS methode,
       endpoint AS route, operation AS operation_modele, status AS statut,
       http_status AS code_http, duration_ms AS duree_ms, message,
       processing_stage AS etape, row_count AS lignes, feature_count AS variables,
       filename AS fichier, error_type AS type_erreur, error_details AS detail_erreur,
       request_details AS contexte, response_summary AS resume_resultat,
       model_sha256 AS version_modele, completed_at AS date_fin
FROM api_exchanges;

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
