<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![MIT License][license-shield]][license-url]
[![][version-shield]][version-url]

<!-- PROJECT NAME -->
<br/>
<div align="center">
    <h3 align="center">MWO Competitive Stats Visualization</h3>
    <p align="center">
        A web application that helps you visualize data from competitive matches.
    </p>
</div>

<!-- ABOUT THE PROJECT -->
## About The Project

This application takes spreadsheet data with results of lobby matches as an input, parse it and provide you various stats plots.

<!-- GETTING STARTED -->
## Getting Started

### Deployment

For a Linux-based system:
- Make a folder for the project
- Initialize Git and clone repository:
  ```shell
  git init
  git clone https://github.com/iT-Drake/MWOCompStatsVisualization.git
  ```
- Create virtual environment with Python, activate it and install dependencies:
  ```shell
  python3 -m venv .venv
  . .venv/bin/activate
  .venv/bin/pip install -r requirements.txt
  ```
- Make a file for environment variables, name it `.env` (note that dot in the name), add one line and fill it with proper url:
  ```
  URL=https://docs.google.com/spreadsheets/d/<ID_OF_YOUR_SHARED_SPREADSHEET_>/edit?usp=sharing
  ```
- Run `Streamlit`:
  ```shell
  streamlit run app.py
  ```
- Run your browser, go to `http://serveraddress:8501` and test the application.

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/iT-Drake/MWOCompStatsVisualization.svg?style=for-the-badge
[contributors-url]: https://github.com/iT-Drake/MWOCompStatsVisualization/graphs/contributors

[license-shield]: https://img.shields.io/github/license/iT-Drake/MWOCompStatsVisualization.svg?style=for-the-badge
[license-url]: https://github.com/iT-Drake/MWOCompStatsVisualization/blob/main/LICENSE

[version-shield]: https://img.shields.io/badge/Version-0.1-blue?style=for-the-badge
[version-url]: https://github.com/iT-Drake/MWOCompStatsVisualization
