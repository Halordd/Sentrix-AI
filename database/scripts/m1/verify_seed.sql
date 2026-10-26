SELECT 'scan_profile' AS table_name, count(*) AS n FROM scan_profile
UNION ALL SELECT 'app_user', count(*) FROM app_user
UNION ALL SELECT 'project', count(*) FROM project
UNION ALL SELECT 'project_member', count(*) FROM project_member
UNION ALL SELECT 'target', count(*) FROM target
UNION ALL SELECT 'target_authorization', count(*) FROM target_authorization
UNION ALL SELECT 'scan_job', count(*) FROM scan_job
UNION ALL SELECT 'scan_run', count(*) FROM scan_run
UNION ALL SELECT 'scan_observation', count(*) FROM scan_observation
UNION ALL SELECT 'finding', count(*) FROM finding
UNION ALL SELECT 'evidence', count(*) FROM evidence
UNION ALL SELECT 'finding_status_event', count(*) FROM finding_status_event
UNION ALL SELECT 'analysis', count(*) FROM analysis
UNION ALL SELECT 'prompt_template', count(*) FROM prompt_template
UNION ALL SELECT 'prompt_template_version', count(*) FROM prompt_template_version
UNION ALL SELECT 'model', count(*) FROM model
UNION ALL SELECT 'model_version', count(*) FROM model_version
UNION ALL SELECT 'dataset', count(*) FROM dataset
UNION ALL SELECT 'dataset_version', count(*) FROM dataset_version
UNION ALL SELECT 'evaluation_run', count(*) FROM evaluation_run
UNION ALL SELECT 'remediation', count(*) FROM remediation
UNION ALL SELECT 'verification', count(*) FROM verification
UNION ALL SELECT 'report', count(*) FROM report
UNION ALL SELECT 'report_finding', count(*) FROM report_finding
UNION ALL SELECT 'audit_event', count(*) FROM audit_event
ORDER BY table_name;
