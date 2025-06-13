
# TPL Reservation Automation

This project automates the process of reserving attraction passes through the Toronto Public Library (TPL) ePass system using Selenium and GitHub Actions.

---

## 📦 Files Included

- `tpl_reservation_script.py` – Main automation script supporting `monthly` and `daily` modes.
- `.github/workflows/reservation.yml` – GitHub Actions workflow for scheduled and manual runs.
- `README.md` – Setup and usage instructions.

---

## ⚙️ Features

- Automatically reserves passes for popular attractions like Ripley's Aquarium and Toronto Zoo.
- Supports two modes:
  - `monthly`: Runs on the first Wednesday of the month at 2:00 PM EST to book next month's passes.
  - `daily`: Can be run any day to check for cancellations or newly available passes for the current and next month.
- Secure credential storage using GitHub Secrets or local `.env` file.
- GitHub Actions integration for scheduled and manual runs.
- Multi-threaded and retry logic with exponential backoff.

---

## 🧰 Local Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/tpl-reservation-automation.git
cd tpl-reservation-automation
