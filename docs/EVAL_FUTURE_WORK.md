# Eval System — Future Work

## Current State (Binary Evaluation)
- Autorater returns `{"assessment": "pass"|"fail", ...}`
- Optional `confidence: 0-1` field (captured but not yet used)
- Ground truth via tag mapping at run time: transcript tags mapped to expected pass/fail
- Metrics: pass rate (always), accuracy/precision/recall/F1 (when tag mapping configured)

## Planned Extensions

### Multi-Class Labels
- Support autorater responses with categorical outputs beyond pass/fail
- Example: `{"category": "refund"|"complaint"|"general", "assessment": "pass"|"fail"}`
- Per-category precision/recall/F1 (already partially implemented in classification eval)
- Confusion matrix visualization

### Numeric Thresholds
- Support numeric scores instead of binary pass/fail
- Example: `{"score": 0.85, "assessment": "pass"}`
- Configurable threshold: score >= threshold → pass
- Distribution histograms and percentile metrics

### Confidence Scoring
- Use the `confidence` field returned by autoraters
- Confidence-weighted accuracy
- Calibration curves (predicted confidence vs actual accuracy)
- Low-confidence flagging for human review

### Advanced Ground Truth
- Multiple label dimensions per transcript (e.g., tone + accuracy + completeness)
- Weighted scoring across dimensions
- Inter-rater agreement when multiple autoraters evaluate the same transcripts
