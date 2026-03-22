CREATE INDEX IF NOT EXISTS idx_members_username ON members(username);
CREATE INDEX IF NOT EXISTS idx_members_role ON members(role);
CREATE INDEX IF NOT EXISTS idx_sessions_member ON sessions(member_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_project_tables_db ON project_tables(database_name);
CREATE INDEX IF NOT EXISTS idx_project_records_table ON project_records(database_name, table_name);
CREATE INDEX IF NOT EXISTS idx_project_records_key ON project_records(database_name, table_name, record_key);
CREATE INDEX IF NOT EXISTS idx_uploadsession_device ON UploadSession(deviceID);
CREATE INDEX IF NOT EXISTS idx_uploadsession_policy ON UploadSession(policyID);
CREATE INDEX IF NOT EXISTS idx_uploadsession_status ON UploadSession(status);
CREATE INDEX IF NOT EXISTS idx_filemetadata_session ON FileMetadata(sessionID);
CREATE INDEX IF NOT EXISTS idx_onetimetoken_session ON OneTimeToken(sessionID);
CREATE INDEX IF NOT EXISTS idx_onetimetoken_tokenvalue ON OneTimeToken(tokenValue);
CREATE INDEX IF NOT EXISTS idx_downloadlog_token ON DownloadLog(tokenID);
CREATE INDEX IF NOT EXISTS idx_downloadlog_time ON DownloadLog(downloadTime);
CREATE INDEX IF NOT EXISTS idx_ratelimit_device ON RateLimitLog(deviceID);
CREATE INDEX IF NOT EXISTS idx_ratelimit_time ON RateLimitLog(timestamp);

