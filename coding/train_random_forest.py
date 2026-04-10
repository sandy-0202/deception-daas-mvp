import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('sessions_features.csv')

def classify_session(row):
    if row['has_download'] == 1 and row['has_priv_esc'] == 1:
        return 'MALICIOUS'
    elif row['has_recon'] == 1 or row['login_failures'] >= 2:
        return 'RECON'
    else:
        return 'BENIGN'

df['label'] = df.apply(classify_session, axis=1)

feature_cols = ['duration_seconds', 'num_commands', 'unique_commands',
                'has_download', 'has_priv_esc', 'has_recon',
                'login_failures', 'login_success', 'file_uploads']

X = df[feature_cols].fillna(0)
y = df['label']

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_encoded, test_size=0.3, random_state=42, stratify=y_encoded
)

rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)

y_pred = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

df['predicted_label'] = label_encoder.inverse_transform(rf_model.predict(X_scaled))
df['prediction_confidence'] = rf_model.predict_proba(X_scaled).max(axis=1)

joblib.dump(rf_model, 'random_forest_model.pkl')
joblib.dump(scaler, 'rf_scaler.pkl')
joblib.dump(label_encoder, 'rf_label_encoder.pkl')
df.to_csv('rf_predictions.csv', index=False)

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

axes[0, 0].barh(feature_importance['feature'], feature_importance['importance'])
axes[0, 0].set_xlabel('Importance')
axes[0, 0].set_title('Feature Importance')
axes[0, 0].invert_yaxis()

cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_, ax=axes[0, 1])
axes[0, 1].set_title('Confusion Matrix')

class_counts = df['label'].value_counts()
axes[1, 0].bar(class_counts.index, class_counts.values, color=['green', 'orange', 'red'])
axes[1, 0].set_title('Class Distribution')
axes[1, 0].tick_params(axis='x', rotation=45)

axes[1, 1].hist(df['prediction_confidence'], bins=10, edgecolor='black')
axes[1, 1].set_title('Prediction Confidence')
axes[1, 1].axvline(x=0.8, color='r', linestyle='--', label='80% threshold')
axes[1, 1].legend()

plt.tight_layout()
plt.savefig('rf_analysis.png', dpi=150, bbox_inches='tight')

print(f"✅ Random Forest trained: {accuracy*100:.1f}% accuracy")
print(f"✅ Class distribution: {dict(df['label'].value_counts())}")
print(f"✅ Saved: random_forest_model.pkl, rf_scaler.pkl, rf_label_encoder.pkl, rf_predictions.csv, rf_analysis.png")