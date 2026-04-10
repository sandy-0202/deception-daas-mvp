import pandas as pd
import numpy as np
from datetime import datetime

df = pd.read_csv('cowrie_data.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['command'] = df['message'].str.extract(r'CMD:\s*(.+)', expand=False)

sessions = df.groupby('session').agg({
    'timestamp': ['min', 'max', 'count'],
    'command': lambda x: ' '.join(x.dropna().astype(str)),
    'src_ip': 'first',
    'eventid': lambda x: list(x),
    'duration': 'max',
    'password': 'first',
    'username': 'first'
}).reset_index()

sessions.columns = ['session', 'start_time', 'end_time', 'event_count', 
                    'commands', 'src_ip', 'events', 'duration', 'password', 'username']

sessions['duration_seconds'] = sessions.apply(
    lambda row: row['duration'] if pd.notna(row['duration']) 
    else (row['end_time'] - row['start_time']).total_seconds(),
    axis=1
)

sessions['num_commands'] = sessions['commands'].str.split().str.len()
sessions['unique_commands'] = sessions['commands'].apply(
    lambda x: len(set(str(x).split())) if pd.notna(x) else 0
)

sessions['has_download'] = sessions['commands'].str.contains(
    'wget|curl|scp|ftp', case=False, na=False
).astype(int)

sessions['has_priv_esc'] = sessions['commands'].str.contains(
    'sudo|su|chmod|chown', case=False, na=False
).astype(int)

sessions['has_recon'] = sessions['commands'].str.contains(
    'whoami|uname|cat /etc|ps|netstat|ifconfig', case=False, na=False
).astype(int)

sessions['login_failures'] = sessions['events'].apply(
    lambda x: sum(1 for e in x if 'login.failed' in str(e))
)

sessions['login_success'] = sessions['events'].apply(
    lambda x: sum(1 for e in x if 'login.success' in str(e))
)

sessions['file_uploads'] = sessions['events'].apply(
    lambda x: sum(1 for e in x if 'file_upload' in str(e))
)

feature_cols = [
    'session', 'src_ip', 'username', 'password',
    'duration_seconds', 'event_count', 'num_commands', 'unique_commands',
    'has_download', 'has_priv_esc', 'has_recon',
    'login_failures', 'login_success', 'file_uploads'
]

sessions_clean = sessions[feature_cols].fillna({
    'duration_seconds': 0,
    'num_commands': 0,
    'unique_commands': 0
})

sessions_clean.to_csv('sessions_features.csv', index=False)

print(f"✅ Processed {len(sessions_clean)} sessions → sessions_features.csv")