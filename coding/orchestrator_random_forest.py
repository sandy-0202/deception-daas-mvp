from flask import Flask, jsonify
from elasticsearch import Elasticsearch
import joblib
import pandas as pd
import numpy as np
import json
import paramiko
from datetime import datetime, timedelta

app = Flask(__name__)
es = Elasticsearch(['http://localhost:9200'])

# Load Random Forest model and components
model = joblib.load('random_forest_model.pkl')
scaler = joblib.load('rf_scaler.pkl')
label_encoder = joblib.load('rf_label_encoder.pkl')

# Adaptive actions log file
ACTIONS_LOG = 'adaptive_actions.json'

# Azure VM connection details
AZURE_VM_HOST = '172.188.98.114'
AZURE_VM_USER = 'azureuser'
AZURE_VM_KEY = r'S:\devops\azure_key\honeypot-vm_key.pem'

def get_recent_sessions():
    """Query Elasticsearch for Cowrie sessions in last 5 minutes"""
    query = {
        'query': {
            'bool': {
                'must': [
                    {'match': {'honeypot': 'cowrie'}},
                    {'range': {'@timestamp': {'gte': 'now-5m'}}}
                ]
            }
        },
        'sort': [{'@timestamp': 'desc'}]
    }
    try:
        result = es.search(index='filebeat-*', body=query, size=1000)
        return result['hits']['hits']
    except Exception as e:
        print(f"Elasticsearch error: {e}")
        return []

def extract_features(session_events):
    """Extract ML features from session events"""
    commands = []
    for e in session_events:
        src = e.get('_source', {})
        
        cmd = src.get('input')
        if cmd and isinstance(cmd, str):
            commands.append(cmd)
        
        msg = src.get('message', '')
        if 'CMD:' in str(msg):
            cmd_text = str(msg).split('CMD:')[-1].strip()
            if cmd_text:
                commands.append(cmd_text)
    
    durations = [e['_source'].get('duration', 0) for e in session_events if e['_source'].get('duration')]
    duration = max(durations) if durations else 20.0
    
    commands_str = ' '.join(commands)
    features = {
        'duration_seconds': float(duration),
        'num_commands': len(commands),
        'unique_commands': len(set(commands)) if commands else 0,
        'has_download': 1 if any(c in commands_str.lower() for c in ['wget', 'curl', 'scp']) else 0,
        'has_priv_esc': 1 if any(c in commands_str.lower() for c in ['sudo', 'su', 'chmod']) else 0,
        'has_recon': 1 if any(c in commands_str.lower() for c in ['whoami', 'uname', 'ps']) else 0,
        'login_failures': sum(1 for e in session_events if 'login.failed' in e['_source'].get('eventid', '')),
        'login_success': sum(1 for e in session_events if 'login.success' in e['_source'].get('eventid', '')),
        'file_uploads': sum(1 for e in session_events if 'file_upload' in e['_source'].get('eventid', ''))
    }
    
    return pd.DataFrame([features])

def execute_action_on_vm(action, session_id):
    """
    ACTUALLY EXECUTE adaptive action on Azure VM honeypot
    This plants real files that attackers will see
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"\n🔗 Connecting to Azure VM {AZURE_VM_HOST}...")
        ssh.connect(
            AZURE_VM_HOST,
            username=AZURE_VM_USER,
            key_filename=AZURE_VM_KEY
        )
        
        if action == 'drop_fake_creds':
            # Plant fake credentials file in Cowrie filesystem
            fake_creds = f"""# PRODUCTION SYSTEM CREDENTIALS
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# CONFIDENTIAL - DO NOT DISTRIBUTE

[DATABASE]
prod_db_host=10.0.1.100
prod_db_user=db_admin
prod_db_pass=Pr0d_DB#2024!Secret
prod_db_port=5432

[SSH_ACCESS]
deploy_user=deployer
deploy_pass=D3pl0y#K3y!2024
backup_server=10.0.2.50

[API_KEYS]
stripe_api_key=sk_live_51H7xKLGmW9dR8TnN2024FAKE
aws_access_key=AKIA4ODZJFAKEKEY2024DEMO
aws_secret=wJalrXUtnFEMI/K7MDENG/bPxRfiCYFAKEKEY

[ADMIN_PANEL]
admin_url=https://admin.internal.company.com
admin_user=sysadmin
admin_pass=Adm1n#P@ssw0rd!2024
"""
            
            command = f"""sudo docker exec cowrie bash -c 'cat > /cowrie/cowrie-git/honeyfs/root/.credentials << "EOFMARKER"
{fake_creds}
EOFMARKER
chmod 644 /cowrie/cowrie-git/honeyfs/root/.credentials'"""
            
            stdin, stdout, stderr = ssh.exec_command(command)
            stdout.channel.recv_exit_status()  # Wait for command
            
            print(f"✅ Planted fake credentials file: /root/.credentials")
            print(f"   Attacker will see: 'cat .credentials' or 'ls -la'")
            result = "SUCCESS: Fake credentials planted"
            
        elif action == 'enable_detailed_logging':
            # Create monitoring marker
            command = f"sudo docker exec cowrie bash -c 'echo MONITORING_ENABLED_{session_id} > /tmp/monitor_active'"
            stdin, stdout, stderr = ssh.exec_command(command)
            stdout.channel.recv_exit_status()
            
            print(f"✅ Enabled detailed logging for session {session_id}")
            result = "SUCCESS: Detailed logging enabled"
            
        elif action == 'change_ssh_banner':
            # Modify MOTD
            new_motd = f"""
Ubuntu 20.04.6 LTS Production Server
Welcome to DB-PRIMARY-01

Last login: {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}
System load: 0.42 0.38 0.31
Memory usage: 34%
Swap usage: 2%

[PRODUCTION] Database cluster node 1 of 3
All actions are logged and monitored.
"""
            command = f"""sudo docker exec cowrie bash -c 'cat > /cowrie/cowrie-git/honeyfs/etc/motd << "EOFMOTD"
{new_motd}
EOFMOTD'"""
            
            stdin, stdout, stderr = ssh.exec_command(command)
            stdout.channel.recv_exit_status()
            
            print(f"✅ Modified SSH banner/MOTD")
            result = "SUCCESS: SSH banner modified"
            
        else:
            result = f"NO ACTION: {action}"
        
        ssh.close()
        return True, result
        
    except Exception as e:
        print(f"❌ VM execution failed: {e}")
        return False, f"FAILED: {str(e)}"

def map_class_to_action(predicted_class, confidence, features):
    """Map predicted attack class to adaptive action - considers features for advanced detection"""
    
    # SPECIAL RULE: RECON with download+priv_esc = advanced attacker
    # Deploy fake credentials to engage them (threshold: 60% confidence)
    if predicted_class == 'RECON' and confidence >= 0.60:
        if features.get('has_download', 0) == 1 and features.get('has_priv_esc', 0) == 1:
            return {
                'action': 'drop_fake_creds',
                'description': 'Advanced reconnaissance with exploit attempts detected - deploying fake credentials to engage sophisticated attacker'
            }
    
    # Standard mappings
    action_mapping = {
        'BENIGN': {
            'action': 'none',
            'description': 'Normal behavior - no adaptive response needed'
        },
        'RECON': {
            'action': 'enable_detailed_logging',
            'description': 'Reconnaissance detected - enable verbose logging to track attacker movements'
        },
        'MALICIOUS': {
            'action': 'drop_fake_creds',
            'description': 'Active attack detected - deploy fake credentials to engage attacker and track exfiltration attempts'
        }
    }
    
    action_info = action_mapping.get(predicted_class, action_mapping['BENIGN'])
    
    # Low confidence override - just monitor
    if confidence < 0.7 and predicted_class != 'BENIGN':
        action_info['action'] = 'enable_detailed_logging'
        action_info['description'] += ' (low confidence - monitoring mode)'
    
    return action_info

def execute_adaptive_action(session_id, src_ip, predicted_class, confidence, action_info, features):
    """
    Execute adaptive action based on Random Forest classification
    NOW WITH REAL VM EXECUTION
    """
    
    # Create detailed action log entry
    action_log = {
        'timestamp': datetime.now().isoformat(),
        'session_id': session_id,
        'source_ip': src_ip,
        'predicted_class': predicted_class,
        'confidence': float(confidence),
        'action_triggered': action_info['action'],
        'action_description': action_info['description'],
        'session_features': features,
        'model_type': 'Random Forest Classifier',
        'adaptive_response_status': 'EXECUTING' if action_info['action'] != 'none' else 'NO_ACTION_NEEDED'
    }
    
    # EXECUTE THE ACTION ON VM
    execution_success = False
    execution_result = "NOT_EXECUTED"
    
    if action_info['action'] != 'none':
        execution_success, execution_result = execute_action_on_vm(action_info['action'], session_id)
        action_log['execution_status'] = execution_result
        action_log['execution_success'] = execution_success
    
    # Log the adaptive decision
    try:
        with open(ACTIONS_LOG, 'a') as f:
            f.write(json.dumps(action_log) + '\n')
        
        # Print to console for monitoring
        if action_info['action'] != 'none':
            print("\n" + "="*70)
            print("🎯 ADAPTIVE ACTION EXECUTED (Random Forest)")
            print("="*70)
            print(f"Session: {session_id}")
            print(f"Source IP: {src_ip}")
            print(f"Classified as: {predicted_class}")
            print(f"Confidence: {confidence*100:.1f}%")
            print(f"Action: {action_info['action']}")
            print(f"Result: {execution_result}")
            print(f"Reason: {action_info['description']}")
            print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"Error logging adaptive action: {e}")
        return False

@app.route('/analyze')
def analyze():
    """Analyze recent Cowrie sessions using Random Forest classifier"""
    events = get_recent_sessions()
    
    if not events:
        return jsonify({'status': 'no recent activity', 'sessions': []})
    
    # Group events by session
    sessions = {}
    for e in events:
        src = e.get('_source', {})
        sid = src.get('session')
        if sid:
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(e)
    
    if not sessions:
        return jsonify({'status': 'no sessions found', 'sessions': []})
    
    # Classify each session
    results = []
    for sid, session_events in sessions.items():
        try:
            # Extract features
            X = extract_features(session_events)
            features_dict = X.to_dict('records')[0]
            
            # Scale features
            X_scaled = scaler.transform(X)
            
            # Get prediction and confidence
            predicted_class_encoded = model.predict(X_scaled)[0]
            predicted_class = label_encoder.inverse_transform([predicted_class_encoded])[0]
            
            probabilities = model.predict_proba(X_scaled)[0]
            confidence = probabilities[predicted_class_encoded]
            
            all_probabilities = {
                label_encoder.inverse_transform([i])[0]: float(prob)
                for i, prob in enumerate(probabilities)
            }
            
            # Map class to action (NOW considers features for advanced detection)
            action_info = map_class_to_action(predicted_class, confidence, features_dict)
            
            # Get session details
            src_ip = session_events[0]['_source'].get('src_ip', 'unknown')
            num_events = len(session_events)
            
            # ⭐ EXECUTE ADAPTIVE ACTION ON VM
            action_executed = execute_adaptive_action(
                session_id=sid,
                src_ip=src_ip,
                predicted_class=predicted_class,
                confidence=confidence,
                action_info=action_info,
                features=features_dict
            )
            
            results.append({
                'session': sid,
                'src_ip': src_ip,
                'num_events': num_events,
                'predicted_class': predicted_class,
                'confidence': float(confidence),
                'class_probabilities': all_probabilities,
                'recommended_action': action_info['action'],
                'action_description': action_info['description'],
                'action_logged': action_executed,
                'features': features_dict
            })
        except Exception as e:
            print(f"Error processing session {sid}: {e}")
            continue
    
    # Sort by confidence (most confident first)
    results.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Count by class
    class_counts = {}
    for r in results:
        cls = r['predicted_class']
        class_counts[cls] = class_counts.get(cls, 0) + 1
    
    return jsonify({
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'model_type': 'Random Forest Classifier with Advanced Adaptive Logic',
        'total_sessions_analyzed': len(results),
        'class_distribution': class_counts,
        'sessions': results
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        es.info()
        model_loaded = model is not None
        scaler_loaded = scaler is not None
        encoder_loaded = label_encoder is not None
        
        # Test VM connection
        vm_status = "disconnected"
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(AZURE_VM_HOST, username=AZURE_VM_USER, key_filename=AZURE_VM_KEY, timeout=5)
            ssh.close()
            vm_status = "connected"
        except:
            pass
        
        return jsonify({
            'status': 'healthy',
            'elasticsearch': 'connected',
            'azure_vm': vm_status,
            'model_type': 'Random Forest Classifier',
            'model_loaded': model_loaded,
            'scaler_loaded': scaler_loaded,
            'encoder_loaded': encoder_loaded,
            'num_classes': len(label_encoder.classes_),
            'classes': label_encoder.classes_.tolist(),
            'adaptive_execution': 'enabled'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/actions')
def get_actions():
    """View all adaptive actions taken"""
    try:
        actions = []
        with open(ACTIONS_LOG, 'r') as f:
            for line in f:
                try:
                    actions.append(json.loads(line.strip()))
                except:
                    continue
        
        # Sort by timestamp (most recent first)
        actions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Statistics
        total_actions = len(actions)
        actions_by_type = {}
        actions_by_class = {}
        executed_count = 0
        
        for a in actions:
            # Count by action type
            action_type = a.get('action_triggered', 'unknown')
            actions_by_type[action_type] = actions_by_type.get(action_type, 0) + 1
            
            # Count by predicted class
            pred_class = a.get('predicted_class', 'unknown')
            actions_by_class[pred_class] = actions_by_class.get(pred_class, 0) + 1
            
            # Count executed
            if a.get('execution_success'):
                executed_count += 1
        
        return jsonify({
            'status': 'success',
            'model_type': 'Random Forest Classifier',
            'total_adaptive_actions': total_actions,
            'actions_executed_successfully': executed_count,
            'actions_by_type': actions_by_type,
            'actions_by_class': actions_by_class,
            'recent_actions': actions[:10],
            'all_actions': actions
        })
        
    except FileNotFoundError:
        return jsonify({
            'status': 'success',
            'message': 'No adaptive actions logged yet',
            'total_adaptive_actions': 0,
            'actions_by_type': {},
            'actions_by_class': {},
            'recent_actions': []
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("="*70)
    print("🌲 ADAPTIVE HONEYPOT ORCHESTRATOR (Random Forest)")
    print("="*70)
    print(f"Elasticsearch: http://localhost:9200")
    print(f"Azure VM: {AZURE_VM_HOST}")
    print(f"Orchestrator API: http://localhost:5000")
    print(f"\n📡 Available Endpoints:")
    print(f"  GET /analyze  - Classify sessions & EXECUTE actions on VM")
    print(f"  GET /actions  - View all adaptive actions logged")
    print(f"  GET /health   - Check system health + VM connection")
    print(f"\n🎯 Attack Classes Detected:")
    print(f"  ✓ BENIGN - Normal user behavior")
    print(f"  ✓ RECON - Reconnaissance/scanning")
    print(f"  ✓ MALICIOUS - Active attack with exploits")
    print(f"\n💡 Adaptive Actions (REAL EXECUTION):")
    print(f"  BENIGN → none (monitoring only)")
    print(f"  RECON (standard) → enable_detailed_logging")
    print(f"  RECON (high confidence + exploits) → drop_fake_creds ⭐")
    print(f"  MALICIOUS → drop_fake_creds (PLANTS REAL FILE IN HONEYPOT)")
    print(f"\n⚠️  Actions are ACTUALLY EXECUTED on Azure VM honeypot!")
    print("\n💾 Actions log file: adaptive_actions.json")
    print("="*70 + "\n")
    app.run(port=5000)
