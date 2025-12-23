# Freemir TikTok Brand Analysis Dashboard

This repository contains a **Streamlit** application designed for the Freemir Intelligence Team. It automates the process of scraping TikTok comments, analyzing sentiment/keywords, and generating professional reports.

## Features

1.  **Automated Scraping**: Uses Apify to fetch comments and replies from a specific TikTok video URL.
2.  **Advanced Analysis**:
    * **Sentiment Analysis**: Categorizes comments into Positive, Negative, Neutral, Question, or Statement using a custom Indonesian dictionary.
    * **Slang Normalization**: Automatically converts Indonesian slang (e.g., "yg", "gk", "bgt") into formal Indonesian.
    * **Keyword Extraction**: Identifies top discussed topics excluding common stopwords.
3.  **Dual Reporting**:
    * **Excel Report**: Contains raw data, clean data, and translated summaries (ID/EN/CN) for internal data teams.
    * **HTML Dashboard**: A standalone, interactive HTML file with charts and highlighted comments for management presentations.

## Installation

Ensure you have Python installed. Clone this repository and install the dependencies:

```bash
pip install -r requirements.txt
