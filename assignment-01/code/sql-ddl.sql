CREATE TABLE Member (
    memberID INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL CHECK (age > 0),
    image VARCHAR(255),
    email VARCHAR(150) NOT NULL UNIQUE,
    contactNumber VARCHAR(20) NOT NULL
);

CREATE TABLE Device (
    deviceID INT PRIMARY KEY,
    location VARCHAR(100) NOT NULL,
    deviceType VARCHAR(50) NOT NULL,
    ipAddress VARCHAR(45) NOT NULL
);

CREATE TABLE ExpiryPolicy (
    policyID INT PRIMARY KEY,
    maxLifetimeMinutes INT NOT NULL CHECK (maxLifetimeMinutes > 0),
    deleteAfterFirstDownload BOOLEAN NOT NULL
);

CREATE TABLE UploadSession (
    sessionID INT PRIMARY KEY,
    memberID INT NOT NULL,
    deviceID INT NOT NULL,
    policyID INT NOT NULL,
    uploadTimestamp TIMESTAMP NOT NULL,
    expiryTimestamp TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE','DOWNLOADED','EXPIRED')),
    
    CONSTRAINT fk_session_member
        FOREIGN KEY (memberID)
        REFERENCES Member(memberID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_session_device
        FOREIGN KEY (deviceID)
        REFERENCES Device(deviceID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_session_policy
        FOREIGN KEY (policyID)
        REFERENCES ExpiryPolicy(policyID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT chk_expiry_after_upload
        CHECK (expiryTimestamp > uploadTimestamp)
);

CREATE TABLE FileMetadata (
    fileID INT PRIMARY KEY,
    sessionID INT NOT NULL,
    fileName VARCHAR(255) NOT NULL,
    fileSize INT NOT NULL CHECK (fileSize > 0),
    mimeType VARCHAR(100) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    storagePath VARCHAR(255) NOT NULL,

    CONSTRAINT fk_file_session
        FOREIGN KEY (sessionID)
        REFERENCES UploadSession(sessionID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE OneTimeToken (
    tokenID INT PRIMARY KEY,
    sessionID INT NOT NULL UNIQUE,
    tokenValue VARCHAR(20) NOT NULL UNIQUE,
    createdAt TIMESTAMP NOT NULL,
    expiryAt TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE','USED','EXPIRED')),

    CONSTRAINT fk_token_session
        FOREIGN KEY (sessionID)
        REFERENCES UploadSession(sessionID)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT chk_token_expiry
        CHECK (expiryAt > createdAt)
);

CREATE TABLE DownloadLog (
    downloadID INT PRIMARY KEY,
    tokenID INT NOT NULL,
    downloadTime TIMESTAMP NOT NULL,
    userDeviceInfo VARCHAR(255) NOT NULL,

    CONSTRAINT fk_download_token
        FOREIGN KEY (tokenID)
        REFERENCES OneTimeToken(tokenID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE RateLimitLog (
    requestID INT PRIMARY KEY,
    deviceID INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    eventType VARCHAR(50) NOT NULL,

    CONSTRAINT fk_ratelimit_device
        FOREIGN KEY (deviceID)
        REFERENCES Device(deviceID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE FileIntegrityCheck (
    checkID INT PRIMARY KEY,
    fileID INT NOT NULL,
    computedChecksum VARCHAR(64) NOT NULL,
    verified BOOLEAN NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    CONSTRAINT fk_integrity_file
        FOREIGN KEY (fileID)
        REFERENCES FileMetadata(fileID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE SystemAdmin (
    adminID INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE ErrorLog (
    errorID INT PRIMARY KEY,
    sessionID INT NOT NULL,
    errorMessage VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    CONSTRAINT fk_error_session
        FOREIGN KEY (sessionID)
        REFERENCES UploadSession(sessionID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE AuditTrail (
    auditID INT PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    sessionID INT NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    CONSTRAINT fk_audit_session
        FOREIGN KEY (sessionID)
        REFERENCES UploadSession(sessionID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
