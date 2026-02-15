-- Functionality 1: File Upload & Session Creation

-- 1a. all active upload sessions
SELECT us.sessionID, fm.fileName, us.status
FROM UploadSession us
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE us.status = 'ACTIVE';

-- 1b. token for an active session
SELECT ot.tokenValue, ot.expiryAt, fm.fileName
FROM OneTimeToken ot
JOIN UploadSession us ON ot.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE us.sessionID = 5 AND ot.status = 'ACTIVE';

-- 1c. uploads per device
SELECT d.location, COUNT(us.sessionID) AS totalUploads
FROM Device d
LEFT JOIN UploadSession us ON d.deviceID = us.deviceID
GROUP BY d.deviceID, d.location
ORDER BY totalUploads DESC;


-- Functionality 2: File Download Using One-Time Token

-- 2a. validate token and get file info
SELECT ot.tokenValue, ot.status, fm.fileName, fm.storagePath
FROM OneTimeToken ot
JOIN UploadSession us ON ot.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE ot.tokenValue = 'TKN-U1V2W3X4Y5' AND ot.status = 'ACTIVE';

-- 2b. download history
SELECT dl.downloadID, dl.downloadTime, dl.userDeviceInfo, fm.fileName
FROM DownloadLog dl
JOIN OneTimeToken ot ON dl.tokenID = ot.tokenID
JOIN UploadSession us ON ot.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
ORDER BY dl.downloadTime DESC;

-- 2c. files downloaded within 5 minutes of upload
SELECT fm.fileName, us.uploadTimestamp, dl.downloadTime
FROM DownloadLog dl
JOIN OneTimeToken ot ON dl.tokenID = ot.tokenID
JOIN UploadSession us ON ot.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE dl.downloadTime - us.uploadTimestamp <= INTERVAL '5 minutes';


-- Functionality 3: Auto-Expiry & File Cleanup

-- 3a. all expired sessions
SELECT us.sessionID, fm.fileName, us.expiryTimestamp
FROM UploadSession us
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE us.status = 'EXPIRED';

-- 3b. active sessions that are past expiry (need cleanup)
SELECT us.sessionID, fm.fileName, us.expiryTimestamp
FROM UploadSession us
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE us.status = 'ACTIVE' AND us.expiryTimestamp < CURRENT_TIMESTAMP;

-- 3c. session status counts
SELECT status, COUNT(*) AS sessionCount
FROM UploadSession
GROUP BY status
ORDER BY sessionCount DESC;

-- 3d. sessions per expiry policy
SELECT ep.policyID, ep.maxLifetimeMinutes, ep.deleteAfterFirstDownload, COUNT(us.sessionID) AS totalSessions
FROM ExpiryPolicy ep
LEFT JOIN UploadSession us ON ep.policyID = us.policyID
GROUP BY ep.policyID, ep.maxLifetimeMinutes, ep.deleteAfterFirstDownload
ORDER BY ep.policyID;


-- Functionality 4: Rate Limiting & Abuse Prevention

-- 4a. devices that hit rate limits
SELECT d.location, d.ipAddress, rl.timestamp
FROM RateLimitLog rl
JOIN Device d ON rl.deviceID = d.deviceID
WHERE rl.eventType = 'RATE_LIMIT_HIT';

-- 4b. upload count per device
SELECT d.location, COUNT(*) AS uploadCount
FROM RateLimitLog rl
JOIN Device d ON rl.deviceID = d.deviceID
WHERE rl.eventType = 'UPLOAD'
GROUP BY d.deviceID, d.location
ORDER BY uploadCount DESC;

-- 4c. devices with more than 2 uploads
SELECT d.location, d.ipAddress, COUNT(*) AS uploadCount
FROM RateLimitLog rl
JOIN Device d ON rl.deviceID = d.deviceID
WHERE rl.eventType = 'UPLOAD'
GROUP BY d.deviceID, d.location, d.ipAddress
HAVING COUNT(*) > 2;


-- Functionality 5: File Integrity Verification

-- 5a. all integrity checks
SELECT fm.fileName, fic.verified, fic.timestamp
FROM FileIntegrityCheck fic
JOIN FileMetadata fm ON fic.fileID = fm.fileID
ORDER BY fic.timestamp;

-- 5b. failed integrity checks
SELECT fm.fileName, fic.computedChecksum, fic.timestamp
FROM FileIntegrityCheck fic
JOIN FileMetadata fm ON fic.fileID = fm.fileID
WHERE fic.verified = FALSE;

-- 5c. integrity check pass/fail counts
SELECT
    SUM(CASE WHEN verified THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN NOT verified THEN 1 ELSE 0 END) AS failed
FROM FileIntegrityCheck;


-- Functionality 6: Audit Trail & System Monitoring

-- 6a. audit trail for session 1
SELECT at.action, at.timestamp
FROM AuditTrail at
WHERE at.sessionID = 1
ORDER BY at.timestamp;

-- 6b. audit action counts
SELECT action, COUNT(*) AS frequency
FROM AuditTrail
GROUP BY action
ORDER BY frequency DESC;

-- 6c. error log with session info
SELECT el.errorMessage, el.timestamp, fm.fileName
FROM ErrorLog el
JOIN UploadSession us ON el.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
ORDER BY el.timestamp;

-- 6d. sessions with most errors
SELECT us.sessionID, fm.fileName, COUNT(el.errorID) AS errorCount
FROM ErrorLog el
JOIN UploadSession us ON el.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
GROUP BY us.sessionID, fm.fileName
ORDER BY errorCount DESC;


-- Functionality 7: Member Activity & Analytics

-- 7a. total data uploaded per device
SELECT d.location, SUM(fm.fileSize) AS totalDataBytes
FROM Device d
JOIN UploadSession us ON d.deviceID = us.deviceID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
GROUP BY d.deviceID, d.location
ORDER BY totalDataBytes DESC;

-- 7b. file types uploaded
SELECT fm.mimeType, COUNT(*) AS uploadCount
FROM FileMetadata fm
GROUP BY fm.mimeType
ORDER BY uploadCount DESC;

-- 7c. uploads by hour
SELECT EXTRACT(HOUR FROM uploadTimestamp) AS hour, COUNT(*) AS uploads
FROM UploadSession
GROUP BY hour
ORDER BY hour;

-- 7d. tokens that expired without being downloaded
SELECT ot.tokenValue, fm.fileName, ot.expiryAt
FROM OneTimeToken ot
JOIN UploadSession us ON ot.sessionID = us.sessionID
JOIN FileMetadata fm ON us.sessionID = fm.sessionID
WHERE ot.status = 'EXPIRED';

-- 7e. all members
SELECT * FROM Member;

-- 7f. all devices
SELECT * FROM Device;

-- 7g. all expiry policies
SELECT * FROM ExpiryPolicy;

-- 7h. all system admins
SELECT * FROM SystemAdmin;
