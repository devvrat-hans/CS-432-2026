-- 1a. Member
INSERT INTO Member (memberID, name, age, image, email, contactNumber) VALUES
(1, 'Aarav Sharma', 21, 'aarav_sharma.jpg', 'aarav.sharma@iitgn.ac.in', '+91-9876543210'),
(2, 'Priya Patel', 22, 'priya_patel.jpg', 'priya.patel@iitgn.ac.in', '+91-9876543211'),
(3, 'Rohan Gupta', 20, 'rohan_gupta.jpg', 'rohan.gupta@iitgn.ac.in', '+91-9876543212'),
(4, 'Sneha Reddy', 23, 'sneha_reddy.jpg', 'sneha.reddy@iitgn.ac.in', '+91-9876543213'),
(5, 'Vikram Singh', 24, 'vikram_singh.jpg', 'vikram.singh@iitgn.ac.in', '+91-9876543214'),
(6, 'Ananya Iyer', 19, 'ananya_iyer.jpg', 'ananya.iyer@iitgn.ac.in', '+91-9876543215'),
(7, 'Karthik Nair', 25, 'karthik_nair.jpg', 'karthik.nair@iitgn.ac.in', '+91-9876543216'),
(8, 'Meera Joshi', 22, 'meera_joshi.jpg', 'meera.joshi@iitgn.ac.in', '+91-9876543217'),
(9, 'Arjun Desai', 21, 'arjun_desai.jpg', 'arjun.desai@iitgn.ac.in', '+91-9876543218'),
(10, 'Divya Menon', 20, 'divya_menon.jpg', 'divya.menon@iitgn.ac.in', '+91-9876543219'),
(11, 'Rahul Verma', 23, 'rahul_verma.jpg', 'rahul.verma@iitgn.ac.in', '+91-9876543220'),
(12, 'Ishita Kapoor', 22, 'ishita_kapoor.jpg', 'ishita.kapoor@iitgn.ac.in', '+91-9876543221'),
(13, 'Siddharth Rao', 24, 'siddharth_rao.jpg', 'siddharth.rao@iitgn.ac.in', '+91-9876543222'),
(14, 'Neha Agarwal', 21, 'neha_agarwal.jpg', 'neha.agarwal@iitgn.ac.in', '+91-9876543223'),
(15, 'Amit Kulkarni', 20, 'amit_kulkarni.jpg', 'amit.kulkarni@iitgn.ac.in', '+91-9876543224');

-- 1b. Device
INSERT INTO Device (deviceID, location, deviceType, ipAddress) VALUES
(1, 'Central Library - Floor 1', 'Desktop', '10.0.1.101'),
(2, 'Central Library - Floor 2', 'Desktop', '10.0.1.102'),
(3, 'Central Library - Floor 3', 'Desktop', '10.0.1.103'),
(4, 'Computer Lab A - AB1', 'Desktop', '10.0.2.201'),
(5, 'Computer Lab B - AB1', 'Desktop', '10.0.2.202'),
(6, 'Computer Lab C - AB2', 'Desktop', '10.0.2.203'),
(7, 'Cybercafe - Hostel Block A', 'Desktop', '10.0.3.301'),
(8, 'Cybercafe - Hostel Block B', 'Desktop', '10.0.3.302'),
(9, 'Student Activity Center', 'Kiosk', '10.0.4.401'),
(10, 'Admin Building Lobby', 'Kiosk', '10.0.4.402'),
(11, 'Placement Cell Office', 'Desktop', '10.0.5.501'),
(12, 'Workshop Lab - AB3', 'Desktop', '10.0.5.502');

-- 1c. ExpiryPolicy
INSERT INTO ExpiryPolicy (policyID, maxLifetimeMinutes, deleteAfterFirstDownload) VALUES
(1, 5, TRUE),
(2, 10, TRUE),
(3, 15, TRUE),
(4, 30, TRUE),
(5, 60, TRUE),
(6, 5, FALSE),
(7, 10, FALSE),
(8, 15, FALSE),
(9, 30, FALSE),
(10, 60, FALSE);

-- 1d. UploadSession
INSERT INTO UploadSession (sessionID, memberID, deviceID, policyID, uploadTimestamp, expiryTimestamp, status) VALUES
(1,  1,  1, 1, '2026-02-10 09:00:00', '2026-02-10 09:05:00', 'DOWNLOADED'),
(2,  2,  2, 2, '2026-02-10 09:15:00', '2026-02-10 09:25:00', 'DOWNLOADED'),
(3,  3,  4, 3, '2026-02-10 10:00:00', '2026-02-10 10:15:00', 'EXPIRED'),
(4,  4,  5, 1, '2026-02-10 10:30:00', '2026-02-10 10:35:00', 'DOWNLOADED'),
(5,  5,  7, 4, '2026-02-10 11:00:00', '2026-02-10 11:30:00', 'ACTIVE'),
(6,  6,  3, 2, '2026-02-10 11:30:00', '2026-02-10 11:40:00', 'EXPIRED'),
(7,  7,  8, 5, '2026-02-10 12:00:00', '2026-02-10 13:00:00', 'DOWNLOADED'),
(8,  8,  6, 1, '2026-02-10 12:30:00', '2026-02-10 12:35:00', 'DOWNLOADED'),
(9,  9,  9, 3, '2026-02-10 13:00:00', '2026-02-10 13:15:00', 'EXPIRED'),
(10, 10, 10, 2, '2026-02-10 13:30:00', '2026-02-10 13:40:00', 'DOWNLOADED'),
(11, 11, 11, 4, '2026-02-10 14:00:00', '2026-02-10 14:30:00', 'ACTIVE'),
(12, 12, 12, 1, '2026-02-10 14:30:00', '2026-02-10 14:35:00', 'DOWNLOADED'),
(13, 1,  2,  5, '2026-02-11 09:00:00', '2026-02-11 10:00:00', 'DOWNLOADED'),
(14, 3,  4,  2, '2026-02-11 09:30:00', '2026-02-11 09:40:00', 'EXPIRED'),
(15, 5,  7,  3, '2026-02-11 10:00:00', '2026-02-11 10:15:00', 'DOWNLOADED'),
(16, 7,  1,  1, '2026-02-11 10:30:00', '2026-02-11 10:35:00', 'DOWNLOADED'),
(17, 13, 3,  4, '2026-02-11 11:00:00', '2026-02-11 11:30:00', 'ACTIVE'),
(18, 14, 6,  2, '2026-02-11 11:30:00', '2026-02-11 11:40:00', 'DOWNLOADED'),
(19, 15, 8,  5, '2026-02-11 12:00:00', '2026-02-11 13:00:00', 'EXPIRED'),
(20, 2,  9,  1, '2026-02-11 12:30:00', '2026-02-11 12:35:00', 'ACTIVE');

-- 1e. FileMetadata
INSERT INTO FileMetadata (fileID, sessionID, fileName, fileSize, mimeType, checksum, storagePath) VALUES
(1,  1,  'lecture_notes_dbms.pdf',       2048576,  'application/pdf',       'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2', '/tmp/blinddrop/sess_1/lecture_notes_dbms.pdf'),
(2,  2,  'assignment_solution.docx',     1536000,  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3', '/tmp/blinddrop/sess_2/assignment_solution.docx'),
(3,  3,  'project_report.pdf',           3145728,  'application/pdf',       'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', '/tmp/blinddrop/sess_3/project_report.pdf'),
(4,  4,  'resume_sneha.pdf',             512000,   'application/pdf',       'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5', '/tmp/blinddrop/sess_4/resume_sneha.pdf'),
(5,  5,  'presentation_ml.pptx',         5242880,  'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6', '/tmp/blinddrop/sess_5/presentation_ml.pptx'),
(6,  6,  'code_snippet.py',              4096,     'text/x-python',         'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1', '/tmp/blinddrop/sess_6/code_snippet.py'),
(7,  7,  'dataset_analytics.csv',        8388608,  'text/csv',              'a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3', '/tmp/blinddrop/sess_7/dataset_analytics.csv'),
(8,  8,  'photo_id_card.jpg',            1048576,  'image/jpeg',            'b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4', '/tmp/blinddrop/sess_8/photo_id_card.jpg'),
(9,  9,  'lab_manual.pdf',               2621440,  'application/pdf',       'c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5', '/tmp/blinddrop/sess_9/lab_manual.pdf'),
(10, 10, 'spreadsheet_budget.xlsx',      768000,   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'd5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6', '/tmp/blinddrop/sess_10/spreadsheet_budget.xlsx'),
(11, 11, 'thesis_draft.pdf',             4194304,  'application/pdf',       'e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1', '/tmp/blinddrop/sess_11/thesis_draft.pdf'),
(12, 12, 'certificate_scan.png',         2097152,  'image/png',             'f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2', '/tmp/blinddrop/sess_12/certificate_scan.png'),
(13, 13, 'research_paper.pdf',           3670016,  'application/pdf',       'a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4', '/tmp/blinddrop/sess_13/research_paper.pdf'),
(14, 14, 'notes_algebra.pdf',            1024000,  'application/pdf',       'b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5', '/tmp/blinddrop/sess_14/notes_algebra.pdf'),
(15, 15, 'video_clip.mp4',               10485760, 'video/mp4',             'c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6', '/tmp/blinddrop/sess_15/video_clip.mp4'),
(16, 16, 'form_filled.pdf',              256000,   'application/pdf',       'd6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7', '/tmp/blinddrop/sess_16/form_filled.pdf'),
(17, 17, 'slides_networking.pptx',       6291456,  'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2', '/tmp/blinddrop/sess_17/slides_networking.pptx'),
(18, 18, 'marksheet_scan.jpg',           1572864,  'image/jpeg',            'f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3', '/tmp/blinddrop/sess_18/marksheet_scan.jpg'),
(19, 19, 'ebook_chapter.pdf',            2359296,  'application/pdf',       'a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5', '/tmp/blinddrop/sess_19/ebook_chapter.pdf'),
(20, 20, 'invoice_receipt.pdf',          384000,   'application/pdf',       'b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6d7e8f3a4b5c6', '/tmp/blinddrop/sess_20/invoice_receipt.pdf');

-- 1f. OneTimeToken
INSERT INTO OneTimeToken (tokenID, sessionID, tokenValue, createdAt, expiryAt, status) VALUES
(1,  1,  'TKN-A1B2C3D4E5',  '2026-02-10 09:00:00', '2026-02-10 09:05:00', 'USED'),
(2,  2,  'TKN-F6G7H8I9J0',  '2026-02-10 09:15:00', '2026-02-10 09:25:00', 'USED'),
(3,  3,  'TKN-K1L2M3N4O5',  '2026-02-10 10:00:00', '2026-02-10 10:15:00', 'EXPIRED'),
(4,  4,  'TKN-P6Q7R8S9T0',  '2026-02-10 10:30:00', '2026-02-10 10:35:00', 'USED'),
(5,  5,  'TKN-U1V2W3X4Y5',  '2026-02-10 11:00:00', '2026-02-10 11:30:00', 'ACTIVE'),
(6,  6,  'TKN-Z6A7B8C9D0',  '2026-02-10 11:30:00', '2026-02-10 11:40:00', 'EXPIRED'),
(7,  7,  'TKN-E1F2G3H4I5',  '2026-02-10 12:00:00', '2026-02-10 13:00:00', 'USED'),
(8,  8,  'TKN-J6K7L8M9N0',  '2026-02-10 12:30:00', '2026-02-10 12:35:00', 'USED'),
(9,  9,  'TKN-O1P2Q3R4S5',  '2026-02-10 13:00:00', '2026-02-10 13:15:00', 'EXPIRED'),
(10, 10, 'TKN-T6U7V8W9X0',  '2026-02-10 13:30:00', '2026-02-10 13:40:00', 'USED'),
(11, 11, 'TKN-Y1Z2A3B4C5',  '2026-02-10 14:00:00', '2026-02-10 14:30:00', 'ACTIVE'),
(12, 12, 'TKN-D6E7F8G9H0',  '2026-02-10 14:30:00', '2026-02-10 14:35:00', 'USED'),
(13, 13, 'TKN-I1J2K3L4M5',  '2026-02-11 09:00:00', '2026-02-11 10:00:00', 'USED'),
(14, 14, 'TKN-N6O7P8Q9R0',  '2026-02-11 09:30:00', '2026-02-11 09:40:00', 'EXPIRED'),
(15, 15, 'TKN-S1T2U3V4W5',  '2026-02-11 10:00:00', '2026-02-11 10:15:00', 'USED'),
(16, 16, 'TKN-X6Y7Z8A9B0',  '2026-02-11 10:30:00', '2026-02-11 10:35:00', 'USED'),
(17, 17, 'TKN-C1D2E3F4G5',  '2026-02-11 11:00:00', '2026-02-11 11:30:00', 'ACTIVE'),
(18, 18, 'TKN-H6I7J8K9L0',  '2026-02-11 11:30:00', '2026-02-11 11:40:00', 'USED'),
(19, 19, 'TKN-M1N2O3P4Q5',  '2026-02-11 12:00:00', '2026-02-11 13:00:00', 'EXPIRED'),
(20, 20, 'TKN-R6S7T8U9V0',  '2026-02-11 12:30:00', '2026-02-11 12:35:00', 'ACTIVE');

-- 1g. DownloadLog
INSERT INTO DownloadLog (downloadID, tokenID, downloadTime, userDeviceInfo) VALUES
(1,  1,  '2026-02-10 09:02:30', 'iPhone 15 Pro - Safari 19 - iOS 19.2'),
(2,  2,  '2026-02-10 09:18:45', 'Samsung Galaxy S25 - Chrome 130 - Android 16'),
(3,  4,  '2026-02-10 10:32:10', 'MacBook Air M4 - Safari 19 - macOS 16'),
(4,  7,  '2026-02-10 12:45:00', 'Dell Inspiron - Firefox 135 - Windows 12'),
(5,  8,  '2026-02-10 12:33:20', 'iPad Pro - Safari 19 - iPadOS 19'),
(6,  10, '2026-02-10 13:35:50', 'OnePlus 13 - Chrome 130 - Android 16'),
(7,  12, '2026-02-10 14:32:15', 'Google Pixel 10 - Chrome 130 - Android 16'),
(8,  13, '2026-02-11 09:30:00', 'HP Pavilion - Edge 130 - Windows 12'),
(9,  15, '2026-02-11 10:08:30', 'Lenovo ThinkPad - Firefox 135 - Ubuntu 24.04'),
(10, 16, '2026-02-11 10:33:00', 'iPhone 14 - Safari 18 - iOS 18.5'),
(11, 18, '2026-02-11 11:35:20', 'Xiaomi 15 - Chrome 130 - Android 16'),
(12, 1,  '2026-02-10 09:03:00', 'iPad Mini - Safari 19 - iPadOS 19');

-- 1h. RateLimitLog
INSERT INTO RateLimitLog (requestID, deviceID, timestamp, eventType) VALUES
(1,  1,  '2026-02-10 09:00:00', 'UPLOAD'),
(2,  2,  '2026-02-10 09:15:00', 'UPLOAD'),
(3,  4,  '2026-02-10 10:00:00', 'UPLOAD'),
(4,  5,  '2026-02-10 10:30:00', 'UPLOAD'),
(5,  7,  '2026-02-10 11:00:00', 'UPLOAD'),
(6,  3,  '2026-02-10 11:30:00', 'UPLOAD'),
(7,  8,  '2026-02-10 12:00:00', 'UPLOAD'),
(8,  6,  '2026-02-10 12:30:00', 'UPLOAD'),
(9,  1,  '2026-02-10 12:31:00', 'UPLOAD'),
(10, 1,  '2026-02-10 12:32:00', 'UPLOAD'),
(11, 1,  '2026-02-10 12:33:00', 'RATE_LIMIT_HIT'),
(12, 9,  '2026-02-10 13:00:00', 'UPLOAD'),
(13, 10, '2026-02-10 13:30:00', 'UPLOAD'),
(14, 7,  '2026-02-11 10:00:00', 'UPLOAD'),
(15, 7,  '2026-02-11 10:01:00', 'RATE_LIMIT_HIT');

-- 1i. FileIntegrityCheck
INSERT INTO FileIntegrityCheck (checkID, fileID, computedChecksum, verified, timestamp) VALUES
(1,  1,  'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2', TRUE,  '2026-02-10 09:00:05'),
(2,  2,  'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3', TRUE,  '2026-02-10 09:15:05'),
(3,  3,  'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', TRUE,  '2026-02-10 10:00:05'),
(4,  4,  'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5', TRUE,  '2026-02-10 10:30:05'),
(5,  5,  'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6', TRUE,  '2026-02-10 11:00:05'),
(6,  6,  'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1', TRUE,  '2026-02-10 11:30:05'),
(7,  7,  'a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3', TRUE,  '2026-02-10 12:00:05'),
(8,  8,  'b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4', TRUE,  '2026-02-10 12:30:05'),
(9,  9,  'c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5', TRUE,  '2026-02-10 13:00:05'),
(10, 10, 'd5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6', TRUE,  '2026-02-10 13:30:05'),
(11, 11, 'e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1', TRUE,  '2026-02-10 14:00:05'),
(12, 12, 'f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2', TRUE,  '2026-02-10 14:30:05'),
(13, 1,  'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', FALSE, '2026-02-10 09:04:00'),
(14, 13, 'a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4', TRUE,  '2026-02-11 09:00:05'),
(15, 15, 'c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6', TRUE,  '2026-02-11 10:00:05');

-- 1j. SystemAdmin
INSERT INTO SystemAdmin (adminID, name, email) VALUES
(1, 'Dr. Yogesh Meena', 'yogesh.meena@iitgn.ac.in'),
(2, 'Rajesh Kumar', 'rajesh.kumar@iitgn.ac.in'),
(3, 'Sunita Devi', 'sunita.devi@iitgn.ac.in'),
(4, 'Manish Tiwari', 'manish.tiwari@iitgn.ac.in'),
(5, 'Pooja Saxena', 'pooja.saxena@iitgn.ac.in'),
(6, 'Deepak Chauhan', 'deepak.chauhan@iitgn.ac.in'),
(7, 'Kavita Bhatt', 'kavita.bhatt@iitgn.ac.in'),
(8, 'Nitin Arora', 'nitin.arora@iitgn.ac.in'),
(9, 'Swati Mishra', 'swati.mishra@iitgn.ac.in'),
(10, 'Anil Pandey', 'anil.pandey@iitgn.ac.in');

-- 1k. ErrorLog
INSERT INTO ErrorLog (errorID, sessionID, errorMessage, timestamp) VALUES
(1,  3,  'File upload timed out - connection reset by peer',         '2026-02-10 10:01:00'),
(2,  6,  'Token expired before download attempt',                     '2026-02-10 11:41:00'),
(3,  9,  'File integrity check failed - checksum mismatch',           '2026-02-10 13:05:00'),
(4,  3,  'Retry failed - session already expired',                    '2026-02-10 10:16:00'),
(5,  14, 'Upload rejected - file size exceeds 50MB limit',            '2026-02-11 09:31:00'),
(6,  19, 'Storage write error - disk quota exceeded temporarily',     '2026-02-11 12:01:00'),
(7,  6,  'Download attempt on expired session',                       '2026-02-10 11:42:00'),
(8,  9,  'Token validation failed - invalid token format',            '2026-02-10 13:10:00'),
(9,  14, 'Session cleanup failed - file already deleted',             '2026-02-11 09:45:00'),
(10, 19, 'Automatic expiry triggered - file removed from storage',    '2026-02-11 13:01:00'),
(11, 3,  'Rate limit exceeded for device at location Library Floor3', '2026-02-10 10:02:00'),
(12, 6,  'Concurrent download attempt blocked',                       '2026-02-10 11:39:00');

-- 1l. AuditTrail
INSERT INTO AuditTrail (auditID, action, sessionID, timestamp) VALUES
(1,  'FILE_UPLOADED',        1,  '2026-02-10 09:00:00'),
(2,  'TOKEN_GENERATED',      1,  '2026-02-10 09:00:01'),
(3,  'FILE_DOWNLOADED',      1,  '2026-02-10 09:02:30'),
(4,  'TOKEN_USED',           1,  '2026-02-10 09:02:30'),
(5,  'FILE_DELETED',         1,  '2026-02-10 09:02:31'),
(6,  'FILE_UPLOADED',        2,  '2026-02-10 09:15:00'),
(7,  'TOKEN_GENERATED',      2,  '2026-02-10 09:15:01'),
(8,  'FILE_DOWNLOADED',      2,  '2026-02-10 09:18:45'),
(9,  'FILE_UPLOADED',        3,  '2026-02-10 10:00:00'),
(10, 'TOKEN_GENERATED',      3,  '2026-02-10 10:00:01'),
(11, 'SESSION_EXPIRED',      3,  '2026-02-10 10:15:00'),
(12, 'FILE_AUTO_DELETED',    3,  '2026-02-10 10:15:01'),
(13, 'FILE_UPLOADED',        5,  '2026-02-10 11:00:00'),
(14, 'TOKEN_GENERATED',      5,  '2026-02-10 11:00:01'),
(15, 'FILE_UPLOADED',        7,  '2026-02-10 12:00:00'),
(16, 'FILE_DOWNLOADED',      7,  '2026-02-10 12:45:00'),
(17, 'FILE_UPLOADED',        13, '2026-02-11 09:00:00'),
(18, 'FILE_DOWNLOADED',      13, '2026-02-11 09:30:00'),
(19, 'INTEGRITY_CHECK_FAIL', 3,  '2026-02-10 10:05:00'),
(20, 'RATE_LIMIT_TRIGGERED', 5,  '2026-02-10 11:05:00');
