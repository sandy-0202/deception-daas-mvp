import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt

df = pd.read_csv('sessions_features.csv')

feature_cols = [
    'duration_seconds', 'num_commands', 'unique_commands',
    'has_download', 'has_priv_esc', 'has_recon',
    'login_failures', 'login_success', 'file_uploads'
]

X = df[feature_cols].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = IsolationForest(contamination=0.2, random_state=42, n_estimators=100)
model.fit(X_scaled)

df['anomaly_score'] = model.decision_function(X_scaled)
df['is_anomaly'] = model.predict(X_scaled)

joblib.dump(model, 'cowrie_anomaly_model.pkl')
joblib.dump(scaler, 'feature_scaler.pkl')
df.to_csv('session_predictions.csv', index=False)

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

axes[0, 0].barh(range(len(df)), df.sort_values('anomaly_score')['anomaly_score'], 
                color=['red' if x == -1 else 'green' for x in df.sort_values('anomaly_score')['is_anomaly']])
axes[0, 0].set_xlabel('Anomaly Score')
axes[0, 0].set_title('Session Anomaly Scores')

axes[0, 1].scatter(df['duration_seconds'], df['num_commands'], 
                   c=['red' if x == -1 else 'green' for x in df['is_anomaly']], s=100, alpha=0.6)
axes[0, 1].set_xlabel('Duration (s)')
axes[0, 1].set_ylabel('Commands')
axes[0, 1].set_title('Session Behavior')

axes[1, 0].barh(feature_cols, X.var())
axes[1, 0].set_xlabel('Variance')
axes[1, 0].set_title('Feature Variance')

axes[1, 1].bar(['Download', 'PrivEsc', 'Recon'], df[['has_download', 'has_priv_esc', 'has_recon']].sum())
axes[1, 1].set_title('Attack Patterns')

plt.tight_layout()
plt.savefig('anomaly_analysis.png', dpi=150, bbox_inches='tight')

print(f"✅ Trained model: {(df['is_anomaly'] == -1).sum()}/{len(df)} anomalies detected")
print("✅ Saved: cowrie_anomaly_model.pkl, feature_scaler.pkl, session_predictions.csv, anomaly_analysis.png")