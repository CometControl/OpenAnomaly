# Time Series Foundation Models (TSFM) & Anomaly Detection: A Research Guide

> **"Data Science Oriented Project"**
> This document serves as the scientific backbone of OpenAnomaly. It bridges the gap between theoretical papers and practical implementation, focusing on the latest advancements in Time Series Foundation Models.

---

## 1. The Paradigm Shift: Zero-Shot Forecasting
Traditional anomaly detection relied on training specific models (ARIMA, LSTM, Prophet) on specific datasets. The new era leverages **Foundation Models** trained on massive corpora of public time series data (100B+ tokens).

These models enable **Zero-Shot Inference**:
1.  **Input**: A context window of historical values (e.g., last 1 hour).
2.  **Output**: A probabilistic forecast for the future (e.g., next 15 mins).
3.  **Anomaly Detection**: Comparison of *Actual* vs. *Forecast* (using confidence intervals or quantiles).

**Best Practice**: Most of these models come with Jupyter Notebooks in their GitHub repositories. **Always start there** to understand the specific data constraints, scaling requirements, and performance characteristics before implementing the adapter.

---

## 2. Key Models & Papers

### 🔵 TimesFM (Google)
*   **Version**: **TimesFM 2.5** (Newer architecture, 200M params).
*   **Type**: Decoder-only Transformer (patched).
*   **Strengths**: High accuracy on long horizons, robust zero-shot performance.
*   **Resources**:
    *   [HuggingFace: google/timesfm-2.5-200m-pytorch](https://huggingface.co/google/timesfm-2.5-200m-pytorch)
    *   [GitHub: google-research/timesfm](https://github.com/google-research/timesfm)

### 🟠 Chronos (Amazon / AutoGluon)
*   Two distinct modern variants:
    1.  **Chronos-2**: Newer **Encoder-only** architecture (not T5-based). Supports multivariate & covariates natively.
    2.  **Chronos-Bolt**: **T5-based** (Encoder-Decoder) like original Chronos, but significantly faster/optimized.
*   **Resources**:
    *   [HuggingFace: autogluon/chronos-2-small](https://huggingface.co/autogluon/chronos-2-small) (Chronos-2)
    *   [HuggingFace: amazon/chronos-bolt-base](https://huggingface.co/amazon/chronos-bolt-base) (Chronos-Bolt)
    *   [GitHub: amazon-science/chronos-forecasting](https://github.com/amazon-science/chronos-forecasting)

### 🟢 TOTO (Datadog)
*   **Version**: **Toto-Open-Base-1.0**.
*   **Type**: Specialized for Observability metrics.
*   **Strengths**: Trained on 1 Trillion metric points.
*   **Resources**:
    *   [HuggingFace: Datadog/toto-open-base-1.0](https://huggingface.co/Datadog/toto-open-base-1.0)
    *   [GitHub: datadog/toto](https://github.com/DataDog/toto)

### 🟣 Moirai (Salesforce)
*   **Version**: **Moirai-2.0**.
*   **Type**: Masked Encoder-based Universal Time Series Transformer.
*   **Strengths**: Multi-variate support, flexible patch size.
*   **Resources**:
    *   [HuggingFace: Salesforce/moirai-2.0-R-base](https://huggingface.co/Salesforce/moirai-2.0-R-base)
    *   [HuggingFace: Salesforce/moirai-2.0-R-small](https://huggingface.co/Salesforce/moirai-2.0-R-small)
    *   [GitHub: SalesforceAIResearch/uni2ts](https://github.com/SalesforceAIResearch/uni2ts)

### ⚪ Granite TTM (IBM)
*   **Version**: **granite-timeseries-ttm-r2**.
*   **Type**: MLP-Mixer based (Tiny Time Mixers).
*   **Strengths**: High speed, good for edge.
*   **Resources**:
    *   [HuggingFace: ibm-granite/granite-timeseries-ttm-r2](https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2)
    *   [GitHub: ibm-granite/granite-tsfm](https://github.com/ibm-granite/granite-tsfm)

---

## 3. Benchmarking & Evaluation

### TAB: Time Series Anomaly Benchmark
*   **Paper**: *Unified Benchmarking of Time Series Anomaly* (in `research/` folder).
*   **Significance**: Critical reference for **how to evaluate** anomaly detection (Precision, Recall, F1).
*   **GitHub**: Contains standard benchmarking code.

### BOOM Benchmark
*   **Paper**: *TOTO_BOOM.pdf* (in `research/`).
*   **Description**: A modern large-scale observability benchmark mentioned in the TOTO paper.
*   **Significance**: Compares TOTO against Chronos, TimesFM, and others. Details computational cost.
*   **Resources**:
    *   [GitHub: DataDog/toto/tree/main/boom](https://github.com/DataDog/toto/tree/main/boom)

### GIFT-Eval
*   A modern benchmark for TSFMs.
*   [HuggingFace Space](https://huggingface.co/spaces/Salesforce/GIFT-Eval)

---

## 4. Future Datasets & Demo

### Project BOOM
*   **Description**: Large-scale observability dataset.
*   **Usage**: Future "Live Demo" by replaying BOOM metrics into VictoriaMetrics.
