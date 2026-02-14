# Query Results - Blind Drop

## Functionality 1: File Upload & Session Creation

### 1a. all active upload sessions

```
 sessionid |     name      |        filename        | status
         5 | Vikram Singh  | presentation_ml.pptx   | ACTIVE
         5 | Vikram Singh  | ml_dataset.csv         | ACTIVE
         5 | Vikram Singh  | ml_notebook.py         | ACTIVE
        11 | Rahul Verma   | thesis_draft.pdf       | ACTIVE
        17 | Siddharth Rao | slides_networking.pptx | ACTIVE
        20 | Priya Patel   | invoice_receipt.pdf    | ACTIVE
(6 rows)
```

### 1b. token for an active session

```
   tokenvalue   |      expiryat       |       filename
 TKN-U1V2W3X4Y5 | 2026-02-10 11:30:00 | presentation_ml.pptx
 TKN-U1V2W3X4Y5 | 2026-02-10 11:30:00 | ml_dataset.csv
 TKN-U1V2W3X4Y5 | 2026-02-10 11:30:00 | ml_notebook.py
(3 rows)
```

### 1c. uploads per device

```
          location          | totaluploads
 Cybercafe - Hostel Block B |            2
 Student Activity Center    |            2
 Central Library - Floor 3  |            2
 Computer Lab C - AB2       |            2
 Central Library - Floor 2  |            2
 Cybercafe - Hostel Block A |            2
 Central Library - Floor 1  |            2
 Computer Lab A - AB1       |            2
 Computer Lab B - AB1       |            1
 Workshop Lab - AB3         |            1
 Admin Building Lobby       |            1
 Placement Cell Office      |            1
(12 rows)
```


## Functionality 2: File Download Using One-Time Token

### 2a. validate token and get file info

```
   tokenvalue   | status |       filename       |                storagepath
 TKN-U1V2W3X4Y5 | ACTIVE | presentation_ml.pptx | /tmp/blinddrop/sess_5/presentation_ml.pptx
 TKN-U1V2W3X4Y5 | ACTIVE | ml_dataset.csv       | /tmp/blinddrop/sess_5/ml_dataset.csv
 TKN-U1V2W3X4Y5 | ACTIVE | ml_notebook.py       | /tmp/blinddrop/sess_5/ml_notebook.py
(3 rows)
```

### 2b. download history

```
 downloadid |    downloadtime     |                userdeviceinfo                |         filename
         11 | 2026-02-11 11:35:20 | Xiaomi 15 - Chrome 130 - Android 16          | marksheet_scan.jpg
         10 | 2026-02-11 10:33:00 | iPhone 14 - Safari 18 - iOS 18.5             | form_filled.pdf
          9 | 2026-02-11 10:08:30 | Lenovo ThinkPad - Firefox 135 - Ubuntu 24.04 | video_clip.mp4
          8 | 2026-02-11 09:30:00 | HP Pavilion - Edge 130 - Windows 12          | research_paper.pdf
          8 | 2026-02-11 09:30:00 | HP Pavilion - Edge 130 - Windows 12          | research_data.csv
          7 | 2026-02-10 14:32:15 | Google Pixel 10 - Chrome 130 - Android 16    | certificate_scan.png
          6 | 2026-02-10 13:35:50 | OnePlus 13 - Chrome 130 - Android 16         | spreadsheet_budget.xlsx
          4 | 2026-02-10 12:45:00 | Dell Inspiron - Firefox 135 - Windows 12     | dataset_analytics.csv
          4 | 2026-02-10 12:45:00 | Dell Inspiron - Firefox 135 - Windows 12     | analytics_report.pdf
          5 | 2026-02-10 12:33:20 | iPad Pro - Safari 19 - iPadOS 19             | photo_id_card.jpg
          3 | 2026-02-10 10:32:10 | MacBook Air M4 - Safari 19 - macOS 16        | resume_sneha.pdf
          2 | 2026-02-10 09:18:45 | Samsung Galaxy S25 - Chrome 130 - Android 16 | assignment_solution.docx
         12 | 2026-02-10 09:03:00 | iPad Mini - Safari 19 - iPadOS 19            | lecture_slides_dbms.pptx
         12 | 2026-02-10 09:03:00 | iPad Mini - Safari 19 - iPadOS 19            | lecture_notes_dbms.pdf
          1 | 2026-02-10 09:02:30 | iPhone 15 Pro - Safari 19 - iOS 19.2         | lecture_notes_dbms.pdf
          1 | 2026-02-10 09:02:30 | iPhone 15 Pro - Safari 19 - iOS 19.2         | lecture_slides_dbms.pptx
(16 rows)
```

### 2c. files downloaded within 5 minutes of upload

```
         filename         |   uploadtimestamp   |    downloadtime
 lecture_notes_dbms.pdf   | 2026-02-10 09:00:00 | 2026-02-10 09:02:30
 lecture_slides_dbms.pptx | 2026-02-10 09:00:00 | 2026-02-10 09:02:30
 assignment_solution.docx | 2026-02-10 09:15:00 | 2026-02-10 09:18:45
 resume_sneha.pdf         | 2026-02-10 10:30:00 | 2026-02-10 10:32:10
 photo_id_card.jpg        | 2026-02-10 12:30:00 | 2026-02-10 12:33:20
 certificate_scan.png     | 2026-02-10 14:30:00 | 2026-02-10 14:32:15
 form_filled.pdf          | 2026-02-11 10:30:00 | 2026-02-11 10:33:00
 lecture_notes_dbms.pdf   | 2026-02-10 09:00:00 | 2026-02-10 09:03:00
 lecture_slides_dbms.pptx | 2026-02-10 09:00:00 | 2026-02-10 09:03:00
(9 rows)
```


## Functionality 3: Auto-Expiry & File Cleanup

### 3a. all expired sessions

```
 sessionid |     name      |      filename      |   expirytimestamp
         3 | Rohan Gupta   | project_report.pdf | 2026-02-10 10:15:00
         6 | Ananya Iyer   | code_snippet.py    | 2026-02-10 11:40:00
         9 | Arjun Desai   | lab_manual.pdf     | 2026-02-10 13:15:00
        14 | Rohan Gupta   | notes_algebra.pdf  | 2026-02-11 09:40:00
        19 | Amit Kulkarni | ebook_chapter.pdf  | 2026-02-11 13:00:00
(5 rows)
```

### 3b. active sessions that are past expiry (need cleanup)

```
 sessionid |        filename        |   expirytimestamp
         5 | presentation_ml.pptx   | 2026-02-10 11:30:00
         5 | ml_dataset.csv         | 2026-02-10 11:30:00
         5 | ml_notebook.py         | 2026-02-10 11:30:00
        11 | thesis_draft.pdf       | 2026-02-10 14:30:00
        17 | slides_networking.pptx | 2026-02-11 11:30:00
        20 | invoice_receipt.pdf    | 2026-02-11 12:35:00
(6 rows)
```

### 3c. session status counts

```
   status   | sessioncount
 DOWNLOADED |           11
 EXPIRED    |            5
 ACTIVE     |            4
(3 rows)
```

### 3d. sessions per expiry policy

```
 policyid | maxlifetimeminutes | deleteafterfirstdownload | totalsessions
        1 |                  5 | t                        |             6
        2 |                 10 | t                        |             5
        3 |                 15 | t                        |             3
        4 |                 30 | t                        |             3
        5 |                 60 | t                        |             3
        6 |                  5 | f                        |             0
        7 |                 10 | f                        |             0
        8 |                 15 | f                        |             0
        9 |                 30 | f                        |             0
       10 |                 60 | f                        |             0
(10 rows)
```


## Functionality 4: Rate Limiting & Abuse Prevention

### 4a. devices that hit rate limits

```
          location          | ipaddress  |      timestamp
 Central Library - Floor 1  | 10.0.1.101 | 2026-02-10 12:33:00
 Cybercafe - Hostel Block A | 10.0.3.301 | 2026-02-11 10:01:00
(2 rows)
```

### 4b. upload count per device

```
          location          | uploadcount
 Central Library - Floor 1  |           3
 Cybercafe - Hostel Block A |           2
 Central Library - Floor 3  |           1
 Computer Lab A - AB1       |           1
 Computer Lab B - AB1       |           1
 Computer Lab C - AB2       |           1
 Cybercafe - Hostel Block B |           1
 Student Activity Center    |           1
 Admin Building Lobby       |           1
 Central Library - Floor 2  |           1
(10 rows)
```

### 4c. devices with more than 2 uploads

```
         location          | ipaddress  | uploadcount
 Central Library - Floor 1 | 10.0.1.101 |           3
(1 row)
```


## Functionality 5: File Integrity Verification

### 5a. all integrity checks

```
         filename         | verified |      timestamp
 lecture_notes_dbms.pdf   | t        | 2026-02-10 09:00:05
 lecture_slides_dbms.pptx | t        | 2026-02-10 09:00:06
 lecture_notes_dbms.pdf   | f        | 2026-02-10 09:04:00
 assignment_solution.docx | t        | 2026-02-10 09:15:05
 project_report.pdf       | t        | 2026-02-10 10:00:05
 resume_sneha.pdf         | t        | 2026-02-10 10:30:05
 presentation_ml.pptx     | t        | 2026-02-10 11:00:05
 ml_dataset.csv           | t        | 2026-02-10 11:00:06
 ml_notebook.py           | t        | 2026-02-10 11:00:07
 code_snippet.py          | t        | 2026-02-10 11:30:05
 dataset_analytics.csv    | t        | 2026-02-10 12:00:05
 photo_id_card.jpg        | t        | 2026-02-10 12:30:05
 lab_manual.pdf           | t        | 2026-02-10 13:00:05
 research_paper.pdf       | t        | 2026-02-11 09:00:05
 video_clip.mp4           | t        | 2026-02-11 10:00:05
(15 rows)
```

### 5b. failed integrity checks

```
        filename        |                         computedchecksum                         |      timestamp
 lecture_notes_dbms.pdf | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | 2026-02-10 09:04:00
(1 row)
```

### 5c. integrity check pass/fail counts

```
 passed | failed
     14 |      1
(1 row)
```


## Functionality 6: Audit Trail & System Monitoring

### 6a. audit trail for session 1

```
     action      |      timestamp
 FILE_UPLOADED   | 2026-02-10 09:00:00
 TOKEN_GENERATED | 2026-02-10 09:00:01
 FILE_DOWNLOADED | 2026-02-10 09:02:30
 TOKEN_USED      | 2026-02-10 09:02:30
 FILE_DELETED    | 2026-02-10 09:02:31
(5 rows)
```

### 6b. audit action counts

```
        action        | frequency
 FILE_UPLOADED        |         6
 TOKEN_GENERATED      |         4
 FILE_DOWNLOADED      |         4
 FILE_AUTO_DELETED    |         1
 RATE_LIMIT_TRIGGERED |         1
 SESSION_EXPIRED      |         1
 TOKEN_USED           |         1
 FILE_DELETED         |         1
 INTEGRITY_CHECK_FAIL |         1
(9 rows)
```

### 6c. error log with session info

```
                       errormessage                        |      timestamp      |      filename
 File upload timed out - connection reset by peer          | 2026-02-10 10:01:00 | project_report.pdf
 Rate limit exceeded for device at location Library Floor3 | 2026-02-10 10:02:00 | project_report.pdf
 Retry failed - session already expired                    | 2026-02-10 10:16:00 | project_report.pdf
 Concurrent download attempt blocked                       | 2026-02-10 11:39:00 | code_snippet.py
 Token expired before download attempt                     | 2026-02-10 11:41:00 | code_snippet.py
 Download attempt on expired session                       | 2026-02-10 11:42:00 | code_snippet.py
 File integrity check failed - checksum mismatch           | 2026-02-10 13:05:00 | lab_manual.pdf
 Token validation failed - invalid token format            | 2026-02-10 13:10:00 | lab_manual.pdf
 Upload rejected - file size exceeds 50MB limit            | 2026-02-11 09:31:00 | notes_algebra.pdf
 Session cleanup failed - file already deleted             | 2026-02-11 09:45:00 | notes_algebra.pdf
 Storage write error - disk quota exceeded temporarily     | 2026-02-11 12:01:00 | ebook_chapter.pdf
 Automatic expiry triggered - file removed from storage    | 2026-02-11 13:01:00 | ebook_chapter.pdf
(12 rows)
```

### 6d. sessions with most errors

```
 sessionid |      filename      | errorcount
         3 | project_report.pdf |          3
         6 | code_snippet.py    |          3
         9 | lab_manual.pdf     |          2
        14 | notes_algebra.pdf  |          2
        19 | ebook_chapter.pdf  |          2
(5 rows)
```


## Functionality 7: Member Activity & Analytics

### 7a. upload count per member

```
     name      | totaluploads
 Karthik Nair  |            2
 Rohan Gupta   |            2
 Aarav Sharma  |            2
 Vikram Singh  |            2
 Priya Patel   |            2
 Rahul Verma   |            1
 Arjun Desai   |            1
 Amit Kulkarni |            1
 Ishita Kapoor |            1
 Sneha Reddy   |            1
 Meera Joshi   |            1
 Divya Menon   |            1
 Ananya Iyer   |            1
 Neha Agarwal  |            1
 Siddharth Rao |            1
(15 rows)
```

### 7b. file types uploaded

```
                                 mimetype                                  | uploadcount
 application/pdf                                                           |          11
 application/vnd.openxmlformats-officedocument.presentationml.presentation |           3
 text/csv                                                                  |           3
 image/jpeg                                                                |           2
 text/x-python                                                             |           2
 application/vnd.openxmlformats-officedocument.wordprocessingml.document   |           1
 image/png                                                                 |           1
 video/mp4                                                                 |           1
 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet         |           1
(9 rows)
```

### 7c. uploads by hour

```
 hour | uploads
    9 |       4
   10 |       4
   11 |       4
   12 |       4
   13 |       2
   14 |       2
(6 rows)
```

### 7d. members who never uploaded

```
 name | email
(0 rows)
```

### 7e. all members

```
 memberid |     name      | age |       image       |           email           | contactnumber
        1 | Aarav Sharma  |  21 | aarav_sharma.jpg  | aarav.sharma@iitgn.ac.in  | +91-9876543210
        2 | Priya Patel   |  22 | priya_patel.jpg   | priya.patel@iitgn.ac.in   | +91-9876543211
        3 | Rohan Gupta   |  20 | rohan_gupta.jpg   | rohan.gupta@iitgn.ac.in   | +91-9876543212
        4 | Sneha Reddy   |  23 | sneha_reddy.jpg   | sneha.reddy@iitgn.ac.in   | +91-9876543213
        5 | Vikram Singh  |  24 | vikram_singh.jpg  | vikram.singh@iitgn.ac.in  | +91-9876543214
        6 | Ananya Iyer   |  19 | ananya_iyer.jpg   | ananya.iyer@iitgn.ac.in   | +91-9876543215
        7 | Karthik Nair  |  25 | karthik_nair.jpg  | karthik.nair@iitgn.ac.in  | +91-9876543216
        8 | Meera Joshi   |  22 | meera_joshi.jpg   | meera.joshi@iitgn.ac.in   | +91-9876543217
        9 | Arjun Desai   |  21 | arjun_desai.jpg   | arjun.desai@iitgn.ac.in   | +91-9876543218
       10 | Divya Menon   |  20 | divya_menon.jpg   | divya.menon@iitgn.ac.in   | +91-9876543219
       11 | Rahul Verma   |  23 | rahul_verma.jpg   | rahul.verma@iitgn.ac.in   | +91-9876543220
       12 | Ishita Kapoor |  22 | ishita_kapoor.jpg | ishita.kapoor@iitgn.ac.in | +91-9876543221
       13 | Siddharth Rao |  24 | siddharth_rao.jpg | siddharth.rao@iitgn.ac.in | +91-9876543222
       14 | Neha Agarwal  |  21 | neha_agarwal.jpg  | neha.agarwal@iitgn.ac.in  | +91-9876543223
       15 | Amit Kulkarni |  20 | amit_kulkarni.jpg | amit.kulkarni@iitgn.ac.in | +91-9876543224
(15 rows)
```

### 7f. all devices

```
 deviceid |          location          | devicetype | ipaddress
        1 | Central Library - Floor 1  | Desktop    | 10.0.1.101
        2 | Central Library - Floor 2  | Desktop    | 10.0.1.102
        3 | Central Library - Floor 3  | Desktop    | 10.0.1.103
        4 | Computer Lab A - AB1       | Desktop    | 10.0.2.201
        5 | Computer Lab B - AB1       | Desktop    | 10.0.2.202
        6 | Computer Lab C - AB2       | Desktop    | 10.0.2.203
        7 | Cybercafe - Hostel Block A | Desktop    | 10.0.3.301
        8 | Cybercafe - Hostel Block B | Desktop    | 10.0.3.302
        9 | Student Activity Center    | Kiosk      | 10.0.4.401
       10 | Admin Building Lobby       | Kiosk      | 10.0.4.402
       11 | Placement Cell Office      | Desktop    | 10.0.5.501
       12 | Workshop Lab - AB3         | Desktop    | 10.0.5.502
(12 rows)
```

### 7g. all expiry policies

```
 policyid | maxlifetimeminutes | deleteafterfirstdownload
        1 |                  5 | t
        2 |                 10 | t
        3 |                 15 | t
        4 |                 30 | t
        5 |                 60 | t
        6 |                  5 | f
        7 |                 10 | f
        8 |                 15 | f
        9 |                 30 | f
       10 |                 60 | f
(10 rows)
```

### 7h. all system admins

```
 adminid |       name       |           email
       1 | Dr. Yogesh Meena | yogesh.meena@iitgn.ac.in
       2 | Rajesh Kumar     | rajesh.kumar@iitgn.ac.in
       3 | Sunita Devi      | sunita.devi@iitgn.ac.in
       4 | Manish Tiwari    | manish.tiwari@iitgn.ac.in
       5 | Pooja Saxena     | pooja.saxena@iitgn.ac.in
       6 | Deepak Chauhan   | deepak.chauhan@iitgn.ac.in
       7 | Kavita Bhatt     | kavita.bhatt@iitgn.ac.in
       8 | Nitin Arora      | nitin.arora@iitgn.ac.in
       9 | Swati Mishra     | swati.mishra@iitgn.ac.in
      10 | Anil Pandey      | anil.pandey@iitgn.ac.in
(10 rows)
```
