-- =============================================================
-- Module B: SQL Indexes for Query Optimisation
-- Targeting WHERE, JOIN, ORDER BY clauses in API queries
-- =============================================================

-- UploadSession — most queried table (status filter, device joins, expiry checks)
CREATE INDEX IF NOT EXISTS idx_uploadsession_status
    ON UploadSession(status);

CREATE INDEX IF NOT EXISTS idx_uploadsession_deviceid
    ON UploadSession(deviceID);

CREATE INDEX IF NOT EXISTS idx_uploadsession_policyid
    ON UploadSession(policyID);

CREATE INDEX IF NOT EXISTS idx_uploadsession_expiry
    ON UploadSession(expiryTimestamp);

CREATE INDEX IF NOT EXISTS idx_uploadsession_upload_ts
    ON UploadSession(uploadTimestamp);

-- FileMetadata — always JOINed with UploadSession
CREATE INDEX IF NOT EXISTS idx_filemetadata_sessionid
    ON FileMetadata(sessionID);

CREATE INDEX IF NOT EXISTS idx_filemetadata_mimetype
    ON FileMetadata(mimeType);

CREATE INDEX IF NOT EXISTS idx_filemetadata_filename
    ON FileMetadata(fileName);

-- OneTimeToken — looked up by tokenValue on every download
CREATE INDEX IF NOT EXISTS idx_onetimetoken_tokenvalue
    ON OneTimeToken(tokenValue);

CREATE INDEX IF NOT EXISTS idx_onetimetoken_status
    ON OneTimeToken(status);

CREATE INDEX IF NOT EXISTS idx_onetimetoken_sessionid
    ON OneTimeToken(sessionID);

-- DownloadLog — JOINed with OneTimeToken
CREATE INDEX IF NOT EXISTS idx_downloadlog_tokenid
    ON DownloadLog(tokenID);

CREATE INDEX IF NOT EXISTS idx_downloadlog_time
    ON DownloadLog(downloadTime DESC);

-- RateLimitLog — filtered by deviceID + eventType
CREATE INDEX IF NOT EXISTS idx_ratelimitlog_deviceid
    ON RateLimitLog(deviceID);

CREATE INDEX IF NOT EXISTS idx_ratelimitlog_eventtype
    ON RateLimitLog(eventType);

CREATE INDEX IF NOT EXISTS idx_ratelimitlog_composite
    ON RateLimitLog(deviceID, eventType);

-- FileIntegrityCheck — filtered by fileID and verified flag
CREATE INDEX IF NOT EXISTS idx_integrity_fileid
    ON FileIntegrityCheck(fileID);

CREATE INDEX IF NOT EXISTS idx_integrity_verified
    ON FileIntegrityCheck(verified);

-- AuditTrail — filtered by sessionID, ordered by timestamp
CREATE INDEX IF NOT EXISTS idx_audittrail_sessionid
    ON AuditTrail(sessionID);

CREATE INDEX IF NOT EXISTS idx_audittrail_timestamp
    ON AuditTrail(timestamp DESC);

-- ErrorLog — filtered by sessionID
CREATE INDEX IF NOT EXISTS idx_errorlog_sessionid
    ON ErrorLog(sessionID);

CREATE INDEX IF NOT EXISTS idx_errorlog_timestamp
    ON ErrorLog(timestamp DESC);

-- Member — email lookups (login)
CREATE INDEX IF NOT EXISTS idx_member_email
    ON Member(email);

-- UserLogin — username lookup on login
CREATE INDEX IF NOT EXISTS idx_userlogin_username
    ON UserLogin(username);

CREATE INDEX IF NOT EXISTS idx_userlogin_memberid
    ON UserLogin(memberID);
