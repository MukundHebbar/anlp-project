# Teacher-setting documentation check

Checked official sources on2026-09-20 while AK conversions were already running. No active settings were changed.

DeepSeek's [V4.1 encoding documentation](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/encoding/README.md) accepts integer reasoning effort1–100 and aliases low=50, high=75, max=100. This establishes that low is meaningful in the model's own encoding, not that DeepInfra necessarily implements that mapping identically.

The official [model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) recommends temperature1.0 and top_p0.95 or1.0; its reported instruct evaluations use maximum effort. Our teacher helper currently sends temperature0, top_p1 and effortlow. This difference motivates a prospective sampling calibration; it does not prove that temperature0 caused a particular error or timeout. The broad model-card output recommendation is not evidence that every short audit needs that many tokens.

The [DeepInfra model API page](https://deepinfra.com/deepseek-ai/DeepSeek-V4.1-Flash/api) confirms the exact deployed model ID and OpenAI-compatible chat endpoint, but its retrieved static page does not document effort mapping. Do not claim provider-level effort verification based only on the model's repository.

Retain AK's registered settings and all first-attempt outcomes. Any temperature/effort comparison must be a separate paired calibration on fixed reviewed cases, with completion, mathematics, schema validity, latency and token usage all reported. Do not overwrite production verdicts or retrospectively label a failed request successful under a changed configuration.
