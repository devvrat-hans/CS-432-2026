CREATE TABLE IF NOT EXISTS Member (
    memberID INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0),
    image TEXT,
    email TEXT NOT NULL UNIQUE,
    contactNumber TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Device (
    deviceID INTEGER PRIMARY KEY,
    location TEXT NOT NULL,
    deviceType TEXT NOT NULL,
    ipAddress TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ExpiryPolicy (
    policyID INTEGER PRIMARY KEY,
    maxLifetimeMinutes INTEGER NOT NULL CHECK (maxLifetimeMinutes > 0),
    deleteAfterFirstDownload INTEGER NOT NULL CHECK (deleteAfterFirstDownload IN (0, 1))
);

CREATE TABLE IF NOT EXISTS UploadSession (
    sessionID INTEGER PRIMARY KEY,
    deviceID INTEGER NOT NULL,
    policyID INTEGER NOT NULL,
    uploadTimestamp TEXT NOT NULL,
    expiryTimestamp TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'DOWNLOADED', 'EXPIRED')),
    FOREIGN KEY (deviceID) REFERENCES Device(deviceID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (policyID) REFERENCES ExpiryPolicy(policyID) ON DELETE RESTRICT ON UPDATE CASCADE,
    CHECK (expiryTimestamp > uploadTimestamp)
);

CREATE TABLE IF NOT EXISTS FileMetadata (
    fileID INTEGER PRIMARY KEY,
    sessionID INTEGER NOT NULL,
    fileName TEXT NOT NULL,
    fileSize INTEGER NOT NULL CHECK (fileSize > 0),
    mimeType TEXT NOT NULL,
    checksum TEXT NOT NULL,
    storagePath TEXT NOT NULL,
    FOREIGN KEY (sessionID) REFERENCES UploadSession(sessionID) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS OneTimeToken (
    tokenID INTEGER PRIMARY KEY,
    sessionID INTEGER NOT NULL UNIQUE,
    tokenValue TEXT NOT NULL UNIQUE,
    createdAt TEXT NOT NULL,
    expiryAt TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'USED', 'EXPIRED')),
    FOREIGN KEY (sessionID) REFERENCES UploadSession(sessionID) ON DELETE CASCADE ON UPDATE CASCADE,
    CHECK (expiryAt > createdAt)
);

CREATE TABLE IF NOT EXISTS DownloadLog (
    downloadID INTEGER PRIMARY KEY,
    tokenID INTEGER NOT NULL,
    downloadTime TEXT NOT NULL,
    userDeviceInfo TEXT NOT NULL,
    FOREIGN KEY (tokenID) REFERENCES OneTimeToken(tokenID) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS RateLimitLog (
    requestID INTEGER PRIMARY KEY,
    deviceID INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    eventType TEXT NOT NULL,
    FOREIGN KEY (deviceID) REFERENCES Device(deviceID) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FileIntegrityCheck (
    checkID INTEGER PRIMARY KEY,
    fileID INTEGER NOT NULL,
    computedChecksum TEXT NOT NULL,
    verified INTEGER NOT NULL CHECK (verified IN (0, 1)),
    timestamp TEXT NOT NULL,
    FOREIGN KEY (fileID) REFERENCES FileMetadata(fileID) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS SystemAdmin (
    adminID INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ErrorLog (
    errorID INTEGER PRIMARY KEY,
    sessionID INTEGER NOT NULL,
    errorMessage TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (sessionID) REFERENCES UploadSession(sessionID) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS AuditTrail (
    auditID INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    sessionID INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (sessionID) REFERENCES UploadSession(sessionID) ON DELETE CASCADE ON UPDATE CASCADE
);
