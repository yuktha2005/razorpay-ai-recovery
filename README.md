# AI Payment Recovery Agent

An AI-driven payment recovery decision engine that detects payment degradation, identifies the affected payment route, quantifies business impact, evaluates alternative banks, and simulates a recovery strategy.

> **Prototype / simulation environment:** This project uses synthetic transaction data. It does not process real payments or change live payment routing.

---

## 1. Problem Statement

Payment failures do not always affect an entire payment system uniformly. A degradation can be concentrated in a particular combination of:

- Payment method
- Bank
- Device type
- Time window

A conventional monitoring dashboard can show that failures increased, but an operations team still needs to determine:

1. Where is the degradation occurring?
2. How severe is it compared with normal performance?
3. Which payment route is most affected?
4. What is the financial impact?
5. Which alternative bank has historically performed better?
6. What could recovery look like if eligible traffic were shifted?

This project addresses that workflow end to end.

---

## 2. Solution

The **AI Payment Recovery Agent** combines transaction analytics and rule/statistical scoring into an operational decision workflow:

```text
Transaction Data
       |
       v
Payment Monitoring
       |
       v
Temporal / Route Incident Detection
       |
       v
Root Cause Analysis
       |
       v
Business Impact Analysis
       |
       v
Alternative Route Evaluation
       |
       v
Recovery Recommendation
       |
       v
Counterfactual Recovery Simulation
       |
       v
Streamlit Control Center
```

The agent's investigation flow is:

**Detect -> Diagnose -> Quantify -> Compare -> Recommend -> Simulate**

---

## 3. Demonstration Scenario

The synthetic dataset contains a deliberately injected payment degradation scenario.

Example detected route:

```text
UPI -> Bank_X -> Android
```

Example incident characteristics:

- Incident window: **2026-07-23 19:00 to 20:00**
- Affected route transactions: **508**
- Incident success rate: **69.49%**
- Historical baseline: **94.42%**
- Degradation: **24.93 percentage points**
- Actual failures: **155**
- Excess failures: approximately **126.6**
- Estimated revenue at risk: approximately **₹355,840**
- Recommended alternative bank: **Bank_A**
- Historical alternative success rate: approximately **96%**
- Simulated additional successful payments: approximately **135**
- Simulated recoverable value: approximately **₹291K**

These values are produced from the included synthetic dataset and may change if the dataset is regenerated.

---

## 4. Core Capabilities

### Payment Monitoring

`src/monitor.py`

Calculates time-window payment performance including:

- Transaction volume
- Successful transactions
- Failed transactions
- Total transaction value
- Failed transaction value
- Success rate

### Segment Monitoring

`src/segment_monitor.py`

Breaks payment performance down by:

- Time window
- Payment method
- Bank
- Device type

It surfaces low-success segments for investigation.

### Temporal Incident Detection

`src/temporal_detector.py`

Evaluates hourly payment routes and compares observed success rates with route-level historical performance.

The detector considers:

- Route degradation
- Transaction volume
- Failed transaction value
- Detection score

### Automatic Incident Detection

`src/agent.py`

The integrated agent performs route-level hourly detection using a historical baseline that excludes the current hour.

A candidate must satisfy minimum volume and degradation conditions before being considered an incident.

### Root Cause Analysis

`src/root_cause.py` and the `analyze_root_cause()` function in `src/agent.py`

Analyzes dimensions such as:

- Payment method
- Bank
- Device type
- Location
- Error code
- Payment route

The integrated agent also calculates an explainability-oriented confidence score and summarizes incident failure reasons.

### Revenue Impact Analysis

`src/revenue_impact.py` and `calculate_revenue_impact()` in `src/agent.py`

Estimates:

- Actual failures
- Expected failures under the historical baseline
- Excess failures
- Failed transaction value
- Revenue at risk

### Recovery Recommendation

`src/recovery_engine.py` and `recommend_recovery()` in `src/agent.py`

Evaluates alternative banks for the affected payment method and recommends an alternative based on historical success performance and minimum historical volume.

### Recovery Simulation

`src/recovery_simulator.py`

Performs a counterfactual simulation of the recommended route.

It estimates:

- Before success rate
- Simulated after success rate
- Additional successful payments
- Remaining failures
- Estimated recovered transaction value

### Streamlit Control Center

`app.py`

Provides the product interface for:

- Payment health
- Active incident
- Incident timeline
- AI root cause analysis
- Failure reasons
- Business impact
- Alternative route analysis
- Agent decision trail
- Recovery simulation

---

## 5. Project Structure

```text
razorpay-ai-recovery/
|
├── app.py
|
├── data/
│   └── transactions.csv
|
├── src/
│   ├── agent.py
│   ├── anomaly_detector.py
│   ├── generate_data.py
│   ├── incident_detector.py
│   ├── monitor.py
│   ├── recovery_engine.py
│   ├── recovery_simulator.py
│   ├── revenue_impact.py
│   ├── root_cause.py
│   ├── segment_monitor.py
│   └── temporal_detector.py
|
├── notebooks/
|
└── README.md
```

---

## 6. Technology Stack

- **Python**
- **Pandas** — transaction data processing and aggregation
- **NumPy** — numerical calculations and synthetic data generation
- **Streamlit** — interactive product interface

The current implementation is intentionally lightweight and can run locally without a live payment gateway.

---

## 7. Installation

### Clone / open the project

Open a terminal in the project root:

```bash
cd razorpay-ai-recovery
```

### Create a virtual environment

Windows:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### Install dependencies

```bash
pip install pandas numpy streamlit
```

---

## 8. Generate the Synthetic Dataset

Run:

```bash
python src/generate_data.py
```

The script creates:

```text
data/transactions.csv
```

The generated dataset includes transaction attributes such as:

- Transaction ID
- Merchant ID
- Customer ID
- Amount
- Payment method
- Bank
- Device type
- Location
- Timestamp
- Payment status
- Error code
- Retry count
- Incident ground truth

The generator also injects a controlled incident scenario for demonstration and evaluation.

---

## 9. Run Individual Analysis Modules

### Payment monitoring

```bash
python src/monitor.py
```

### Segment monitoring

```bash
python src/segment_monitor.py
```

### Anomaly analysis

```bash
python src/anomaly_detector.py
```

### Incident detection

```bash
python src/incident_detector.py
```

### Temporal detection

```bash
python src/temporal_detector.py
```

### Root cause analysis

```bash
python src/root_cause.py
```

### Revenue impact

```bash
python src/revenue_impact.py
```

### Recovery recommendation

```bash
python src/recovery_engine.py
```

### Recovery simulation

```bash
python src/recovery_simulator.py
```

---

## 10. Run the Complete AI Agent

From the project root:

```bash
python src/agent.py
```

The agent combines the main investigation stages and prints:

```text
INCIDENT DETECTED
        |
        v
ROOT CAUSE
        |
        v
BUSINESS IMPACT
        |
        v
RECOVERY RECOMMENDATION
```

---

## 11. Launch the Product Dashboard

Run:

```bash
python -m streamlit run app.py
```

Streamlit will provide a local URL, normally:

```text
http://localhost:8501
```

Open that URL in your browser.

---

## 12. Recommended Demo Flow

For a short hackathon demonstration:

### Step 1 — Show Payment Health

Start with the overall transaction health:

- Success rate
- Transaction volume
- Failed transactions
- Failed amount

### Step 2 — Show the Incident

The agent automatically identifies the degraded route:

```text
UPI -> Bank_X -> Android
```

### Step 3 — Explain the Degradation

Show:

```text
Current success:   69.49%
Baseline:          94.42%
Degradation:       24.93 pp
```

### Step 4 — Show Root Cause

Explain that the degradation is concentrated on the affected payment route and show the failure reasons.

### Step 5 — Quantify Business Impact

Show:

```text
Excess failures:    ~126.6
Revenue at risk:    ~₹355,840
```

### Step 6 — Compare Alternatives

Show the historical success rates of alternative banks.

### Step 7 — Explain the Agent Decision

The decision trail is:

```text
DETECT
  ↓
DIAGNOSE
  ↓
QUANTIFY
  ↓
COMPARE
  ↓
RECOMMEND
```

### Step 8 — Simulate Recovery

Click:

```text
🚀 Simulate Recovery
```

Demonstrate the counterfactual improvement:

```text
Bank_X                    Bank_A
69.49%                    96.00%

155 failures              ~20 failures

             +135
     successful payments
```

The final message is:

> The system does not merely report that payments are failing; it identifies the affected route, estimates the business impact, recommends an alternative route, and quantifies the potential recovery.

---

## 13. Why This Is an AI / Intelligent Operations Prototype

The current implementation does not depend on a large language model.

The intelligence comes from:

- Historical baselines
- Route-level segmentation
- Temporal degradation detection
- Severity scoring
- Root-cause comparison
- Financial impact estimation
- Alternative-route ranking
- Counterfactual simulation

This makes the prototype explainable and deterministic while leaving room for more advanced ML or agentic orchestration in a production implementation.

---

## 14. Limitations

This is a prototype based on synthetic data.

It does **not**:

- Process real payments
- Connect to banks
- Execute real payment routing
- Change production routing rules
- Guarantee future payment success
- Guarantee the estimated recovered revenue
- Provide production-grade fraud or risk controls

The recovery result is a **counterfactual estimate**, not a guaranteed business outcome.

---

## 15. Production Evolution

A production-grade version could extend the prototype with:

### Real-time ingestion

Replace the CSV input with payment events from a streaming or event-driven system.

### Advanced anomaly detection

Add models such as:

- Isolation Forest
- Change-point detection
- Bayesian anomaly detection
- Time-series forecasting
- Online learning

### Route optimization

Use contextual route scoring based on:

- Recent success rate
- Bank health
- Latency
- Failure reason
- Transaction value
- Merchant segment
- Customer context
- Capacity

### Guardrails

Add:

- Confidence thresholds
- Minimum sample sizes
- Human approval
- Automatic rollback
- Rate limits
- Circuit breakers

### Observability

Integrate with production monitoring and alerting systems.

### Closed-loop learning

Capture the outcome of every routing recommendation and use it to improve future decisions.

---

## 16. Product Positioning

The product should be presented as:

> **An AI-driven payment recovery decision engine that detects route-level payment degradation, identifies probable root causes, quantifies financial impact, recommends alternative payment routes, and simulates potential recovery.**

Streamlit is the **control-center interface**. The core product is the payment recovery intelligence pipeline behind it.

---

## 17. Safety / Simulation Notice

This repository is intended for experimentation, demonstration, and hackathon use.

```text
SIMULATION ENVIRONMENT
No real payment routing or payment processing is performed.
```

---

## 18. License

Add the appropriate license before public distribution.

If this project is being submitted to a hackathon or used only as a prototype, follow the event's repository and licensing requirements.
