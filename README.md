#  Expense Categorizer App

A smart and intuitive web app that helps users upload bills and statements, automatically categorizes items like groceries, clothing, snacks, and more, and visualizes spending using charts. Built with Flask, OCR, and Chart.js.

---

![Image](https://github.com/user-attachments/assets/abc39055-7ab0-4d65-a066-c04e71c363b7)


##  Table of Contents

- [Features ](#features)
- [Prerequisites ](#prerequisites)
- [Setup Instructions ](#setup-instructions)
  - [Clone the Repository](#1.clone-the-repository)
  - [Create and Activate Virtual Environment](#2.create-and-activate-a-virtual-environment)
  - [Install Dependencies](#3.install-dependencies)
  - [Install Tesseract OCR](#4.install-tesseract-ocr)
- [Running the Application ](#running-the-application)
- [Usage Guide ](#usage-guide)
  - [Uploading Expenses](#uploading-expenses)
  - [Reviewing and Editing](#reviewing-and-editing)
  - [Visualizations](#visualizations)
- [Security Notes ](#security-notes)
- [Troubleshooting ](#troubleshooting)
- [Contributing ](#contributing)
- [License ](#license)
- [Acknowledgments ](#acknowledgments)


## Features

-  User authentication with secure login
-  Upload receipts as **images or PDFs**
- AI-assisted item categorization (fuzzy matching + Open Food Facts)
-  Pie chart visualizing expense breakdown
-  Edit categories & delete items before saving
-  Learns from user corrections over time
-  Identifies duplicate transactions from statements

---

## Prerequisites

- Python 3.8 or higher  
- Tesseract OCR installed and configured in PATH  
- Flask and supporting Python libraries  
- (Optional) OpenFoodFacts API access  

---

## Setup Instructions

### 1.Clone the repository

```bash
git clone https://github.com/yourusername/expense-categorizer-app.git
cd expense-categorizer-app
```

### 2.Create and activate a virtual environment
```bash
-python -m venv venv
```

### On Windows:
```bash
-venv\Scripts\activate
```

### On macOS/Linux:
```bash
-source venv/bin/activate
```

### 3.Install dependencies
```bash
-pip install -r requirements.txt
```

### 4.Install Tesseract OCR
Tesseract Installation Guide
Make sure it's in your system PATH or update the path in ocr_processor.py.


## Running the Application
```bash
python app.py
```
### Visit the application in your browser:
```bash
http://localhost:5000
```

## Usage Guide

### Uploading Expenses
- Go to the Upload page
- Select a bill or statement (PDF or image)
- The app will scan the file and extract items

### Reviewing and Editing
- Review extracted items and categories
- Change incorrect categories using dropdowns
- Mark unnecessary items using delete checkbox
- Click Apply Changes to save your data

### Visualizations
- View a pie chart of your spending breakdown
- See total amounts spent per category

## Security Notes
- User sessions are managed with Flask-Login
- Only valid file types are accepted
- Categorization is processed locally
- User edits are remembered for future bills

## Troubleshooting
### Problem	                            ### Solution
"Tesseract is not installed"   ->	 Install it and add to system PATH
"No text could be extracted"	  ->  Ensure file is readable (good quality scan)
"App crashes on upload"	       ->  Check for file format and size
"Category doesn't match"	      ->  Fix it once — app will learn next time

## Contributing
Want to improve this project?
Feel free to fork it and submit a pull request!
For major changes, please open an issue first to discuss your idea.

## License
MIT License

## Acknowledgments
- Open Food Facts for food category data
-  Tesseract OCR
-  Flask, Bootstrap, Chart.js for framework and UI components

