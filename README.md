# 🧾 Expense Categorizer App

A smart and intuitive web app that helps users upload bills and statements, automatically categorizes items like groceries, clothing, snacks, and more, and visualizes spending using charts. Built with Flask, OCR, and Chart.js.

---

## ✨ Features

- 🔐 User authentication with secure login
- 📸 Upload receipts as **images or PDFs**
- 🧠 AI-assisted item categorization (fuzzy matching + Open Food Facts)
- 📊 Pie chart visualizing expense breakdown
- 📝 Edit categories & delete items before saving
- 💾 Learns from user corrections over time
- 🧠 Identifies duplicate transactions from statements

---

## 📋 Prerequisites

- Python 3.8 or higher  
- Tesseract OCR installed and configured in PATH  
- Flask and supporting Python libraries  
- (Optional) OpenFoodFacts API access  

---

## 🚀 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/expense-categorizer-app.git
cd expense-categorizer-app
