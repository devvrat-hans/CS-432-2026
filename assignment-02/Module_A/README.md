# Lightweight DBMS with B+ Tree Index  
## CS 432 Databases – Assignment 2 (Module A)

---

## 📌 Project Overview
This project implements a **lightweight Database Management System (DBMS)** using a **B+ Tree indexing structure**. It supports efficient data operations such as insertion, search, deletion, update, and range queries.

The system is also compared against a **Brute Force approach** to analyze performance differences.

---

## 📂 Project Structure

---
```

db_management_system/
│
├── database/
│ ├── init.py
│ ├── bplustree.py # B+ Tree implementation
│ ├── bruteforce.py # Brute-force baseline
│ ├── db_manager.py # DB Manager (table operations)
│ ├── performance.py # Performance benchmarking
│ ├── table.py # Table abstraction using B+ Tree
│
├── Module_A_outputs/ # Graphviz visualization outputs
│
├── report.ipynb # Main report (implementation + analysis) -- Main Report File
├── test_bplustree.py # Test B+ Tree operations
├── test_dbmanager.py # Test DB Manager functionality
├── test_performance.py # Run performance benchmarks

```
---

## ⚙️ Features

### 🔹 B+ Tree Implementation
- Insert with automatic node splitting
- Delete with merging and rebalancing
- Search (exact match)
- Range queries using leaf linkage
- Update existing records
- In-order traversal

### 🔹 DBMS Layer
- Create and drop tables
- Insert and retrieve records
- Range-based queries
- Error handling

### 🔹 Performance Analysis
- Insert, search, delete timing comparison
- Range query benchmarking
- Random workload testing
- Memory usage comparison

### 🔹 Visualization
- Tree structure using Graphviz
- Parent-child relationships
- Leaf node linkage (dashed connections)

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <your-repo-link>
cd db_management_system
```
2. Install Python Dependencies
```bash
pip install graphviz matplotlib pandas
```
3. Install Graphviz (System Requirement)
Windows:

Download and install from: https://graphviz.org/download/

Add Graphviz to system PATH.

Ubuntu:
```bash
sudo apt install graphviz
```
Mac:
```bash
brew install graphviz
```
---
▶️ How to Run
- ✅ Run Jupyter Notebook (Recommended)
```bash
jupyter notebook
```
- Open report.ipynb
- Run all cells

---

✅ Run Individual Test Files
- Test B+ Tree
```bash
python test_bplustree.py
```
- Test DB Manager
```bash
python test_dbmanager.py
```
- Run Performance Analysis
```bash
python test_performance.py
```
---

### 📊 Outputs
- Graphs and tables shown in report.ipynb
- Tree visualizations saved in:
```bash
Module_A_outputs/
```

---

📈 Key Results
- B+ Tree provides O(log n) performance for search, insert, and delete
- Brute Force shows O(n) complexity
- Significant improvements observed in:
- Search operations
- Deletion operations
- Random workloads
- Trade-off: Slightly higher memory usage in B+ Tree
