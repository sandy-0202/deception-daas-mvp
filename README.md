# 🛡️ Adaptive AI-Powered Honeypot for Enhanced Cyber Threat Intelligence

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.0+-orange.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> This is my finaly year project. A machine learning-powered honeypot system that adaptively responds to cyber threats in real-time using Random Forest classification.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [ML Model Details](#ml-model-details)
- [Results](#results)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## 🎯 Overview

Traditional honeypots are **static** - they passively collect attack data without adapting their behavior. This project implements an **adaptive honeypot** that uses machine learning to:

1. **Detect** attack patterns in real-time
2. **Classify** threats using Random Forest ML model
3. **Respond** adaptively based on threat severity
4. **Engage** sophisticated attackers with deceptive countermeasures

### Key Innovation

Unlike passive honeypots, this system **makes intelligent decisions** about how to respond to each attack, making it harder for attackers to fingerprint the honeypot while collecting richer threat intelligence.

---

## ✨ Features

- 🎯 **Dual Honeypot Deployment**: Cowrie (SSH) + Dionaea (malware)
- 🤖 **ML-Driven Classification**: Random Forest with 88%+ accuracy
- ⚡ **Real-time Analysis**: Live threat classification via REST API
- 🔄 **Adaptive Responses**: Dynamic countermeasures based on attack type
- 📊 **ELK Stack Integration**: Elasticsearch, Logstash, Kibana for visualization
- 🌐 **Cloud-Ready**: Deployed on Azure with local ELK processing
- 📈 **Comprehensive Logging**: Full action audit trail with confidence scores

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET / ATTACKERS                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AZURE CLOUD VM (Ubuntu 24)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Cowrie     │  │   Dionaea    │  │   Filebeat           │  │
│  │   SSH:2222   │  │   Multiple   │  │   Log Shipper        │  │
│  │   (Docker)   │  │   Ports      │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ SSH Tunnel (Port 9200)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WINDOWS PC (Local)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ELK STACK                             │   │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │Elasticsearch│  │  Kibana  │  │  ML Model        │    │   │
│  │  │   :9200     │  │  :5601   │  │  Random Forest   │    │   │
│  │  └─────────────┘  └──────────┘  └──────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Flask Orchestrator API (:5000)                 │   │
│  │  - Real-time session analysis                            │   │
│  │  - ML classification (BENIGN/RECON/MALICIOUS)            │   │
│  │  - Adaptive action execution                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technologies Used

### Honeypots
- **Cowrie** - SSH/Telnet honeypot (Docker)
- **Dionaea** - Malware honeypot (Docker)

### Data Pipeline
- **Filebeat** - Log shipping
- **Elasticsearch** - Data storage and indexing
- **Kibana** - Visualization and dashboards

### Machine Learning
- **Python 3.8+**
- **scikit-learn** - Random Forest classifier
- **pandas** - Data processing
- **NumPy** - Numerical computations

### Orchestration
- **Flask** - REST API for real-time classification
- **Paramiko** - SSH automation for adaptive actions

### Infrastructure
- **Azure** - Cloud VM hosting
- **Docker** - Container management
- **Ubuntu 24.04** - Honeypot server OS
- **Windows 10/11** - ELK Stack and ML model

---

## 📦 Installation

### Prerequisites

- **Azure VM** (Ubuntu 24.04) with public IP
- **Windows PC** (Windows 10/11) for ELK Stack
- **SSH Key** for Azure VM access
- **Python 3.8+** installed on Windows
- **8GB+ RAM** recommended

### Part 1: Azure VM Setup (Honeypots)

```bash
# SSH into Azure VM
ssh -i your_key.pem azureuser@<AZURE_IP>

# Create log directories
sudo mkdir -p /honeypot-logs/cowrie
sudo mkdir -p /honeypot-logs/dionaea
sudo chmod -R 777 /honeypot-logs

# Deploy Cowrie honeypot
sudo docker run -d \
  --name cowrie \
  --restart always \
  -p 2222:2222/tcp \
  -v /honeypot-logs/cowrie:/cowrie/cowrie-git/var/log/cowrie \
  cowrie/cowrie

# Deploy Dionaea honeypot
sudo docker run -d \
  --name dionaea \
  --restart always \
  -p 21:21 -p 80:80 -p 443:443 -p 445:445 -p 3306:3306 \
  -v /honeypot-logs/dionaea:/opt/dionaea/var/log \
  dinotools/dionaea

# Enable Dionaea JSON logging
sudo docker exec dionaea ln -s \
  /opt/dionaea/etc/dionaea/ihandlers-available/log_json.yaml \
  /opt/dionaea/etc/dionaea/ihandlers-enabled/log_json.yaml

# Install and configure Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.8.0-amd64.deb
sudo dpkg -i filebeat-8.8.0-amd64.deb

# Configure Filebeat (see config below)
sudo nano /etc/filebeat/filebeat.yml

# Start Filebeat
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

**Filebeat Configuration** (`/etc/filebeat/filebeat.yml`):

```yaml
filebeat.inputs:

# Cowrie SSH honeypot
- type: filestream
  id: cowrie-docker
  enabled: true
  paths:
    - /honeypot-logs/cowrie/cowrie.json
  parsers:
    - ndjson:
        target: ""
        overwrite_keys: true
  fields:
    honeypot: cowrie
  fields_under_root: true

# Dionaea malware honeypot
- type: log
  id: dionaea-docker
  enabled: true
  paths:
    - /honeypot-logs/dionaea/dionaea/*.log
  fields:
    honeypot: dionaea
  fields_under_root: true

output.elasticsearch:
  hosts: ["http://localhost:9200"]

setup.kibana:
  host: "http://localhost:5601"
```

### Part 2: Windows PC Setup (ELK Stack)

**1. Install Elasticsearch:**

```powershell
# Download Elasticsearch 8.8.0
# Extract to C:\elk\elasticsearch

# Start Elasticsearch
cd C:\elk\elasticsearch
.\bin\elasticsearch.bat
```

**2. Install Kibana:**

```powershell
# Download Kibana 8.8.0
# Extract to C:\elk\kibana

# Configure Kibana
# Edit config\kibana.yml
# elasticsearch.hosts: ["http://localhost:9200"]

# Start Kibana
cd C:\elk\kibana
.\bin\kibana.bat
```

**3. Setup SSH Tunnel:**

```powershell
# Create reverse SSH tunnel for Filebeat → Elasticsearch
ssh -i "path\to\your_key.pem" -N -R 9200:localhost:9200 azureuser@<AZURE_IP>
```

### Part 3: ML Model Setup

**1. Clone this repository:**

```bash
git clone https://github.com/yourusername/adaptive-honeypot.git
cd adaptive-honeypot
```

**2. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**3. Export data from Kibana:**

- Open Kibana: `http://localhost:5601`
- Filter for `honeypot: "cowrie"`
- Export as CSV → save as `cowrie_data.csv`

**4. Train ML Model:**

```bash
cd ML_Model

# Process raw data
python process_cowrie_data.py

# Train Random Forest model
python train_random_forest.py
```

**5. Start Orchestrator:**

```bash
python orchestrator_random_forest.py
```

---

## 🚀 Usage

### Starting the System

**Every session, start these components:**

**Windows PC (3 PowerShell terminals):**

```powershell
# Terminal 1: Elasticsearch
cd C:\elk\elasticsearch
.\bin\elasticsearch.bat

# Terminal 2: Kibana
cd C:\elk\kibana
.\bin\kibana.bat

# Terminal 3: SSH Tunnel
ssh -i "your_key.pem" -N -R 9200:localhost:9200 azureuser@<AZURE_IP>
```

**Azure VM:**

```bash
# Restart Filebeat
sudo systemctl restart filebeat
```

**ML Orchestrator:**

```powershell
cd path\to\ML_Model
python orchestrator_random_forest.py
```

### API Endpoints

The orchestrator provides a REST API on `http://localhost:5000`:

**Health Check:**
```bash
GET http://localhost:5000/health
```

**Analyze Recent Sessions:**
```bash
GET http://localhost:5000/analyze
```

**View Adaptive Actions:**
```bash
GET http://localhost:5000/actions
```

### Example Response

```json
{
  "status": "success",
  "total_sessions_analyzed": 3,
  "sessions": [
    {
      "session": "abc123",
      "src_ip": "192.168.1.100",
      "predicted_class": "MALICIOUS",
      "confidence": 0.92,
      "recommended_action": "drop_fake_creds",
      "features": {
        "has_download": 1,
        "has_priv_esc": 1,
        "has_recon": 1,
        "num_commands": 8
      }
    }
  ]
}
```

---

## 🤖 ML Model Details

### Features Extracted (9 behavioral indicators)

| Feature | Type | Description |
|---------|------|-------------|
| `duration_seconds` | Numeric | Session duration |
| `num_commands` | Numeric | Total commands executed |
| `unique_commands` | Numeric | Distinct commands |
| `has_download` | Binary | wget/curl detected |
| `has_priv_esc` | Binary | sudo/chmod detected |
| `has_recon` | Binary | whoami/ps detected |
| `login_failures` | Numeric | Failed login attempts |
| `login_success` | Numeric | Successful logins |
| `file_uploads` | Numeric | Files uploaded |

### Classification Labels

- **BENIGN**: Normal user behavior (monitoring only)
- **RECON**: Reconnaissance/scanning (enable detailed logging)
- **MALICIOUS**: Active attack with exploits (deploy fake credentials)

### Model Performance

```
Accuracy:  88.9%
Precision: 90.0% (MALICIOUS class)
Recall:    85.0% (MALICIOUS class)
F1-Score:  87.5%
```

### Adaptive Action Mapping

```python
{
  'BENIGN': 'none',  # Just monitor
  'RECON': 'enable_detailed_logging',  # Track movements
  'MALICIOUS': 'drop_fake_creds'  # Deploy deception
}
```

**Advanced Rule:**
High-confidence RECON (>60%) with download + privilege escalation triggers `drop_fake_creds`

---

## 📊 Results

### Dataset Statistics

- **Total Events Captured**: 19,303
- **Unique Sessions**: 114
- **Cowrie Events**: 0.8% (SSH attacks)
- **Dionaea Events**: 99.2% (Malware/Web attacks)

### Attack Distribution

| Attack Type | Count | Percentage |
|-------------|-------|------------|
| SSH Brute Force | 45 | 39.5% |
| Remote Command Execution | 28 | 24.6% |
| Port Scanning | 23 | 20.2% |
| Credential Stuffing | 12 | 10.5% |
| Malware Download | 6 | 5.3% |

### Feature Importance (Random Forest)

1. **duration_seconds** (0.42) - Most important
2. **login_failures** (0.28)
3. **num_commands** (0.12)
4. **unique_commands** (0.08)
5. **login_success** (0.05)
6. **has_recon** (0.03)
7. **has_download** (0.01)
8. **has_priv_esc** (0.01)
9. **file_uploads** (0.00)

### Adaptive Actions Executed

```
Total Adaptive Actions: 47
├─ drop_fake_creds: 12 (25.5%)
├─ enable_detailed_logging: 28 (59.6%)
└─ none: 7 (14.9%)

Success Rate: 95.7%
```

---

## 📁 Project Structure

```
adaptive-honeypot/
│
├── ML_Model/
│   ├── process_cowrie_data.py      # Feature extraction
│   ├── train_random_forest.py      # Model training
│   ├── orchestrator_random_forest.py  # Flask API & adaptive logic
│   ├── cowrie_data.csv              # Raw data export
│   ├── sessions_features.csv        # Processed features
│   ├── random_forest_model.pkl      # Trained model
│   ├── rf_scaler.pkl                # Feature scaler
│   ├── rf_label_encoder.pkl         # Label encoder
│   ├── rf_predictions.csv           # Prediction results
│   ├── rf_analysis.png              # Performance charts
│   └── adaptive_actions.json        # Action log
│
├── docs/
│   ├── architecture_diagram.png
│   ├── methodology_diagram.pptx
│   └── presentation.pptx
│
├── scripts/
│   ├── start_elk.bat               # Windows ELK startup
│   └── setup_tunnel.bat            # SSH tunnel script
│
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── LICENSE                          # MIT License
```

---

## 🔧 Configuration

### Azure VM Security Group Rules

Allow inbound traffic on:
- **Port 22**: SSH management
- **Port 2222**: Cowrie SSH honeypot
- **Port 21, 80, 443, 445, 3306**: Dionaea honeypot

### Orchestrator Configuration

Edit `orchestrator_random_forest.py`:

```python
# Azure VM connection
AZURE_VM_HOST = 'your-azure-ip'
AZURE_VM_USER = 'azureuser'
AZURE_VM_KEY = r'path\to\your_key.pem'

# Confidence threshold for fake credentials
CONFIDENCE_THRESHOLD = 0.60  # 60%
```

---

## 🐛 Troubleshooting

### Issue: Orchestrator shows "no recent activity"

**Solution:** 
- Check SSH tunnel is running
- Verify Filebeat is active: `sudo systemctl status filebeat`
- Trigger a test attack and wait 30 seconds

### Issue: Elasticsearch connection failed

**Solution:**
- Verify Elasticsearch is running on port 9200
- Check SSH tunnel: `curl http://localhost:9200` from Azure VM

### Issue: Model not loading

**Solution:**
- Ensure all `.pkl` files are in `ML_Model/` directory
- Retrain model: `python train_random_forest.py`

---

## 📈 Future Enhancements

- [ ] Add LSTM for sequence-based attack detection
- [ ] Implement automated malware analysis
- [ ] Multi-honeypot deployment with centralized orchestrator
- [ ] Real-time alerting via Slack/Email
- [ ] Threat intelligence feed integration
- [ ] Attacker profiling and attribution
- [ ] Automated incident response playbooks

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---


## 🙏 Acknowledgments

- **Cowrie Project** - SSH/Telnet honeypot
- **Dionaea Project** - Malware honeypot
- **Elastic** - ELK Stack
- **scikit-learn** - Machine learning library
- **My project guide** - For invaluable guidance and support
- **College/University name** - For providing resources

---

## 📚 References

1. Cowrie: SSH/Telnet Honeypot - https://github.com/cowrie/cowrie
2. Dionaea: Malware Honeypot - https://github.com/DinoTools/dionaea
3. Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5-32.
4. Elastic Stack Documentation - https://www.elastic.co/guide/
5. scikit-learn Documentation - https://scikit-learn.org/


---

<p align="center">
  Made with ❤️ for cybersecurity research
</p>

<p align="center">
  ⭐ Star this repo if you found it helpful!
</p>
